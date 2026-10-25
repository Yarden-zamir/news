"""Contract: every bonus story on a page comes with a Riffle source that signed-in readers can follow, and history means earlier issues."""

import json
import subprocess
import sys
from pathlib import Path

GAZETTE = Path(__file__).resolve().parents[1] / "skills" / "newspaper" / "gazette.py"
SOURCE = {"name": "Example News: AI agents", "plugin": "rss-atom", "config": {"url": "https://news.example/feed", "include_any": ["AI agent"]}}


def item(n: int, bonus: bool = False) -> dict:
    return {"id": f"bonus-{n}" if bonus else str(n), "section": "dev", "title": f"Story number {n}", "url": f"https://example.com/{n}",
            "summary": "", "published_at": "2026-10-13T08:00:00+00:00", "source": f"Source {n}", "kind": "article", "bonus": bonus}


def render(tmp_path: Path, follow: list[dict] | None, *, items: list[dict] | None = None, fetched: str = "2026-10-14",
           history: Path | None = None) -> subprocess.CompletedProcess:
    items = items or [item(1), item(2, bonus=True), item(3)]
    (tmp_path / "items.json").write_text(json.dumps({
        "fetched": f"{fetched}T12:00:00+00:00", "days": 8, "home": "https://riffle.example.com/", "items": items}))
    picks = {"title": "Test", "issue": "No. 1", "motto": "m", "colophon": "c", "page": f"/issues/{fetched}/",
             "editions": [{"section": "dev", "title": "Dev", "banner": "b", "lead": {"item": items[0]["id"], "body": "body"},
                           "side": [{"item": item_["id"]} for item_ in items[1:]], "flow": []}]}
    if follow is not None:
        picks["follow"] = follow
    (tmp_path / "picks.json").write_text(json.dumps(picks))
    out = tmp_path / "issues" / fetched / "index.html"
    return subprocess.run([sys.executable, "-I", str(GAZETTE), "render", str(tmp_path / "items.json"), str(tmp_path / "picks.json"), str(out),
                           *(["--history", str(history)] if history else [])], capture_output=True, text=True)


def sync_config(tmp_path: Path, fetched: str = "2026-10-14") -> dict:
    page = (tmp_path / "issues" / fetched / "index.html").read_text()
    start = page.index('id="riffle-sync">') + len('id="riffle-sync">')
    return json.loads(page[start:page.index("</script>", start)])


def test_page_offers_the_source_of_each_bonus_story(tmp_path: Path) -> None:
    done = render(tmp_path, [{**SOURCE, "items": ["bonus-2"]}])
    assert done.returncode == 0, done.stderr
    assert sync_config(tmp_path)["follow"] == [{**SOURCE, "urls": ["https://example.com/2"]}]


def test_bonus_story_without_a_source_stops_the_build(tmp_path: Path) -> None:
    done = render(tmp_path, None)
    assert done.returncode != 0
    assert "bonus-2" in done.stderr and "no Riffle source" in done.stderr


def test_source_lists_only_bonus_items_that_the_page_shows(tmp_path: Path) -> None:
    for listed in (["bonus-2", "3"], ["bonus-2", "bonus-9"]):
        assert render(tmp_path, [{**SOURCE, "items": listed}]).returncode != 0, listed


def test_reader_picks_the_profile(tmp_path: Path) -> None:
    done = render(tmp_path, [{**SOURCE, "config": {**SOURCE["config"], "profile": "dev"}, "items": ["bonus-2"]}])
    assert done.returncode != 0 and "profile" in done.stderr


def test_history_holds_only_earlier_issues(tmp_path: Path) -> None:
    follow = [{**SOURCE, "items": ["bonus-2"]}]
    assert render(tmp_path, follow, fetched="2026-10-14").returncode == 0
    # The issue of the 14th shows item 3. A later issue may not show it again ...
    later = render(tmp_path, follow, fetched="2026-10-21", history=tmp_path / "issues")
    assert later.returncode != 0 and "already ran" in later.stderr
    # ... but the issue of the 14th renders again, although a later issue exists.
    (tmp_path / "issues" / "2026-10-21").mkdir(exist_ok=True)
    (tmp_path / "issues" / "2026-10-21" / "covered.json").write_text((tmp_path / "issues" / "2026-10-14" / "covered.json").read_text()
                                                                   .replace("2026-10-14", "2026-10-21"))
    again = render(tmp_path, follow, fetched="2026-10-14", history=tmp_path / "issues")
    assert again.returncode == 0, again.stderr
    assert "checked against 0 earlier issues" in again.stdout
