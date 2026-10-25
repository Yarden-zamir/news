"""Contract: a spotlight band quotes every item of its source, only items of its source, and can offer that source to follow."""

import json
import subprocess
import sys
from pathlib import Path

GAZETTE = Path(__file__).resolve().parents[1] / "skills" / "newspaper" / "gazette.py"
FORK = "Fork Daily Release"
SOURCE = {"name": FORK, "plugin": "rss-atom", "config": {"url": "https://github.com/me/fork/releases.atom"}}


def item(n: int, source: str = "Source", bonus: bool = False) -> dict:
    return {"id": str(n), "section": "dev", "title": f"Story number {n}", "url": f"https://example.com/{n}", "summary": "",
            "published_at": "2026-10-13T08:00:00+00:00", "source": source, "kind": "article", "bonus": bonus}


def render(tmp_path: Path, rows: list[str], follow: dict | None = SOURCE) -> subprocess.CompletedProcess:
    items = [item(1), item(2), item(3, FORK), item(4, FORK, bonus=True)]
    (tmp_path / "items.json").write_text(json.dumps({
        "fetched": "2026-10-14T12:00:00+00:00", "days": 8, "home": "https://riffle.example.com/", "items": items}))
    # The first group quotes each item; a second group quotes the first item again, as a release lists fork and upstream changes.
    band = {"source": FORK, "kicker": "My fork", "title": "From the fork", "groups": [
        {"title": "Fork changes", "rows": [{"head": f"Change {n}", "text": "news", "item": n} for n in rows]},
        {"title": "Upstream changes", "rows": [{"head": "Upstream", "text": "more news", "item": rows[0]}]}]}
    if follow is not None:
        band["follow"] = follow
    (tmp_path / "picks.json").write_text(json.dumps({
        "title": "Test", "issue": "No. 1", "motto": "m", "colophon": "c",
        "editions": [{"section": "dev", "title": "Dev", "banner": "b", "lead": {"item": "1", "body": "body"},
                      "side": [{"item": "2"}], "spotlight": band, "flow": []}]}))
    out = tmp_path / "out" / "index.html"
    return subprocess.run([sys.executable, "-I", str(GAZETTE), "render", str(tmp_path / "items.json"), str(tmp_path / "picks.json"), str(out)],
                          capture_output=True, text=True)


def test_band_shows_the_source_and_offers_it_to_follow(tmp_path: Path) -> None:
    done = render(tmp_path, ["3", "4"])
    assert done.returncode == 0, done.stderr
    page = (tmp_path / "out" / "index.html").read_text()
    assert 'class="card spotlight"' in page
    start = page.index('id="riffle-sync">') + len('id="riffle-sync">')
    follow = json.loads(page[start:page.index("</script>", start)])["follow"]
    # The band source covers its bonus item, so the page needs no other source for it.
    assert follow == [{**SOURCE, "urls": ["https://example.com/3", "https://example.com/4"]}]


def test_band_must_show_every_item_of_its_source(tmp_path: Path) -> None:
    done = render(tmp_path, ["3"])
    assert done.returncode != 0 and "leaves out" in done.stderr and "4" in done.stderr


def test_band_takes_only_items_of_its_source(tmp_path: Path) -> None:
    done = render(tmp_path, ["3", "4", "2"])
    assert done.returncode != 0


def test_bonus_item_in_a_band_without_a_source_stops_the_build(tmp_path: Path) -> None:
    done = render(tmp_path, ["3", "4"], follow=None)
    assert done.returncode != 0 and "no Riffle source" in done.stderr
