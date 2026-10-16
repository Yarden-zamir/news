"""Contract: each block of a rendered issue lists the URLs of the items that it shows, so reader sync can find them."""

import json
import subprocess
import sys
from html.parser import HTMLParser
from pathlib import Path

GAZETTE = Path(__file__).resolve().parents[1] / "skills" / "newspaper" / "gazette.py"


def item(n: int, kind: str = "article") -> dict:
    return {"id": str(n), "section": "dev", "title": f"Story number {n}", "url": f"https://example.com/{n}", "summary": "",
            "published_at": f"2026-10-1{n % 4}T08:00:00+00:00", "source": f"Source {n}", "kind": kind}


class Blocks(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.blocks: list[list[str]] = []
        self.config: str | None = None
        self.in_config = False

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        named = dict(attrs)
        if "data-entries" in named:
            self.blocks.append(sorted(json.loads(named["data-entries"] or "")))
        self.in_config = named.get("id") == "riffle-sync"

    def handle_data(self, data: str) -> None:
        if self.in_config:
            self.config = data
            self.in_config = False


def render(tmp_path: Path) -> Blocks:
    items = [item(n) for n in range(1, 10)] + [item(10, "release"), item(11, "release")]
    (tmp_path / "items.json").write_text(json.dumps({
        "fetched": "2026-10-14T12:00:00+00:00", "days": 8, "home": "https://riffle.example.com/", "items": items}))
    (tmp_path / "picks.json").write_text(json.dumps({
        "title": "Test", "issue": "No. 1", "motto": "m", "colophon": "c",
        "editions": [{"section": "dev", "title": "Dev", "banner": "b",
                      "lead": {"item": "1", "body": "body", "also": ["2"]},
                      "side": [{"item": "3"}],
                      "flow": [{"item": "4"}, {"box": "wire", "title": "Wire", "rows": [
                          {"head": "Mon", "text": "five", "item": "5"}, {"head": "Tue", "text": "six", "item": "6"}]}]}]}))
    out = tmp_path / "out" / "index.html"
    subprocess.run([sys.executable, "-I", str(GAZETTE), "render", str(tmp_path / "items.json"), str(tmp_path / "picks.json"), str(out)],
                   check=True, capture_output=True, text=True)
    parser = Blocks()
    parser.feed(out.read_text())
    return parser


def test_blocks_list_the_urls_of_their_items(tmp_path: Path) -> None:
    blocks = render(tmp_path).blocks
    url = "https://example.com/{}".format
    # A story lists its own item and its extra sources.
    assert [url(1), url(2)] in blocks
    assert [url(3)] in blocks and [url(4)] in blocks
    # A box lists every row.
    assert [url(5), url(6)] in blocks
    # The release ticker counts every release, so it lists all of them.
    assert [url(10), url(11)] in blocks
    # Each In brief row is a block of its own.
    for n in (7, 8, 9):
        assert [url(n)] in blocks
    assert len(blocks) == 8


def test_sync_config_names_the_riffle_origin(tmp_path: Path) -> None:
    config = render(tmp_path).config
    assert config is not None
    assert json.loads(config)["origin"] == "https://riffle.example.com"
