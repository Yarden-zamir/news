"""Contract: the build stops on a misquote and on a dead link, keeps the cards in rank order, and the site states its content signals."""

import json
import subprocess
import sys
import threading
from collections.abc import Iterator
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

import pytest

GAZETTE = Path(__file__).resolve().parents[1] / "skills" / "newspaper" / "gazette.py"


def item(n: int, url: str | None = None, summary: str = "") -> dict:
    return {"id": str(n), "section": "dev", "title": f"Story number {n}", "url": url or f"https://example.com/{n}", "summary": summary,
            "published_at": "2026-10-13T08:00:00+00:00", "source": f"Source {n}", "kind": "article"}


def render(tmp_path: Path, items: list[dict], edition: dict, *args: str) -> subprocess.CompletedProcess:
    (tmp_path / "items.json").write_text(json.dumps({"fetched": "2026-10-14T12:00:00+00:00", "days": 8, "items": items}))
    (tmp_path / "picks.json").write_text(json.dumps({
        "title": "Test", "issue": "No. 1", "motto": "m", "colophon": "c", "page": "/issues/2026-10-14/",
        "editions": [{"section": "dev", "title": "Dev", "banner": "b", "lead": {"item": "1", "body": "body"}, "flow": [], **edition}]}))
    out = tmp_path / "issues" / "2026-10-14" / "index.html"
    return subprocess.run([sys.executable, "-I", str(GAZETTE), "render", str(tmp_path / "items.json"), str(tmp_path / "picks.json"),
                           str(out), *args], capture_output=True, text=True)


SAID = "<p>She said: “We’d   ship it on Friday, and then we rest.”</p>"


def overheard(*texts: str) -> dict:
    return {"flow": [{"box": "overheard", "title": "Overheard", "rows": [
        {"head": f"Speaker {n}", "text": text, "item": str(n + 2)} for n, text in enumerate(texts)]}]}


def test_quotes_match_apart_from_whitespace_quote_marks_case_and_left_out_words(tmp_path: Path) -> None:
    items = [item(n, summary=SAID) for n in range(1, 11)]
    result = render(tmp_path, items, overheard("“we'd ship it on friday”", "“We’d ship it…we rest.”", "We'd ship it ... then we rest."))
    assert result.returncode == 0, result.stderr


def test_misquotes_stop_the_build_and_are_all_listed(tmp_path: Path) -> None:
    items = [item(n, summary=SAID) for n in range(1, 11)]
    result = render(tmp_path, items, overheard("“We ship it on Friday”", "“We’d ship it on Friday”", "“then we rest… ship it”"))
    assert result.returncode != 0
    assert "Speaker 0" in result.stderr and "Speaker 2" in result.stderr
    assert "Speaker 1" not in result.stderr


def test_the_quote_box_is_checked(tmp_path: Path) -> None:
    items = [item(n, summary=SAID) for n in range(1, 4)]
    assert render(tmp_path, items, {"quote": {"text": "We rest on Friday", "credit": "Her", "item": "2"}}).returncode != 0
    assert render(tmp_path, items, {"quote": {"text": "then we rest.", "credit": "Her", "item": "2"}}).returncode == 0


class Publisher(BaseHTTPRequestHandler):
    """/ok answers, /gone is 404, /blocked refuses scripts with 403, /no-head refuses HEAD but answers GET."""

    def answer(self, head: bool) -> None:
        status = {"/ok": 200, "/gone": 404, "/blocked": 403, "/no-head": 405 if head else 200}.get(self.path, 500)
        self.send_response(status)
        self.send_header("Content-Length", "0")
        self.end_headers()

    def do_HEAD(self) -> None:
        self.answer(head=True)

    def do_GET(self) -> None:
        self.answer(head=False)

    def log_message(self, *args: object) -> None:
        pass


@pytest.fixture
def publisher() -> Iterator[str]:
    server = ThreadingHTTPServer(("127.0.0.1", 0), Publisher)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    yield f"http://127.0.0.1:{server.server_address[1]}"
    server.shutdown()


def test_dead_links_stop_the_build_and_blocked_links_only_warn(tmp_path: Path, publisher: str) -> None:
    # Port 9 on the loopback address refuses the connection.
    paths = ["/ok", "/no-head", "/blocked", "/gone"]
    items = [item(n + 1, url=publisher + path) for n, path in enumerate(paths)] + [item(5, url="http://127.0.0.1:9/refused")]
    result = render(tmp_path, items, {"side": [{"item": str(n)} for n in range(2, 6)]}, "--check-links")
    assert result.returncode != 0
    failed = [line.strip() for line in result.stderr.splitlines() if line.startswith("  ")]
    assert {line.split()[-1] for line in failed} == {"http://127.0.0.1:9/refused", publisher + "/gone"}
    assert f"403 (blocks scripts) {publisher}/blocked" in result.stderr


def test_live_links_pass(tmp_path: Path, publisher: str) -> None:
    items = [item(1, url=publisher + "/ok"), item(2, url=publisher + "/no-head")]
    result = render(tmp_path, items, {"side": [{"item": "2"}]}, "--check-links")
    assert result.returncode == 0, result.stderr


def test_cards_below_the_fold_stay_in_rank_order(tmp_path: Path) -> None:
    items = [item(n) for n in range(1, 12)]
    flow = [{"item": str(n), "headline": f"Rank {rank}"} for rank, n in enumerate([7, 3, 9, 2, 11, 5], start=1)]
    assert render(tmp_path, items, {"flow": flow}).returncode == 0
    page = (tmp_path / "issues" / "2026-10-14" / "index.html").read_text()
    positions = [page.index(f'id="story-rank-{rank}"') for rank in range(1, 7)]
    assert positions == sorted(positions)


def test_robots_txt_allows_search_and_ai_use_of_the_paper(tmp_path: Path) -> None:
    assert render(tmp_path, [item(1)], {}).returncode == 0
    subprocess.run([sys.executable, "-I", str(GAZETTE), "site", str(tmp_path), "--site", "https://news.example.com", "--title", "T",
                    "--description", "d"], check=True, capture_output=True)
    robots = (tmp_path / "robots.txt").read_text().splitlines()
    assert "Content-Signal: search=yes, ai-input=yes, ai-train=yes" in robots
    assert "Sitemap: https://news.example.com/sitemap.xml" in robots
