"""Render a tick3d newspaper page, and build the site files around the issues.

Usage:
  gazette.py render ITEMS.json PICKS.json OUT.html [--history ISSUES_DIR] [--deny WORDS.txt]
  gazette.py site PUBLIC_DIR --site https://news.example.com --title TITLE --description TEXT

render: ITEMS holds the raw news items. PICKS holds the editorial choices. Each item appears in one place only.
The build stops on a duplicate item, an unknown item or key, a generic image, an image without alt text, a deck
over 25 words, a flow in a small section, an unsafe link, or a denied word. Next to OUT it writes covered.json,
the list of every item that the page shows. With --history it reads covered.json of every earlier issue: a picked
item that an earlier issue showed stops the build, and automatic lists skip such items.

site: reads PUBLIC_DIR/issues/*/covered.json. It copies the newest issue to PUBLIC_DIR/index.html and writes the
archive page, feed.xml, sitemap.xml, 404.html and the fonts.

SKILL.md next to this file describes the file formats.
"""

import argparse
import html
import json
import shutil
import sys
from collections import Counter
from collections.abc import Iterable
from dataclasses import dataclass, field
from datetime import datetime, timedelta, tzinfo
from html.parser import HTMLParser
from pathlib import Path
from typing import Literal, NoReturn, get_args
from urllib.parse import quote, urlsplit, urlunsplit

type Kind = Literal["article", "release", "status"]
type BoxKind = Literal["weather", "classifieds", "corrections", "blotter", "overheard", "wire", "prolific"]
type Audience = Literal["public", "private"]

# Logos, share cards and house illustrations say nothing about a story. A picked image with one of these markers stops the build.
GENERIC_IMAGE_MARKERS = ("generic-", "social-v3-", "steam_share_image", "arc-raiders-social", "opengraph.githubassets.com", "/og/")
MAX_DECK_WORDS = 25
# A section with fewer items gets a lead and side stories only, with no flow below the fold.
SMALL_SECTION = 8
# Twin feeds post one story under two URLs within hours. A later post with the same title, such as a weekly
# "Update Released", is a new story.
TWIN_WINDOW = timedelta(hours=36)
FONTS = Path(__file__).resolve().parent / "assets" / "fonts"
ICON = ("data:image/svg+xml," + quote(
    '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 64 64"><rect x="6" y="6" width="54" height="54" rx="6" fill="#000"/>'
    '<rect x="2" y="2" width="54" height="54" rx="6" fill="#6C5CE7" stroke="#000" stroke-width="4"/>'
    '<text x="29" y="44" font-family="Arial,sans-serif" font-size="36" font-weight="900" fill="#fff" text-anchor="middle">G</text></svg>'))


# ---------- input ----------

def fail(message: str) -> NoReturn:
    sys.exit(f"gazette: {message}")


def read_json(path: Path, what: str) -> object:
    try:
        return json.loads(path.read_text())
    except OSError as error:
        fail(f"cannot read the {what} {path}: {error.strerror or error}")
    except json.JSONDecodeError as error:
        fail(f"the {what} {path} is not valid JSON: {error}")


def keys(data: object, where: str, required: set[str], optional: set[str] = frozenset()) -> dict:
    if not isinstance(data, dict):
        fail(f"{where} must be an object, not {type(data).__name__}")
    missing, unknown = required - data.keys(), data.keys() - required - optional
    if missing or unknown:
        fail(f"{where}: missing keys {sorted(missing)}, unknown keys {sorted(unknown)}")
    return data


def opt_text(data: dict, key: str, where: str, default: str | None = None) -> str | None:
    value = data.get(key)
    if value is None:
        return default
    if not isinstance(value, str):
        fail(f"{where}.{key} must be text")
    return value


def req_text(data: dict, key: str, where: str) -> str:
    value = data.get(key)
    if not isinstance(value, str) or not value.strip():
        fail(f"{where}.{key} must be non-empty text")
    return value


def as_list(data: dict, key: str, where: str) -> list:
    value = data.get(key, [])
    if not isinstance(value, list):
        fail(f"{where}.{key} must be a list")
    return value


def as_bool(data: dict, key: str, where: str) -> bool:
    value = data.get(key, False)
    if not isinstance(value, bool):
        fail(f"{where}.{key} must be true or false")
    return value


def item_id(value: object, where: str) -> str:
    if isinstance(value, bool) or not isinstance(value, (str, int)) or not str(value):
        fail(f"{where} must be an item id (text or a whole number)")
    return str(value)


def parse_time(value: object, where: str, zone: tzinfo | None) -> datetime:
    """An ISO time with an offset. A time without an offset would depend on the machine's time zone, so it stops the build."""
    if not isinstance(value, str):
        fail(f"{where} must be an ISO date and time")
    try:
        moment = datetime.fromisoformat(value)
    except ValueError:
        fail(f"{where} is not an ISO date and time: {value!r}")
    if moment.tzinfo is None:
        fail(f"{where} has no time zone offset: {value!r}")
    return moment.astimezone(zone) if zone else moment


def link(value: str | None, where: str) -> str | None:
    """A link that the page may use: a fragment, a path on this site, or https. Anything else stops the build."""
    if value is None:
        return None
    if value.startswith("#") or (value.startswith("/") and not value.startswith("//")) or value.startswith("https://"):
        return value
    fail(f"{where} must start with #, / or https://, not {value!r}")


def norm_url(url: str) -> str:
    parts = urlsplit(url)
    return urlunsplit((parts.scheme.lower(), parts.netloc.lower(), parts.path.rstrip("/") or "/", parts.query, ""))


def norm_title(title: str) -> str:
    return " ".join(title.casefold().split())


def slug(text: str) -> str:
    out: list[str] = []
    for char in text.casefold():
        if char.isascii() and char.isalnum():
            out.append(char)
        elif out and out[-1] != "-":
            out.append("-")
    return "".join(out)[:60].strip("-")


@dataclass(frozen=True)
class Item:
    id: str
    section: str
    title: str
    url: str | None
    summary: str
    published_at: datetime
    source: str
    kind: Kind
    read: bool
    saved: bool
    bonus: bool


@dataclass(frozen=True)
class Feed:
    fetched: datetime
    days: int
    home: str | None
    shares: dict[str, str]
    items: list[Item]


@dataclass(frozen=True)
class Story:
    item: str
    kicker: str
    headline: str | None
    deck: str | None
    tag: str | None
    also: tuple[str, ...]
    image: str | None
    alt: str | None
    follows: str | None  # URL of an item that an earlier issue showed. The story is a development of it.


@dataclass(frozen=True)
class Lead:
    story: Story
    body: str


@dataclass(frozen=True)
class Row:
    head: str
    text: str
    item: str


@dataclass(frozen=True)
class Box:
    kind: BoxKind
    title: str
    note: str | None
    rows: tuple[Row, ...]


@dataclass(frozen=True)
class Edition:
    section: str
    slug: str
    title: str
    banner: str
    lead: Lead
    side: tuple[Story, ...]
    quote: Row | None  # head is the quote, text is the credit.
    dates: tuple[Row, ...]  # head is the day, text is the event.
    flow: tuple[Story | Box, ...]


@dataclass(frozen=True)
class Number:
    value: str
    label: str
    tip: str
    href: str


@dataclass(frozen=True)
class Picks:
    title: str
    issue: str
    motto: str
    word: str | None
    colophon: str
    audience: Audience
    site: str | None  # Origin of the published site, for canonical and share links.
    page: str | None  # Path of this issue. Later issues link their developments to it.
    previous: str | None
    archive: str | None
    contact: str | None
    description: str | None
    about: str | None
    share_image: str | None
    numbers: tuple[Number, ...]
    editions: tuple[Edition, ...]


@dataclass(frozen=True)
class Past:
    """An item that an earlier issue showed."""

    issue: str
    page: str | None
    anchor: str | None
    headline: str


@dataclass
class History:
    urls: dict[str, Past] = field(default_factory=dict)
    titles: dict[str, list[tuple[datetime, Past]]] = field(default_factory=dict)
    releases: dict[str, datetime] = field(default_factory=dict)  # The newest release that an earlier issue showed, per source.
    issues: int = 0


STORY_KEYS = {"kicker", "headline", "deck", "tag", "also", "image", "alt", "follows"}


def load_items(path: Path) -> Feed:
    data = keys(read_json(path, "items file"), "items file", {"fetched", "days", "items"}, {"home", "shares"})
    fetched = parse_time(data["fetched"], "items file: fetched", None)
    days = data["days"]
    if isinstance(days, bool) or not isinstance(days, int) or days < 1:
        fail("items file: days must be a whole number of at least 1")
    shares = data.get("shares", {})
    if not isinstance(shares, dict) or not all(isinstance(url, str) and url.startswith("https://") for url in shares.values()):
        fail("items file: shares must map section names to https links")
    raw_items = as_list(data, "items", "items file")
    items = []
    for index, raw in enumerate(raw_items):
        where = f"items[{index}]"
        raw = keys(raw, where, {"id", "section", "title", "url", "summary", "published_at", "source", "kind"}, {"read", "saved", "bonus"})
        if raw["kind"] not in get_args(Kind.__value__):
            fail(f"{where}.kind must be one of {get_args(Kind.__value__)}")
        url = opt_text(raw, "url", where)
        items.append(Item(
            id=item_id(raw["id"], f"{where}.id"), section=req_text(raw, "section", where), title=req_text(raw, "title", where),
            url=url if url and url.startswith(("https://", "http://")) else None, summary=opt_text(raw, "summary", where, ""),
            published_at=parse_time(raw["published_at"], f"{where}.published_at", fetched.tzinfo),
            source=req_text(raw, "source", where), kind=raw["kind"], read=as_bool(raw, "read", where),
            saved=as_bool(raw, "saved", where), bonus=as_bool(raw, "bonus", where),
        ))
    if doubles := [value for value, count in Counter(item.id for item in items).items() if count > 1]:
        fail(f"items file repeats ids {doubles[:5]}")
    return Feed(fetched=fetched, days=days, home=link(opt_text(data, "home", "items file"), "items file: home"), shares=shares, items=items)


def story(raw: object, where: str) -> Story:
    raw = keys(raw, where, {"item"}, STORY_KEYS)
    image, alt, deck = opt_text(raw, "image", where), opt_text(raw, "alt", where), opt_text(raw, "deck", where)
    if image and (not image.startswith("https://") or any(marker in image for marker in GENERIC_IMAGE_MARKERS)):
        fail(f"{where}.image is not a specific https image: {image}")
    if image and not (alt and alt.strip()):
        fail(f"{where} has an image without alt text. Describe what the image shows in \"alt\".")
    if deck and len(deck.split()) > MAX_DECK_WORDS:
        fail(f"{where}.deck has {len(deck.split())} words. Keep decks at {MAX_DECK_WORDS} words or fewer.")
    follows = opt_text(raw, "follows", where)
    if follows and not follows.startswith(("https://", "http://")):
        fail(f"{where}.follows must be the http(s) URL of an earlier item")
    return Story(item=item_id(raw["item"], f"{where}.item"), kicker=opt_text(raw, "kicker", where, ""),
                 headline=opt_text(raw, "headline", where), deck=deck, tag=opt_text(raw, "tag", where),
                 also=tuple(item_id(value, f"{where}.also") for value in as_list(raw, "also", where)),
                 image=image, alt=alt, follows=follows)


def row(raw: object, where: str, head: str, body: str) -> Row:
    raw = keys(raw, where, {head, body, "item"})
    return Row(head=req_text(raw, head, where), text=req_text(raw, body, where), item=item_id(raw["item"], f"{where}.item"))


def load_picks(path: Path) -> Picks:
    data = keys(read_json(path, "picks file"), "picks file", {"title", "issue", "motto", "colophon", "editions"},
                {"word", "audience", "site", "page", "previous", "archive", "contact", "description", "about", "share_image", "numbers"})
    where = "picks file"
    audience = data.get("audience", "public")
    if audience not in get_args(Audience.__value__):
        fail(f"{where}: audience must be one of {get_args(Audience.__value__)}")
    site = opt_text(data, "site", where)
    if site is not None and (not site.startswith("https://") or site.endswith("/") or urlsplit(site).path):
        fail(f"{where}: site must be an origin such as https://news.example.com, without a path or trailing slash")
    raw_editions = as_list(data, "editions", where)
    if not raw_editions:
        fail(f"{where}: editions must hold at least one edition")
    editions, slugs = [], set()
    for index, raw in enumerate(raw_editions):
        here = f"editions[{index}]"
        raw = keys(raw, here, {"section", "title", "banner", "lead", "flow"}, {"side", "quote", "dates"})
        section = req_text(raw, "section", here)
        section_slug = slug(section)
        if not section_slug or section_slug in slugs:
            fail(f"{here}.section {section!r} is empty after cleanup or repeats another edition")
        slugs.add(section_slug)
        lead_raw = keys(raw["lead"], f"{here}.lead", {"item", "body"}, STORY_KEYS)
        flow: list[Story | Box] = []
        for position, part in enumerate(as_list(raw, "flow", here)):
            part_where = f"{here}.flow[{position}]"
            if isinstance(part, dict) and "box" in part:
                part = keys(part, part_where, {"box", "title"}, {"note", "rows"})
                if part["box"] not in get_args(BoxKind.__value__):
                    fail(f"{part_where}.box must be one of {get_args(BoxKind.__value__)}")
                rows = tuple(row(item, f"{part_where}.rows[{n}]", "head", "text") for n, item in enumerate(as_list(part, "rows", part_where)))
                if (part["box"] == "prolific") == bool(rows):
                    fail(f"{part_where}: a prolific box takes no rows; every other box needs rows")
                flow.append(Box(kind=part["box"], title=req_text(part, "title", part_where), note=opt_text(part, "note", part_where), rows=rows))
            else:
                flow.append(story(part, part_where))
        quote = raw.get("quote")
        editions.append(Edition(
            section=section, slug=section_slug, title=req_text(raw, "title", here), banner=req_text(raw, "banner", here),
            lead=Lead(story=story({k: v for k, v in lead_raw.items() if k != "body"}, f"{here}.lead"), body=req_text(lead_raw, "body", f"{here}.lead")),
            side=tuple(story(item, f"{here}.side[{n}]") for n, item in enumerate(as_list(raw, "side", here))),
            quote=row(quote, f"{here}.quote", "text", "credit") if quote is not None else None,
            dates=tuple(row(item, f"{here}.dates[{n}]", "day", "text") for n, item in enumerate(as_list(raw, "dates", here))),
            flow=tuple(flow),
        ))
    numbers = []
    for n, raw in enumerate(as_list(data, "numbers", where)):
        raw = keys(raw, f"numbers[{n}]", {"value", "label", "tip", "href"})
        numbers.append(Number(value=req_text(raw, "value", f"numbers[{n}]"), label=req_text(raw, "label", f"numbers[{n}]"),
                              tip=req_text(raw, "tip", f"numbers[{n}]"), href=link(req_text(raw, "href", f"numbers[{n}]"), f"numbers[{n}].href")))
    return Picks(
        title=req_text(data, "title", where), issue=req_text(data, "issue", where), motto=req_text(data, "motto", where),
        word=opt_text(data, "word", where), colophon=req_text(data, "colophon", where), audience=audience, site=site,
        page=link(opt_text(data, "page", where), "page"), previous=link(opt_text(data, "previous", where), "previous"),
        archive=link(opt_text(data, "archive", where), "archive"), contact=link(opt_text(data, "contact", where), "contact"),
        description=opt_text(data, "description", where), about=opt_text(data, "about", where),
        share_image=link(opt_text(data, "share_image", where), "share_image"), numbers=tuple(numbers), editions=tuple(editions),
    )


def load_history(folder: Path, out: Path, page: str | None) -> History:
    """Read covered.json of every earlier issue. The issue that is being rendered (same folder or same page) is not history."""
    history = History()
    for manifest in sorted(folder.glob("*/covered.json")):
        if manifest.parent.resolve() == out.parent.resolve():
            continue
        data = keys(read_json(manifest, "covered file"), str(manifest), {"issue", "page", "date", "built", "items"}, {"title", "description", "leads"})
        if page is not None and data["page"] == page:
            continue
        history.issues += 1
        for index, raw in enumerate(as_list(data, "items", str(manifest))):
            here = f"{manifest}: items[{index}]"
            raw = keys(raw, here, {"url", "title", "kind", "source", "published_at", "headline", "anchor"})
            past = Past(issue=req_text(data, "issue", str(manifest)), page=link(opt_text(data, "page", str(manifest)), f"{manifest}: page"),
                        anchor=opt_text(raw, "anchor", here), headline=req_text(raw, "headline", here))
            published = parse_time(raw["published_at"], f"{here}.published_at", None)
            if url := opt_text(raw, "url", here):
                history.urls.setdefault(norm_url(url), past)
            if raw["kind"] == "article":
                history.titles.setdefault(norm_title(req_text(raw, "title", here)), []).append((published, past))
            if raw["kind"] == "release":
                source = req_text(raw, "source", here)
                history.releases[source] = max(history.releases.get(source, published), published)
    return history


# ---------- helpers ----------

class _Text(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.parts: list[str] = []

    def handle_data(self, data: str) -> None:
        self.parts.append(data)


def plain(raw: str) -> str:
    parser = _Text()
    parser.feed(raw or "")
    return " ".join(" ".join(parser.parts).split())


def e(value: object) -> str:
    return html.escape(str(value), quote=True)


def tip(item: Item) -> str:
    bonus = "Bonus pick from outside the feed. " if item.bonus else ""
    return f"{bonus}{item.source}: {item.title}"


def a(item: Item, label: str, cls: str = "", note: str | None = None) -> str:
    """Link to the source item. The title names the source and its original headline, unless a note is given."""
    klass = f' class="{cls}"' if cls else ""
    if not item.url:
        return f'<span{klass} title="{e(note or tip(item))}">{e(label)}</span>'
    return f'<a{klass} href="{e(item.url)}" title="{e(note or tip(item))}">{e(label)}</a>'


def entries(items: Iterable[Item]) -> str:
    """The data-entries attribute of a block: the URLs of the items that it is based on.
    The page script finds the reader's own changelorg items by URL, because item ids differ per account."""
    urls = list(dict.fromkeys(item.url for item in items if item.url))
    return f' data-entries="{e(json.dumps(urls))}"' if urls else ""


def clean_title(item: Item) -> str:
    """Release feeds often prefix titles with the repository name: 'uv - uv 0.13.0 ...'."""
    prefix, sep, rest = item.title.partition(" - ")
    return rest if sep and item.kind == "release" and " " not in prefix else item.title


def short_title(item: Item) -> str:
    """A short link label. A release title is often its first changelog line, so a release uses its tag instead."""
    url = item.url or ""
    return url.rsplit("/tag/", 1)[1] if item.kind == "release" and "/tag/" in url else clean_title(item)


def plural(count: int, word: str) -> str:
    return f"{count} {word}" + ("" if count == 1 else "s")


def head(title: str, description: str, canonical: str | None, share_image: str | None, feed: bool) -> str:
    """The page head: title, description, share preview, icon and feed link."""
    tags = [
        '<meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">',
        '<meta name="theme-color" content="#E4E7FF" media="(prefers-color-scheme: light)">',
        '<meta name="theme-color" content="#15122B" media="(prefers-color-scheme: dark)">',
        f"<title>{e(title)}</title>", f'<meta name="description" content="{e(description)}">',
        f'<link rel="icon" href="{ICON}">', '<meta property="og:type" content="website">',
        f'<meta property="og:title" content="{e(title)}">', f'<meta property="og:description" content="{e(description)}">',
    ]
    if canonical:
        tags += [f'<link rel="canonical" href="{e(canonical)}">', f'<meta property="og:url" content="{e(canonical)}">']
    if share_image:
        tags += [f'<meta property="og:image" content="{e(share_image)}">', '<meta property="og:image:width" content="1200">',
                 '<meta property="og:image:height" content="630">', '<meta name="twitter:card" content="summary_large_image">']
    if feed:
        tags.append(f'<link rel="alternate" type="application/atom+xml" title="{e(title.split(" · ")[0])}" href="/feed.xml">')
    return "".join(tags) + f"<style>{CSS}</style>"


# ---------- render ----------

class Paper:
    def __init__(self, feed: Feed, picks: Picks, history: History) -> None:
        self.feed, self.picks, self.history = feed, picks, history
        self.fetched, self.days = feed.fetched, feed.days
        self.public = picks.audience == "public"
        self.sections: dict[str, list[Item]] = {}
        for item in sorted(feed.items, key=lambda item: item.published_at, reverse=True):
            self.sections.setdefault(item.section, []).append(item)
        self.by_id = {item.id: item for item in feed.items}
        self.used: set[str] = set()
        self.used_urls: dict[str, str] = {}
        # Every item that the page shows, with its headline and story anchor: the input of covered.json.
        self.shown: dict[str, tuple[str, str | None]] = {}
        self.anchors: set[str] = set()
        self.leads: list[dict] = []

    def use(self, item_id: str) -> Item:
        """Take an item for one place on the page. A second use, or a second item with the same URL, stops the build."""
        if item_id not in self.by_id:
            fail(f"picked item {item_id!r} is not in the items file")
        item = self.by_id[item_id]
        if item_id in self.used:
            fail(f"item {item_id!r} ({item.title}) is picked twice. Keep each item in one place.")
        if item.url and (other := self.used_urls.get(norm_url(item.url))):
            fail(f"items {other!r} and {item_id!r} have the same URL {item.url}. Pick one of them.")
        if (earlier := self.earlier(item)) is not None:
            fail(f"item {item_id!r} ({item.title}) already ran in {earlier.issue}. Pick another item. "
                 "For news that continues that story, mark a new story with \"follows\".")
        self.used.add(item_id)
        if item.url:
            self.used_urls[norm_url(item.url)] = item_id
        self.shown[item_id] = (clean_title(item), None)
        return item

    def earlier(self, item: Item) -> Past | None:
        """The earlier issue that showed this item: the same URL, or for articles the same title within TWIN_WINDOW."""
        if item.url and (past := self.history.urls.get(norm_url(item.url))):
            return past
        if item.kind == "article":
            for published, past in self.history.titles.get(norm_title(item.title), ()):
                if abs(item.published_at - published) <= TWIN_WINDOW:
                    return past
        return None

    def anchor(self, headline: str) -> str:
        base = "story-" + (slug(headline) or "item")
        name, count = base, 1
        while name in self.anchors:
            count += 1
            name = f"{base}-{count}"
        self.anchors.add(name)
        return name

    def story_use(self, story: Story) -> tuple[Item, str]:
        item = self.use(story.item)
        headline = story.headline or clean_title(item)
        story_anchor = self.anchor(headline)
        self.shown[item.id] = (headline, story_anchor)
        return item, story_anchor

    def development(self, story: Story) -> tuple[str, str]:
        """The Development sticker and the line that links back to the earlier story."""
        if story.follows is None:
            return "", ""
        earlier = self.history.urls.get(norm_url(story.follows))
        if earlier is None:
            fail(f"story {story.item!r} follows {story.follows}, which no earlier issue showed. Check the URL, or render with --history.")
        target_link = f"{earlier.page}#{earlier.anchor}" if earlier.page and earlier.anchor else earlier.page
        target = (f'<a href="{e(target_link)}" title="The earlier story, in {e(earlier.issue)}">{e(earlier.headline)}</a>'
                  if target_link else f"“{e(earlier.headline)}”")
        return ('<span class="sticker dev" title="This story continues a story from an earlier issue">Development</span>',
                f'<p class="follows">Follows {target} · {e(earlier.issue)}</p>')

    def date(self, item: Item) -> str:
        built_day = item.published_at.date() == self.fetched.date()
        return (f'<span class="sticker {"info" if built_day else ""}" title="Published {item.published_at:%A %d %B, %H:%M}">'
                f'{item.published_at:%d %b}</span>')

    def marks(self, item: Item) -> str:
        """Bonus and read marks. A public page never shows what its owner read."""
        bonus = '<span class="sticker bonus" title="Bonus pick from outside the feed">Bonus</span>' if item.bonus else ""
        read = '<span class="stamp" title="You cleared this from your desk">✓ read</span>' if item.read and not self.public else ""
        return bonus + read

    @staticmethod
    def figure(item: Item, url: str | None, alt: str | None) -> str:
        if not url:
            return ""
        return (f'<figure class="photo"><img src="{e(url)}" alt="{e(alt or "")}" loading="lazy" decoding="async" '
                f'referrerpolicy="no-referrer"><figcaption>Image: {e(item.source)}</figcaption></figure>')

    def extras(self, story: Story) -> list[Item]:
        return [self.use(extra_id) for extra_id in story.also]

    @staticmethod
    def also(extras: list[Item], main: Item) -> str:
        """Extra sources of a story. Name the source, or a short title when the source repeats."""
        return "".join(f' · {a(item, item.source if item.source != main.source else short_title(item))}' for item in extras)

    def card(self, story: Story) -> str:
        item, story_anchor = self.story_use(story)
        extras = self.extras(story)
        tag = f'<span class="sticker warn">{e(story.tag)}</span>' if story.tag else ""
        sticker, follows = self.development(story)
        return f"""<article class="card story" id="{e(story_anchor)}"{entries([item, *extras])}>{self.figure(item, story.image, story.alt)}
          <div class="pad"><div class="meta">{self.date(item)}<span class="label">{e(story.kicker)}</span>{sticker}{tag}{self.marks(item)}</div>
          <h3>{a(item, story.headline or clean_title(item))}</h3>
          {f'<p class="deck">{e(story.deck)}</p>' if story.deck else ""}{follows}
          <p class="src">{e(item.source)}{self.also(extras, item)}</p></div></article>"""

    @staticmethod
    def box_head(box: Box) -> str:
        note = f'<p class="note">{e(box.note)}</p>' if box.note else ""
        return f"<header><h2>{e(box.title)}</h2>{note}</header>"

    def box(self, box: Box, section: str) -> str:
        if box.kind == "prolific":
            counts = Counter(item.source for item in self.sections[section] if item.kind == "article").most_common(6)
            peak = counts[0][1] if counts else 1
            rows = "".join(
                f'<li><span class="name" title="{count} items from {e(name)} in {self.days} days">{e(name)}</span>'
                f'<span class="bar" style="--w:{count / peak:.3f}"></span><b>{count}</b></li>'
                for name, count in counts)
            return f'<section class="card box prolific">{self.box_head(box)}<ol>{rows}</ol></section>'
        lines = [(line, self.use(line.item)) for line in box.rows]
        rows = "".join(
            f'<li><span class="{"sticker wait" if box.kind == "classifieds" else "label"}">{e(line.head)}</span> '
            f'{a(item, line.text)}</li>'
            for line, item in lines)
        return f'<section class="card box {e(box.kind)}"{entries(item for _, item in lines)}>{self.box_head(box)}<ul>{rows}</ul></section>'

    def lead(self, edition: Edition) -> str:
        story = edition.lead.story
        item, story_anchor = self.story_use(story)
        extras = self.extras(story)
        self.leads.append({"section": edition.section, "headline": story.headline or clean_title(item), "anchor": story_anchor})
        sticker, follows = self.development(story)
        return f"""<article class="card lead" id="{e(story_anchor)}"{entries([item, *extras])}>{self.figure(item, story.image, story.alt)}
          <div class="pad"><span class="stamp extra" title="The biggest story of the edition, as picked by the agent">Extra!</span>
          <div class="meta">{self.date(item)}<span class="label">{e(story.kicker)}</span>{sticker}{self.marks(item)}</div>
          <h3>{a(item, story.headline or clean_title(item))}</h3>
          {f'<p class="deck">{e(story.deck)}</p>' if story.deck else ""}{follows}<p class="body">{e(edition.lead.body)}</p>
          <p class="jump">{a(item, "Continued at " + item.source + " →")}{self.also(extras, item)}</p></div></article>"""

    def side(self, edition: Edition) -> str:
        parts = []
        for story in edition.side:
            item, story_anchor = self.story_use(story)
            extras = self.extras(story)
            sticker, follows = self.development(story)
            parts.append(f"""<article class="card side-story" id="{e(story_anchor)}"{entries([item, *extras])}><div class="pad">
              <div class="meta">{self.date(item)}<span class="label">{e(story.kicker)}</span>{sticker}{self.marks(item)}</div>
              <h3>{a(item, story.headline or clean_title(item))}</h3><p class="deck">{e(story.deck or "")}</p>{follows}
              <p class="src">{e(item.source)}{self.also(extras, item)}</p></div></article>""")
        if edition.quote:
            quoted = self.use(edition.quote.item)
            parts.append(f'<figure class="card quote"{entries([quoted])}><blockquote>“{e(edition.quote.head)}”</blockquote>'
                         f'<figcaption>{a(quoted, edition.quote.text)}</figcaption></figure>')
        if edition.dates:
            dated = [(line, self.use(line.item)) for line in edition.dates]
            rows = "".join(f'<li><span class="sticker wait">{e(line.head)}</span>{a(item, line.text)}</li>' for line, item in dated)
            parts.append(f'<section class="card box coming"{entries(item for _, item in dated)}><header><h2>Save the date</h2></header>'
                         f'<ul>{rows}</ul></section>')
        return "".join(parts)

    def release_log(self, section: str) -> str:
        """Release feeds that no story covers: the newest version each, and only versions newer than earlier issues showed.
        It marks every release item of the section as used."""
        releases = [item for item in self.sections[section] if item.kind == "release"]
        groups: dict[str, list[Item]] = {}
        for item in releases:
            if self.earlier(item) is not None:
                continue
            if (shown := self.history.releases.get(item.source)) is not None and item.published_at <= shown:
                continue
            groups.setdefault(item.source, []).append(item)
        # A source that a story already covers stays out of the ticker. Releases never reach In brief.
        covered = {item.source for item in releases if item.id in self.used}
        self.used.update(item.id for item in releases)
        cells, counted = "", []
        for name, items in sorted(groups.items(), key=lambda pair: (-len(pair[1]), pair[0].lower())):
            if name in covered:
                continue
            latest = items[0]
            self.shown[latest.id] = (short_title(latest), None)
            project = name.removesuffix(" Releases")
            counted += items
            cells += (f'<li><span class="name">{e(project)}</span>'
                      f'{a(latest, short_title(latest), "ver", f"{project}: newest of {len(items)} releases in {self.days} days")}'
                      f'<span class="label">{len(items)}× · {latest.published_at:%d %b}</span></li>')
        if not cells:
            return ""
        # The ticker counts every release of a project, so it is based on all of them, not only on the newest one.
        return f"""<section class="card ticker" aria-label="Also shipped"{entries(counted)}><span class="ticker-label">Also shipped · {len(counted)}</span>
          <ul>{cells}</ul></section>"""

    def brief(self, section: str, limit: int = 14) -> str:
        """In brief: a visible box. With a flow, the page script deals its items into the shortest columns."""
        picked = {norm_title(self.by_id[used].title) for used in self.used}
        rest: list[Item] = []
        for item in self.sections[section]:
            title = norm_title(item.title)
            if item.id in self.used or item.kind == "status" or title in picked or self.earlier(item) is not None:
                continue
            if item.url and norm_url(item.url) in self.used_urls:
                continue
            picked.add(title)
            rest.append(item)
        if not rest:
            return ""
        for item in rest[:limit]:
            self.shown[item.id] = (clean_title(item), None)
        # The page script deals each row into a column on its own, so each row is a block.
        rows = "".join(f'<li{entries([item])}>{self.date(item)}<span>{a(item, clean_title(item))} '
                       f'<span class="label">{e(item.source)}</span>{self.marks(item)}</span></li>'
                       for item in rest[:limit])
        more = len(rest) - min(limit, len(rest))
        note = f'<p class="more">…and {more} more {"item" if more == 1 else "items"} in the feed.</p>' if more else ""
        return f'<section class="card box brief" data-pool><header><h2>In brief</h2></header><ul>{rows}</ul>{note}</section>'

    def shelf(self, section: str) -> str:
        """Saved items that no story uses yet. Only a private page shows the shelf."""
        if self.public:
            return ""
        items = [item for item in self.sections[section]
                 if item.saved and item.kind != "status" and item.id not in self.used and self.earlier(item) is None]
        if not items:
            return ""
        rows = "".join(f'<li>{a(self.use(item.id), item.title)} <span class="label">{e(item.source)}</span>{self.marks(item)}</li>'
                       for item in items)
        return (f'<section class="card box shelf"{entries(items)}><header><h2>On your shelf</h2><p class="note">Saved for later. Later is now.</p>'
                f'</header><ul>{rows}</ul></section>')

    def get_desk(self, section: str, label: str = "Start a feed with these sources →") -> str:
        """A link that copies the sources of a section into the reader's own changelorg."""
        url = self.feed.shares.get(section)
        if url is None:
            return ""
        note = f"Import the {section} sources into your own changelorg feed. No account needed."
        return f'<a class="get-desk" href="{e(url)}" title="{e(note)}">{e(label)}</a>'

    def edition(self, edition: Edition) -> str:
        items = self.sections.get(edition.section)
        if items is None:
            fail(f"section {edition.section!r} has no items. Sections in the items file: {sorted(self.sections)}")
        if len(items) < SMALL_SECTION and edition.flow:
            fail(f"section {edition.section!r} has only {len(items)} items. Use a lead and side stories only, with an empty flow.")
        sources = len({item.source for item in items})
        front = f'<div class="front">{self.lead(edition)}<div class="side">{self.side(edition)}</div></div>'
        flow = [self.card(part) if isinstance(part, Story) else self.box(part, edition.section) for part in edition.flow]
        if shelf := self.shelf(edition.section):
            flow.insert(min(3, len(flow)), shelf)
        ticker = self.release_log(edition.section)
        brief = self.brief(edition.section)
        below = (f'<div class="fold"><span>Below the fold</span></div><div class="flow" data-flow>{"".join(flow)}</div>{brief}'
                 if flow else brief)
        title_id = f"{edition.slug}-title"
        return f"""<section class="edition" id="{e(edition.slug)}" data-section="{e(edition.slug)}" aria-labelledby="{e(title_id)}">
          <div class="banner"><div class="banner-top"><span class="label">{e(edition.title)} · {plural(len(items), "item")} · {plural(sources, "source")}</span>{self.get_desk(edition.section)}</div>
            <h2 id="{e(title_id)}">{e(edition.banner)}</h2></div>
          {front}{ticker}{below}
          <p class="edition-end"><a href="#top">↑ Back to top</a>{self.get_desk(edition.section)}</p>
        </section>"""

    def numbers(self, first: str) -> str:
        every = [item for rows in self.sections.values() for item in rows]
        span = f"{self.fetched - timedelta(days=self.days):%d %b} to {self.fetched:%d %b}"
        per_section = ", ".join(f"{len(rows)} {name}" for name, rows in self.sections.items())
        target = "#about" if self.picks.about else first
        cards = [
            Number(str(len(every)), f"items · {per_section}", f"Items published in these desks from {span}", target),
            Number(str(len({(item.section, item.source) for item in every})), "sources with news",
                   "Sources with at least one item in the window", target),
        ]
        if not self.public and (read := sum(item.read for item in every)):
            cards.append(Number(str(read), "items you already read", "Items that you cleared from your desk. They carry a ✓ read stamp.", first))
        cards += self.picks.numbers
        return '<section class="numbers" aria-label="By the numbers">' + "".join(
            f'<a class="card num" href="{e(card.href)}" title="{e(card.tip)}"><b>{e(card.value)}</b><span>{e(card.label)}</span></a>'
            for card in cards) + "</section>"

    def about(self) -> str:
        if not self.picks.about:
            return ""
        buttons = "".join(self.get_desk(edition.section, f"Start a feed with the {edition.section} sources →")
                          for edition in self.picks.editions if edition.section in self.feed.shares)
        return (f'<section class="card about" id="about" aria-labelledby="about-title"><h2 id="about-title">What is this?</h2>'
                f'<p>{e(self.picks.about)}</p>{f"<div class=about-links>{buttons}</div>" if buttons else ""}</section>')

    def footer(self) -> str:
        picks = self.picks
        shared = [f'<a href="{e(self.feed.shares[ed.section])}" title="Import the {e(ed.section)} sources into your own changelorg feed">'
                  f'{e(ed.section)}</a>' for ed in picks.editions if ed.section in self.feed.shares]
        links = [f'<a href="{e(picks.previous)}">← Previous issue</a>' if picks.previous else "",
                 f'<a href="{e(picks.archive)}">All issues</a>' if picks.archive else "",
                 '<a href="/feed.xml">Feed</a>' if picks.site else "",
                 f'<a href="{e(picks.contact)}">Report a mistake</a>' if picks.contact else ""]
        lines = [e(picks.colophon)]
        if shared:
            lines.append(f"Want these desks? Copy their sources into your own changelorg: {', '.join(shared)}.")
        lines.append("Images load from the publishers' websites. Each image credits its source.")
        if nav := " · ".join(part for part in links if part):
            lines.append(nav)
        return "<footer>" + "".join(f"<p>{line}</p>" for line in lines) + "</footer>"

    def covered(self) -> dict:
        items = []
        for shown_id, (headline, story_anchor) in self.shown.items():
            item = self.by_id[shown_id]
            items.append({"url": item.url, "title": item.title, "kind": item.kind, "source": item.source,
                          "published_at": item.published_at.isoformat(), "headline": headline, "anchor": story_anchor})
        return {"issue": self.picks.issue, "page": self.picks.page, "date": f"{self.fetched:%Y-%m-%d}", "built": self.fetched.isoformat(),
                "title": self.picks.title, "description": self.description(), "leads": self.leads, "items": items}

    def sync_config(self) -> str:
        """Settings of the page script that shows and changes the viewed and shelved state in the reader's changelorg.
        Without a changelorg home in the items file, the page has no sync."""
        if self.feed.home is None:
            return ""
        home = urlsplit(self.feed.home)
        config = {"origin": f"{home.scheme}://{home.netloc}",
                  "since": (self.fetched - timedelta(days=self.days + 1)).isoformat(),
                  "until": (self.fetched + timedelta(days=1)).isoformat(),
                  "shares": self.feed.shares}
        # "<" never appears raw, so the JSON cannot close the script element.
        data = json.dumps(config).replace("<", "\\u003c")
        return f'<script type="application/json" id="changelorg-sync">{data}</script>'

    def description(self) -> str:
        if self.picks.description:
            return self.picks.description
        lead = self.picks.editions[0].lead.story
        return lead.deck or self.picks.motto

    def render(self) -> str:
        picks = self.picks
        body = "".join(self.edition(edition) for edition in picks.editions)
        every = [item for rows in self.sections.values() for item in rows]
        built_day = sum(item.published_at.date() == self.fetched.date() for item in every)
        first = f"#{picks.editions[0].slug}"
        word = ""
        if picks.word:
            count = sum(picks.word.casefold() in f"{item.title} {plain(item.summary)[:600]}".casefold() for item in every)
            word = (f'<a class="ear" href="{e(first)}" title="Items whose title or summary contains the word {e(picks.word)}">'
                    f'<span class="label">Word of the week</span><b>“{e(picks.word)}”</b><span>in {count} items</span></a>')
        buttons = ""
        if len(picks.editions) > 1:
            buttons = '<div class="seg" role="group" aria-label="Show edition"><button aria-pressed="true" data-show="all">All editions</button>' + "".join(
                f'<button aria-pressed="false" data-show="{e(ed.slug)}">{e(ed.section.title())}</button>' for ed in picks.editions) + "</div>"
        canonical = picks.site + picks.page if picks.site and picks.page else None
        share_image = (picks.site + picks.share_image if picks.site and picks.share_image and picks.share_image.startswith("/")
                       else picks.share_image)
        title = f"{picks.title} · {picks.issue} · {self.fetched:%d %B %Y}"
        return f"""<!doctype html>
<html lang="en"><head>{head(title, self.description(), canonical, share_image, bool(picks.site))}</head>
<body><a class="skip" href="#main">Skip to the news</a><div class="page">
<header class="card masthead" id="top">
  <div class="rule"><span class="label">{e(picks.issue)}</span><span class="label">{self.fetched:%A, %d %B %Y}</span><span class="label">Price: 0 tokens</span></div>
  <div class="head">
    {word or "<span></span>"}
    <h1>{e(picks.title)}</h1>
    <a class="ear" href="{e(first)}" title="Items published on {self.fetched:%d %B}, the day this issue was built"><span class="label">Newest</span><b>{built_day} new</b><span>on {self.fetched:%d %b}</span></a>
  </div>
  <p class="motto">{e(picks.motto)}</p>
  <div class="rule">{buttons}<span class="stamp big" title="Every story links to the item that it comes from">✓ Every story sourced</span></div>
</header>
<section class="sync-bar" data-sync aria-label="Your changelorg" aria-live="polite" hidden></section>
<main id="main" class="page-main">
{self.numbers(first)}
{self.about()}
{body}
</main>
{self.footer()}
</div>{self.sync_config()}<script>{JS}</script></body></html>"""


# ---------- site ----------

def build_site(public: Path, site: str, title: str, description: str) -> list[dict]:
    """Copy the newest issue to the home page, and write the archive, the feed, the sitemap, the 404 page and the fonts."""
    if not site.startswith("https://") or site.endswith("/"):
        fail("--site must be an origin such as https://news.example.com, without a trailing slash")
    issues = []
    for manifest in sorted((public / "issues").glob("*/covered.json")):
        data = keys(read_json(manifest, "covered file"), str(manifest), {"issue", "page", "date", "built", "items"}, {"title", "description", "leads"})
        page = link(req_text(data, "page", str(manifest)), f"{manifest}: page")
        if not page.startswith("/"):
            fail(f"{manifest}: page must be a path on this site")
        if not (manifest.parent / "index.html").is_file():
            fail(f"{manifest.parent} has covered.json but no index.html")
        issues.append({**data, "folder": manifest.parent, "built_at": parse_time(data["built"], f"{manifest}: built", None)})
    if not issues:
        fail(f"no issues with covered.json in {public / 'issues'}")
    issues.sort(key=lambda issue: issue["built_at"])
    newest = issues[-1]
    shutil.copyfile(newest["folder"] / "index.html", public / "index.html")
    (public / "fonts").mkdir(exist_ok=True)
    for font in FONTS.iterdir():
        shutil.copyfile(font, public / "fonts" / font.name)

    rows = []
    for issue in reversed(issues):
        leads = "".join(f'<li><span class="label">{e(lead["section"])}</span> <a href="{e(issue["page"])}#{e(lead["anchor"])}">{e(lead["headline"])}</a></li>'
                        for lead in issue.get("leads", []))
        rows.append(f'<article class="card issue-row"><div class="pad"><div class="meta"><span class="sticker wait">{e(issue["issue"])}</span>'
                    f'<span class="label">{issue["built_at"]:%A, %d %B %Y}</span></div>'
                    f'<h2><a href="{e(issue["page"])}">{e(issue.get("description") or issue["issue"])}</a></h2><ul>{leads}</ul></div></article>')
    archive = f"""<!doctype html>
<html lang="en"><head>{head(f"All issues · {title}", description, site + "/issues/", site + "/og.png" if (public / "og.png").is_file() else None, True)}</head>
<body><a class="skip" href="#main">Skip to the list</a><div class="page">
<header class="card masthead" id="top"><div class="rule"><span class="label">Archive</span><span class="label">{plural(len(issues), "issue")}</span></div>
<h1 class="archive-title"><a href="/">{e(title)}</a></h1><p class="motto">{e(description)}</p></header>
<main id="main" class="page-main archive">{"".join(rows)}</main>
<footer><p><a href="/">Newest issue</a> · <a href="/feed.xml">Feed</a></p></footer></div></body></html>"""
    (public / "issues" / "index.html").write_text(archive)

    not_found = f"""<!doctype html>
<html lang="en"><head>{head(f"Page not found · {title}", description, None, None, True)}</head>
<body><div class="page"><main id="main" class="page-main"><section class="card missing"><div class="pad">
<span class="stamp big">404</span><h1>This page is not in the paper.</h1>
<p>It may have moved, or it never ran. Try the <a href="/">newest issue</a> or <a href="/issues/">all issues</a>.</p></div></section></main></div></body></html>"""
    (public / "404.html").write_text(not_found)

    entries = "".join(
        f"<entry><title>{e(issue['issue'])} · {issue['built_at']:%d %B %Y}</title><link href=\"{e(site + issue['page'])}\"/>"
        f"<id>{e(site + issue['page'])}</id><updated>{issue['built_at'].isoformat()}</updated>"
        f"<summary>{e(issue.get('description') or issue['issue'])}</summary>"
        f"<content type=\"html\">{e(''.join(f'<p>{e(lead['section'])}: {e(lead['headline'])}</p>' for lead in issue.get('leads', [])))}</content></entry>"
        for issue in reversed(issues))
    feed = (f'<?xml version="1.0" encoding="utf-8"?>\n<feed xmlns="http://www.w3.org/2005/Atom"><title>{e(title)}</title>'
            f"<subtitle>{e(description)}</subtitle><link href=\"{e(site)}/\"/><link rel=\"self\" href=\"{e(site)}/feed.xml\"/>"
            f"<id>{e(site)}/</id><updated>{newest['built_at'].isoformat()}</updated><author><name>{e(title)}</name></author>{entries}</feed>\n")
    (public / "feed.xml").write_text(feed)

    urls = [site + "/", site + "/issues/"] + [site + issue["page"] for issue in issues]
    sitemap = ('<?xml version="1.0" encoding="utf-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">'
               + "".join(f"<url><loc>{e(url)}</loc></url>" for url in urls) + "</urlset>\n")
    (public / "sitemap.xml").write_text(sitemap)
    return issues


CSS = """
@font-face { font-family: "Bricolage Grotesque"; src: local("Bricolage Grotesque"), url("/fonts/bricolage-grotesque.woff2") format("woff2");
  font-weight: 400 800; font-display: swap; }
@font-face { font-family: "JetBrains Mono"; src: local("JetBrains Mono"), url("/fonts/jetbrains-mono.woff2") format("woff2");
  font-weight: 400 600; font-display: swap; }
:root {
  color-scheme: light;
  --canvas: #E4E7FF; --dots: #00000026; --surface: #FFFFFF; --raised: #F1F2FF;
  --ink: #000000; --muted: #3D3D5C; --border: #000000; --shadow-ink: #000000;
  --accent: #6C5CE7; --accent-fg: #FFFFFF; --select: #FFE14D; --select-fg: #000000;
  --info: #00B3FF; --warning: #FFB347; --warning-surface: #FFF6D1; --error: #FF5277;
  --green: #7CFF8A; --yellow: #FFE14D; --pink: #FF9EB0; --stamp: #8250DF;
  --radius: 0.25rem; --bw: 2px; --shadow: 4px 4px 0 0 var(--shadow-ink); --gap: 1.1rem;
  --sans: "Bricolage Grotesque", system-ui, sans-serif;
  --mono: "JetBrainsMono Nerd Font Mono", "JetBrains Mono", monospace;
}
@media (prefers-color-scheme: dark) {
  :root {
    color-scheme: dark;
    --canvas: #15122B; --dots: #F3F0FF22; --surface: #262147; --raised: #1D1938;
    --ink: #F3F0FF; --muted: #BDB6E6; --border: #F3F0FF; --shadow-ink: #B9A8FF;
    --select: #6C5CE7; --select-fg: #FFFFFF; --warning-surface: #3A3018; --stamp: #A371F7;
  }
}
* { box-sizing: border-box; }
/* The editor reads the paper at 130% on desktop. The base grows from 18px at a 1108px viewport to 23.4px (130%) at 1440px. */
html { font-size: clamp(18px, 1.625vw, 23.4px); }
body { margin: 0; font: 1rem/1.45 var(--sans); color: var(--ink); background-color: var(--canvas);
  background-image: radial-gradient(var(--dots) 1.2px, transparent 1.2px); background-size: 16px 16px; }
h1, h2, h3 { font-weight: 800; letter-spacing: -0.01em; margin: 0; }
a { color: inherit; text-decoration-color: var(--accent); text-decoration-thickness: 2px; text-underline-offset: 2px; }
h3 a { text-decoration: none; }
h3 a:hover { text-decoration: underline; text-decoration-color: var(--accent); text-decoration-thickness: 3px; }
:focus-visible { outline: 2px solid var(--accent); outline-offset: 2px; box-shadow: 0 0 0 6px #FF527766; }
[hidden] { display: none !important; }
.skip { position: absolute; left: -999px; top: 0.5rem; z-index: 10; padding: 0.3rem 0.7rem; font-weight: 800; background: var(--select);
  color: var(--select-fg); border: var(--bw) solid var(--border); border-radius: var(--radius); }
.skip:focus { left: 0.5rem; }
.page, .page-main { display: grid; gap: var(--gap); }
.page { max-width: 78rem; margin: 0 auto; padding: 1rem 0.9rem 2.5rem; }
.card { background: var(--surface); border: var(--bw) solid var(--border); border-radius: var(--radius); box-shadow: var(--shadow); }
.pad { padding: 0.7rem 0.85rem 0.75rem; display: grid; gap: 0.3rem; }
.label { font-size: 0.68rem; font-weight: 800; letter-spacing: 0.06em; text-transform: uppercase; color: var(--muted); }
.sticker { display: inline-block; max-width: 100%; overflow: hidden; text-overflow: ellipsis; padding: 0 0.35rem;
  line-height: 1.5; white-space: nowrap; font-size: 0.68rem; font-weight: 800; letter-spacing: 0.04em;
  text-transform: uppercase; color: #000000; background: var(--pink); border: var(--bw) solid var(--shadow-ink);
  border-radius: 4px; box-shadow: 2px 2px 0 0 var(--shadow-ink); transform: rotate(var(--tilt, -3deg)); }
.sticker.info { background: var(--info); } .sticker.wait { background: var(--yellow); } .sticker.warn { background: var(--warning); }
.sticker.bonus { background: var(--green); }
.sticker.dev { background: var(--accent); color: var(--accent-fg); }
.follows { margin: 0; font-size: 0.78rem; font-weight: 700; color: var(--muted); }
.follows a { color: var(--ink); text-decoration-thickness: 2px; }
.story:nth-child(3n+2) .sticker, li:nth-child(3n+2) .sticker { --tilt: 2deg; }
.story:nth-child(3n) .sticker, li:nth-child(3n) .sticker { --tilt: -1.5deg; }
.stamp { display: inline-block; padding: 0 0.3rem; border: 2px solid var(--stamp); border-radius: 3px; color: var(--stamp);
  font: 900 0.68rem/1.4 var(--sans); text-transform: uppercase; transform: rotate(-6deg); }
.stamp.big { font-size: 0.8rem; padding: 0.05rem 0.4rem; transform: rotate(-8deg); }
.meta { display: flex; flex-wrap: wrap; align-items: center; gap: 0.3rem 0.55rem; }
.deck { margin: 0; color: var(--muted); font-size: 0.88rem; line-height: 1.4; }
.src { margin: 0; font-family: var(--mono); font-size: 0.68rem; color: var(--muted); }

/* Masthead with ears, like a broadsheet. */
.masthead { padding: 0.6rem 1rem; text-align: center; container-type: inline-size; }
.masthead .rule { display: flex; flex-wrap: wrap; justify-content: space-between; align-items: center; gap: 0.5rem 1rem; }
.masthead .rule:first-child { border-bottom: var(--bw) solid var(--border); padding-bottom: 0.4rem; }
.masthead .rule:last-child { border-top: var(--bw) solid var(--border); padding-top: 0.55rem; }
.head { display: grid; grid-template-columns: 8.5rem 1fr 8.5rem; align-items: center; gap: 1rem; margin: 0.55rem 0 0.2rem; }
/* The title is about 10.3 em wide. Its cell is the masthead width minus two 8.5rem ears and two 1rem gaps. */
.head h1 { font-size: clamp(2.2rem, calc((100cqi - 19rem) / 10.6), 4.4rem); line-height: 0.95; }
.ear { display: grid; gap: 0.05rem; padding: 0.35rem 0.4rem; border: var(--bw) solid var(--border); border-radius: var(--radius);
  background: var(--raised); color: inherit; text-decoration: none; transition: transform 80ms, box-shadow 80ms; }
.ear b { font-size: 1.05rem; line-height: 1.1; } .ear span:last-child { font-size: 0.7rem; color: var(--muted); }
@media (max-width: 44rem) { .head { grid-template-columns: 1fr; } .ear, .head > span:empty { display: none; } }
.motto { margin: 0 0 0.55rem; font-weight: 600; color: var(--muted); font-style: italic; }
.seg { display: inline-flex; flex-wrap: wrap; overflow: hidden; background: var(--surface); border: var(--bw) solid var(--border); border-radius: var(--radius); }
.seg button { font: inherit; font-weight: 800; padding: 0.2rem 0.8rem; cursor: pointer; border: 0; background: transparent; color: var(--ink); }
.seg button + button { border-left: var(--bw) solid var(--border); }
.seg button[aria-pressed="true"] { background: var(--select); color: var(--select-fg); }
.seg button:focus-visible { outline-offset: -4px; box-shadow: none; }

.numbers { display: grid; grid-template-columns: repeat(auto-fit, minmax(min(100%, 9rem), 1fr)); gap: var(--gap); }
.num { padding: 0.5rem 0.7rem; display: grid; align-content: start; text-decoration: none; color: inherit;
  transition: transform 80ms, box-shadow 80ms; }
.num:hover, .ear:hover { transform: translate(-1px, -1px); box-shadow: 5px 5px 0 0 var(--shadow-ink); }
.num:active, .ear:active { transform: translate(3px, 3px); box-shadow: none; }
.num b { font-size: 1.8rem; line-height: 1.05; font-weight: 800; }
.num span { font-size: 0.72rem; color: var(--muted); }
.about { padding: 0.75rem 1rem; display: grid; gap: 0.5rem; }
.about h2 { font-size: 0.95rem; text-transform: uppercase; letter-spacing: 0.05em; }
.about p { margin: 0; max-width: 52rem; }
.about-links { display: flex; flex-wrap: wrap; gap: 0.6rem; }

.edition { display: grid; gap: var(--gap); }
.edition + .edition { border-top: 4px double var(--border); padding-top: 1.3rem; }
.banner { display: grid; gap: 0.1rem; }
.banner-top { display: flex; flex-wrap: wrap; align-items: center; justify-content: space-between; gap: 0.4rem 1rem; }
.get-desk { display: inline-flex; align-items: center; padding: 0.2rem 0.65rem; font-size: 0.75rem; font-weight: 800; text-decoration: none;
  color: var(--accent-fg); background: var(--accent); border: var(--bw) solid var(--border); border-radius: var(--radius);
  box-shadow: 3px 3px 0 0 var(--shadow-ink); transition: transform 80ms, box-shadow 80ms; }
.get-desk:hover { transform: translate(-1px, -1px); box-shadow: var(--shadow); }
.get-desk:active { transform: translate(3px, 3px); box-shadow: none; }
.banner h2 { font-size: clamp(1.9rem, 4.6vw, 3rem); line-height: 1; text-transform: uppercase; letter-spacing: -0.02em; }
.edition-end { display: flex; flex-wrap: wrap; align-items: center; justify-content: space-between; gap: 0.6rem; margin: 0;
  font-size: 0.8rem; font-weight: 800; }

/* The lead stretches to the side column height; its text block absorbs the extra space. */
.front { display: grid; grid-template-columns: minmax(0, 1.75fr) minmax(0, 1fr); gap: var(--gap); align-items: stretch; }
.side { display: grid; gap: var(--gap); align-content: start; }
@media (max-width: 54rem) { .front { grid-template-columns: 1fr; } }
.lead { position: relative; display: flex; flex-direction: column; overflow: hidden; }
.lead .pad { position: relative; flex: 1 0 auto; display: flex; flex-direction: column; gap: 0.45rem; padding: 0.85rem 1rem 0.9rem; }
.lead .meta { padding-right: 5.5rem; }
.lead h3 { font-size: clamp(1.8rem, 3.8vw, 2.7rem); line-height: 1.02; }
.lead .deck { font-size: 1.05rem; font-weight: 600; color: var(--ink); }
.lead .body { margin: 0; font-size: 0.92rem; }
.lead .body::first-letter { float: left; font-size: 2.3rem; line-height: 0.9; font-weight: 800; padding: 0.15rem 0.35rem;
  margin: 0.1rem 0.4rem 0 0; background: var(--select); color: var(--select-fg); border: var(--bw) solid var(--border); border-radius: var(--radius); }
.jump { margin: auto 0 0; font-size: 0.75rem; font-weight: 800; }
/* The stamp sits on the text block, never on the image: an image can carry text, such as a chart title. */
.extra { position: absolute; top: 0.6rem; right: 0.8rem; z-index: 2; font-size: 1.1rem; padding: 0.1rem 0.5rem;
  background: var(--surface); transform: rotate(8deg); }
.photo { margin: 0; position: relative; border-bottom: var(--bw) solid var(--border); background: var(--raised); }
/* Images keep their own shape: a chart or a screenshot must not lose its edges. A very tall image shrinks to fit. */
.photo img { display: block; width: 100%; height: auto; max-height: 34rem; object-fit: contain; }
.photo figcaption { position: absolute; left: 0.5rem; bottom: 0.45rem; padding: 0 0.35rem; font-size: 0.66rem; font-weight: 800;
  text-transform: uppercase; letter-spacing: 0.04em; color: #000000; background: var(--yellow); border: var(--bw) solid #000000; border-radius: 3px; }
.side-story { overflow: hidden; display: grid; grid-template-columns: 1fr; }
.side-story h3, .story h3 { font-size: 1.08rem; line-height: 1.15; }
.quote { margin: 0; padding: 0.8rem 0.95rem; background: var(--select); color: var(--select-fg); }
.quote blockquote { margin: 0; font-size: 1.15rem; font-weight: 800; line-height: 1.22; letter-spacing: -0.01em; }
.quote figcaption { margin-top: 0.45rem; font-size: 0.72rem; font-weight: 600; }

/* A static ticker: it scrolls by hand, never by itself. */
.ticker { display: flex; align-items: stretch; overflow: hidden; }
.ticker-label { flex: none; display: grid; place-items: center; padding: 0 0.7rem; background: var(--ink); color: var(--canvas);
  font-size: 0.68rem; font-weight: 800; letter-spacing: 0.06em; text-transform: uppercase; }
.ticker ul { list-style: none; margin: 0; padding: 0.45rem 0.6rem; display: flex; gap: 1rem; overflow-x: auto; scrollbar-width: thin; }
.ticker li { flex: none; display: grid; gap: 0.05rem; padding-right: 1rem; border-right: var(--bw) solid var(--raised); }
.ticker .name { font-size: 0.7rem; font-weight: 800; }
.ticker .ver { font-family: var(--mono); font-size: 0.72rem; }
.ticker .label { font-size: 0.68rem; }

.fold { display: flex; align-items: center; gap: 0.8rem; color: var(--muted); }
.fold::before, .fold::after { content: ""; flex: 1; border-top: var(--bw) dashed var(--border); }
.fold span { font-size: 0.68rem; font-weight: 800; letter-spacing: 0.08em; text-transform: uppercase; }

/* Masonry: JavaScript deals cards into the shortest column, in rank order. CSS columns are the fallback. */
.flow { columns: 3 17rem; column-gap: var(--gap); }
.flow > * { break-inside: avoid; margin-bottom: var(--gap); }
.flow.packed { columns: auto; display: grid; grid-template-columns: repeat(var(--cols), minmax(0, 1fr)); gap: var(--gap); align-items: stretch; }
.flow.packed > .col { display: flex; flex-direction: column; gap: var(--gap); }
/* While cards are dealt, columns keep their natural height, so "shortest" means something. */
.flow.packed.packing { align-items: start; }
.flow.packed .col > * { margin-bottom: 0; }
/* The last card of a column takes the leftover height, and the end mark sits at the bottom. */
.flow.packed .col > :last-child { flex: 1 0 auto; display: flex; flex-direction: column; }
.flow.packed .col > :last-child::after { content: "— 30 —"; margin: auto auto 0.5rem; padding-top: 0.4rem;
  font: 800 0.7rem/1 var(--mono); letter-spacing: 0.2em; color: var(--muted); }
.story { overflow: hidden; display: flex; flex-direction: column; }
.story .photo { flex: none; }

.box > header, .brief > header { padding: 0.4rem 0.85rem; background: var(--raised); border-bottom: var(--bw) solid var(--border); }
.box > header .note { margin: 0.1rem 0 0; font-size: 0.7rem; font-style: italic; color: var(--muted); }
.box h2, .brief h2 { font-size: 0.95rem; text-transform: uppercase; letter-spacing: 0.05em; }
.box ul, .box ol, .brief ul { list-style: none; margin: 0; padding: 0.3rem 0.85rem 0.55rem; display: grid; }
.box li, .brief li { padding: 0.4rem 0; border-bottom: var(--bw) solid var(--raised); font-size: 0.84rem; line-height: 1.35; }
.box li:last-child, .brief li:last-child { border-bottom: 0; }
.box a { text-decoration-thickness: 1px; }
.weather li, .wire li { display: grid; grid-template-columns: 4.6rem 1fr; gap: 0.4rem; }
.blotter li { display: grid; grid-template-columns: 5.6rem 1fr; gap: 0.4rem; }
.blotter > header { background: repeating-linear-gradient(-45deg, var(--raised) 0 8px, var(--surface) 8px 16px); }
.overheard li { display: grid; gap: 0.1rem; }
.overheard a { font-weight: 700; font-style: italic; }
.classifieds ul { font-family: var(--mono); }
.classifieds li { font-size: 0.74rem; }
.classifieds .sticker { font-family: var(--sans); margin-right: 0.2rem; }
.corrections { border-style: dashed; }
.corrections li { display: grid; gap: 0.1rem; }
.coming li { display: grid; gap: 0.3rem; justify-items: start; font-weight: 700; }
.prolific li { display: grid; grid-template-columns: 7.5rem 1fr 1.6rem; align-items: center; gap: 0.5rem; }
.prolific .name { font-size: 0.72rem; font-weight: 700; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.prolific .bar { height: 0.8rem; width: calc(var(--w) * 100%); background: var(--accent); border: var(--bw) solid var(--border); border-radius: 2px; }
.prolific b { text-align: right; font-size: 0.8rem; }
.shelf li .stamp { margin-left: 0.4rem; }

.brief li { display: flex; align-items: baseline; gap: 0.5rem; font-weight: 600; }
.brief .sticker { flex: none; }
.brief .label { margin-left: 0.25rem; font-size: 0.68rem; }
.more { margin: 0; padding: 0 0.85rem 0.6rem; font-size: 0.72rem; color: var(--muted); font-style: italic; }
footer { display: grid; gap: 0.3rem; text-align: center; font-size: 0.72rem; color: var(--muted); max-width: 46rem; margin: 0 auto; }
footer p { margin: 0; }

/* Archive and 404 pages. */
.archive-title { font-size: clamp(2rem, 6vw, 3.6rem); margin: 0.5rem 0 0.2rem; }
.archive-title a { text-decoration: none; }
.issue-row h2 { font-size: 1.3rem; line-height: 1.15; }
.issue-row ul { list-style: none; margin: 0.2rem 0 0; padding: 0; display: grid; gap: 0.25rem; }
.missing { max-width: 40rem; margin: 3rem auto; }
.missing h1 { font-size: 2rem; margin-top: 0.6rem; }
.missing .stamp { justify-self: start; }

/* Sync with the reader's changelorg. The page script fills the bar and adds the buttons after sign-in. */
.sync-bar { display: flex; flex-wrap: wrap; align-items: center; justify-content: center; gap: 0.35rem 0.7rem; padding: 0.45rem 0.9rem;
  font-size: 0.8rem; font-weight: 600; text-align: center; background: var(--raised); border: var(--bw) solid var(--border); border-radius: var(--radius); }
.sync-bar[hidden] { display: none; }
.sync-bar .sticker { font-size: 0.72rem; }
.sync-bar .hint { color: var(--muted); }
.sync-actions { display: flex; flex-wrap: wrap; gap: 0.4rem; }
.sync-btn { display: inline-flex; align-items: center; gap: 0.3rem; min-height: 2rem; padding: 0.1rem 0.6rem; font: inherit; font-size: 0.72rem;
  font-weight: 800; cursor: pointer; color: var(--ink); background: var(--surface); border: var(--bw) solid var(--border); border-radius: var(--radius); }
.sync-btn:hover { transform: translate(-1px, -1px); box-shadow: 2px 2px 0 0 var(--shadow-ink); }
.sync-btn[aria-pressed="true"][data-field="dismissed"] { background: var(--green); color: #000000; }
.sync-btn[aria-pressed="true"][data-field="saved"] { background: var(--yellow); color: #000000; }
.sync-btn:disabled { cursor: progress; opacity: 0.6; }
.pad > .sync-actions { margin-top: 0.2rem; }
.box > .sync-actions { padding: 0 0.85rem 0.6rem; }
.quote > .sync-actions { margin-top: 0.55rem; }
.quote .sync-btn { color: #000000; }
.ticker > .sync-actions { flex: none; align-items: center; flex-wrap: nowrap; padding: 0.3rem 0.6rem; border-left: var(--bw) solid var(--border); }
/* A brief row has room for the signs only. The words stay for screen readers. */
li > .sync-actions { flex: none; flex-wrap: nowrap; gap: 0.25rem; margin-left: auto; align-self: center; }
li .sync-btn { min-width: 2rem; justify-content: center; padding: 0.1rem 0.3rem; }
li .sync-btn span, .ticker .sync-btn span { position: absolute; width: 1px; height: 1px; overflow: hidden; clip-path: inset(50%); white-space: nowrap; }
.is-viewed > :not(.pad, .sync-actions), .is-viewed > .pad > :not(.sync-actions) { opacity: 0.5; }
a.entry-viewed::before { content: "✓ "; }
a.entry-shelved::after { content: " ★"; }
"""

JS = """
// Masonry: deal cards in rank order into the shortest column, so the top row holds the best stories.
// In brief starts as one visible box after the flow. The script deals its items into the columns instead.
const flows = [...document.querySelectorAll("[data-flow]")].map((flow) => {
  const pool = flow.nextElementSibling?.matches("[data-pool]") ? flow.nextElementSibling : null;
  const briefs = pool ? [...pool.querySelectorAll("li")] : [];
  const more = pool?.querySelector(".more") ?? null;
  pool?.remove();
  return { flow, cards: [...flow.children], briefs, more };
});
const shortest = (cols) => cols.reduce((low, col) => (col.offsetHeight < low.offsetHeight ? col : low));
function briefBox(title) {
  const box = Object.assign(document.createElement("section"), { className: "card box brief" });
  box.innerHTML = `<header><h2>${title}</h2></header><ul></ul>`;
  return box;
}
function pack() {
  for (const { flow, cards, briefs, more } of flows) {
    if (flow.closest("[hidden]")) continue;
    // Sizes are in rem and the base size follows the viewport, so measure it on each pack.
    const root = getComputedStyle(document.documentElement);
    const rem = parseFloat(root.fontSize);
    const gap = parseFloat(root.getPropertyValue("--gap")) * rem;
    const columns = Math.max(1, Math.floor((flow.clientWidth + gap) / (17 * rem + gap)));
    const cols = Array.from({ length: columns }, () => Object.assign(document.createElement("div"), { className: "col" }));
    flow.classList.add("packed", "packing");
    flow.style.setProperty("--cols", columns);
    flow.replaceChildren(...cols);
    for (const card of cards) shortest(cols).append(card);
    // In brief fills the gaps: one item at a time into the shortest column, each column with its own box.
    // Three items or fewer stay together in one box, because a box with one item looks empty.
    const boxes = new Map();
    for (const item of briefs) {
      const col = briefs.length <= 3 && boxes.size ? boxes.keys().next().value : shortest(cols);
      if (!boxes.has(col)) boxes.set(col, col.appendChild(briefBox(boxes.size ? "In brief, continued" : "In brief")));
      boxes.get(col).querySelector("ul").append(item);
    }
    if (more && boxes.size) [...boxes.values()].at(-1).append(more);
    flow.classList.remove("packing");
  }
}
let pending = 0;
const schedule = () => { cancelAnimationFrame(pending); pending = requestAnimationFrame(pack); };
addEventListener("resize", schedule);
document.fonts?.ready.then(() => { schedule(); if (location.hash) document.getElementById(decodeURIComponent(location.hash.slice(1)))?.scrollIntoView(); });
for (const img of document.images) img.addEventListener("error", () => { img.closest(".photo")?.remove(); img.remove(); schedule(); });
pack();

const buttons = document.querySelectorAll(".seg button");
for (const button of buttons) button.addEventListener("click", () => {
  for (const other of buttons) other.setAttribute("aria-pressed", String(other === button));
  for (const section of document.querySelectorAll(".edition")) {
    section.hidden = button.dataset.show !== "all" && section.dataset.section !== button.dataset.show;
  }
  schedule();
});

// Sync with the reader's changelorg. Sign-in happens on changelorg, and its session cookie stays there; this site stores nothing.
// A block is an element with data-entries: the URLs of the items that it is based on. Item ids differ per account,
// so the script finds the reader's own items by URL. Buttons on a block change every item of the block.
const syncConfig = document.getElementById("changelorg-sync");
if (syncConfig) startSync(JSON.parse(syncConfig.textContent));

function startSync({ origin, since, until, shares }) {
  const bar = document.querySelector("[data-sync]");
  const blocks = [...document.querySelectorAll("[data-entries]")].map((el) => ({ el, urls: JSON.parse(el.dataset.entries) }));
  const pageUrls = new Set(blocks.flatMap((block) => block.urls));
  const back = encodeURIComponent(location.href.split("#")[0]);
  const BUTTONS = [["dismissed", "✓", "Viewed", "Mark as viewed in your changelorg"], ["saved", "★", "Shelved", "Put on your changelorg shelf"]];
  let account = null;
  let byUrl = new Map();
  let loaded = false;
  let writes = 0;

  const el = (tag, props = {}, ...children) => {
    const node = Object.assign(document.createElement(tag), props);
    node.append(...children);
    return node;
  };

  async function api(path, init = {}) {
    const headers = { ...init.headers, ...(account ? { "X-Changelorg-Owner": account.id } : {}) };
    const response = await fetch(origin + path, { ...init, headers, credentials: "include" });
    if (!response.ok) throw Object.assign(new Error(`changelorg answered ${response.status}`), { status: response.status });
    return response.json();
  }

  // A full page means a cut window, so split it in halves. Below one second, keep the cut page: the bar then shows less.
  async function changes(start, end) {
    const query = new URLSearchParams({ since: start.toISOString(), until: end.toISOString(), include_dismissed: "true", limit: "500" });
    const rows = await api(`/changes?${query}`);
    if (rows.length < 500 || end - start <= 1000) return rows;
    const middle = new Date((start.getTime() + end.getTime()) / 2);
    return [...(await changes(start, middle)), ...(await changes(middle, end))];
  }

  async function load() {
    const next = new Map();
    const ids = new Set();
    for (const row of await changes(new Date(since), new Date(until))) {
      if (!row.url || !pageUrls.has(row.url) || ids.has(row.id)) continue;
      ids.add(row.id);
      next.set(row.url, [...(next.get(row.url) ?? []), row]);
    }
    byUrl = next;
    loaded = true;
  }

  const matched = (block) => block.urls.flatMap((url) => byUrl.get(url) ?? []);
  const actionsOf = (block) => block.el.querySelector(":scope > .sync-actions, :scope > .pad > .sync-actions");

  function addActions(block) {
    const group = el("div", { className: "sync-actions" });
    group.setAttribute("role", "group");
    group.setAttribute("aria-label", "Your changelorg");
    for (const [field, sign, label, title] of BUTTONS) {
      const button = el("button", { type: "button", className: "sync-btn", title }, sign, " ", el("span", {}, label));
      button.dataset.field = field;
      button.setAttribute("aria-label", label);
      button.addEventListener("click", () => toggle(block, field));
      group.append(button);
    }
    (block.el.querySelector(":scope > .pad") ?? block.el).append(group);
    return group;
  }

  function paint() {
    let resized = false;
    for (const block of blocks) {
      const rows = matched(block);
      let group = actionsOf(block);
      if (rows.length && !group) {
        group = addActions(block);
        resized = true;
      } else if (!rows.length && group) {
        group.remove();
        group = null;
        resized = true;
      }
      block.el.classList.toggle("is-viewed", rows.length > 0 && rows.every((row) => row.dismissed));
      block.el.classList.toggle("is-shelved", rows.length > 0 && rows.every((row) => row.saved));
      for (const button of group?.querySelectorAll("button") ?? []) {
        button.setAttribute("aria-pressed", String(rows.every((row) => row[button.dataset.field])));
      }
      for (const link of block.el.querySelectorAll("a[href]")) {
        const own = byUrl.get(link.getAttribute("href")) ?? [];
        link.classList.toggle("entry-viewed", own.length > 0 && own.every((row) => row.dismissed));
        link.classList.toggle("entry-shelved", own.some((row) => row.saved));
      }
    }
    if (resized) schedule();
  }

  function show(...children) {
    bar.replaceChildren(...children);
    bar.hidden = false;
  }

  function signedOut(note) {
    account = null;
    byUrl = new Map();
    loaded = false;
    paint();
    show(...(note ? [el("span", { className: "sticker warn" }, note)] : []),
      el("span", {}, "Read these desks in changelorg?"),
      el("a", { className: "get-desk", href: `${origin}/auth/start?rd=${back}` }, "Sign in with GitHub"),
      el("span", { className: "hint" }, "to see what you viewed and shelved, and to mark it here."));
  }

  function signedIn() {
    const inFeed = [...pageUrls].filter((url) => byUrl.has(url)).length;
    const imports = Object.entries(shares ?? {}).flatMap(([name, url], index) => [index ? " · " : "", el("a", { href: url }, name)]);
    const reach = inFeed
      ? el("span", {}, `${inFeed} of ${pageUrls.size} items on this page are in your feeds`)
      : el("span", {}, "None of the items on this page are in your feeds.", ...(imports.length ? [" Import the sources: ", ...imports] : []));
    show(el("span", {}, "Synced with changelorg as ", el("b", {}, `@${account.login}`)), ...(loaded ? [reach] : []),
      el("a", { href: `${origin}/auth/sign_out?rd=${back}` }, "Sign out"));
  }

  function problem(error) {
    if (error?.status === 401) return signedOut("Your changelorg session ended.");
    signedIn();
    const note = error?.status === 412 ? "Your changelorg account changed. Reload the page." : "changelorg did not answer. Try again.";
    bar.prepend(el("span", { className: "sticker warn" }, note));
  }

  async function toggle(block, field) {
    const rows = matched(block);
    const group = actionsOf(block);
    if (!rows.length || !group) return;
    const value = !rows.every((row) => row[field]);
    const before = rows.map((row) => row[field]);
    for (const row of rows) row[field] = value;
    paint();
    writes += 1;
    for (const button of group.querySelectorAll("button")) button.disabled = true;
    // One PATCH per item. The release ticker can hold 40 or more items. If such writes feel slow, add a bulk route to changelorg.
    const results = await Promise.allSettled(rows.map((row) => api(`/changes/${row.id}`, {
      method: "PATCH",
      headers: { "Content-Type": "application/json", "X-Changelorg-Request": "1" },
      body: JSON.stringify({ [field]: value }),
    })));
    writes -= 1;
    for (const button of group.querySelectorAll("button")) button.disabled = false;
    results.forEach((result, index) => {
      if (result.status === "fulfilled") Object.assign(rows[index], result.value);
      else rows[index][field] = before[index];
    });
    paint();
    const failed = results.find((result) => result.status === "rejected");
    if (failed) problem(failed.reason);
    else signedIn();
  }

  // Live state: read again when the tab comes back, and every minute while it is open. Never during a write.
  async function refresh() {
    if (!account || writes || document.hidden) return;
    try {
      await load();
      paint();
      signedIn();
    } catch (error) {
      problem(error);
    }
  }

  (async () => {
    let me;
    try {
      me = await api("/me");
    } catch (error) {
      // Without an answer, changelorg does not accept this site yet, so the page stays as it is.
      if (error.status === 401) signedOut();
      return;
    }
    if (!me.authenticated) return signedOut();
    account = { id: me.id, login: me.login };
    try {
      await load();
    } catch (error) {
      return problem(error);
    }
    paint();
    signedIn();
    document.addEventListener("visibilitychange", refresh);
    setInterval(refresh, 60000);
  })();
}
"""


def deny_check(page: str, path: Path) -> None:
    """Stop when the page contains a denied word. One word or phrase per line; # starts a comment."""
    try:
        words = [line.split("#", 1)[0].strip().casefold() for line in path.read_text().splitlines()]
    except OSError as error:
        fail(f"cannot read the deny list {path}: {error.strerror or error}")
    text = page.casefold()
    if found := sorted({word for word in words if word and word in text}):
        fail(f"the page contains denied words: {', '.join(found)}. Remove the items or text that hold them.")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n", 1)[0])
    commands = parser.add_subparsers(dest="command", required=True)
    render = commands.add_parser("render", help="render one issue")
    render.add_argument("items", type=Path)
    render.add_argument("picks", type=Path)
    render.add_argument("out", type=Path)
    render.add_argument("--history", type=Path, help="folder with one subfolder per earlier issue, each with covered.json")
    render.add_argument("--deny", type=Path, help="file with words that must not appear on the page, one per line")
    site = commands.add_parser("site", help="build the home page, archive, feed, sitemap, 404 page and fonts")
    site.add_argument("public", type=Path)
    site.add_argument("--site", required=True, help="origin of the site, such as https://news.example.com")
    site.add_argument("--title", required=True)
    site.add_argument("--description", required=True)
    args = parser.parse_args()

    if args.command == "site":
        if not args.public.is_dir():
            fail(f"{args.public} is not a folder")
        issues = build_site(args.public, args.site, args.title, args.description)
        print(f"site: {plural(len(issues), 'issue')}; home page is {issues[-1]['issue']} ({issues[-1]['page']})")
        return

    if args.history is not None and not args.history.is_dir():
        fail(f"--history {args.history} is not a folder")
    picks = load_picks(args.picks)
    history = load_history(args.history, args.out, picks.page) if args.history else History()
    paper = Paper(load_items(args.items), picks, history)
    page = paper.render()
    if args.deny:
        deny_check(page, args.deny)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(page)
    (args.out.parent / "covered.json").write_text(json.dumps(paper.covered(), indent=1, ensure_ascii=False))
    images = page.count('<figure class="photo')
    developments = page.count('class="sticker dev"')
    print(f"wrote {args.out}: {len(paper.shown)} items shown, {images} images, "
          f"checked against {plural(history.issues, 'earlier issue')}, {plural(developments, 'development')}")


if __name__ == "__main__":
    main()
