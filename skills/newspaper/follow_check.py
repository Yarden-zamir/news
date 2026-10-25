"""Check the Riffle source of each bonus story: Riffle previews the source, and the story must be in the preview or fit its rules.

Usage: follow_check.py ITEMS PICKS [--riffle COMMAND]

For each entry of "follow" in the picks file, and for the "follow" source of each spotlight band, Riffle fetches the source as a
preview (POST /sources/preview, which saves nothing). A band source catches the items of its rows. Each item of an entry is then:

- caught: the preview holds its URL.
- fits: the preview does not reach back to it, but the source rules accept it (filter terms, or the html-news path prefix),
  and the source without its filters brings stories from the same site section, such as /misalignment-reports/.
- UNSURE: the rules accept it, but the sample shows no story from its section. Open the feed, and check that it carries
  such stories. If it does not, change the source.
- MISSED: the rules reject it, or the source brings no story from its site. Change the source, or the item list.

The preview shows at most 10 changes of the last 30 days, so older stories can only fit. The script also prints the titles of
the preview, so that you can judge whether the source catches stories like the bonus story. It exits 1 when a preview fails
or an item is MISSED. The Riffle CLI needs a token with write access, because a preview is a POST.
"""

import argparse
import json
import shlex
import subprocess
import sys
from pathlib import Path
from urllib.parse import urlsplit

RIFFLE = "uvx --from git+https://github.com/Yarden-zamir/riffle riffle"


def norm(url: str) -> str:
    parts = urlsplit(url)
    return f"{parts.netloc.lower().removeprefix('www.')}{parts.path.rstrip('/')}?{parts.query}"


def terms(value: object) -> list[str]:
    values = value if isinstance(value, list) else [value] if isinstance(value, str) else []
    return [term.lower() for term in values if isinstance(term, str) and term.strip()]


def fits(source: dict, item: dict) -> bool:
    """The rules of the source accept the item. Riffle matches the same terms against the title, link and text of an entry."""
    config = source["config"]
    if source["plugin"] == "html-news":
        article = urlsplit(item["url"])
        return article.netloc == urlsplit(config["url"]).netloc and article.path.startswith(config.get("article_path_prefix", "/"))
    text = f"{item['title']}\n{item['url']}\n{item.get('summary', '')}".lower()
    include, exclude = terms(config.get("include_any")), terms(config.get("exclude_any"))
    return (not include or any(term in text for term in include)) and not any(term in text for term in exclude)


def section(url: str) -> tuple[str, str]:
    """The host and the first path segment of a URL. Flat paths (/slug) and dated paths (/2026/10/19/slug) have no section."""
    parts = urlsplit(url)
    segments = [segment for segment in parts.path.split("/") if segment]
    first = segments[0] if len(segments) > 1 and not segments[0].isdigit() else ""
    return parts.netloc.lower().removeprefix("www."), first


def preview(riffle: str, source: dict) -> list[dict]:
    body = json.dumps({"name": source["name"], "plugin": source["plugin"], "config": source["config"], "enabled": True})
    done = subprocess.run([*shlex.split(riffle), "api", "-X", "POST", "/sources/preview", "-d", body], capture_output=True, text=True)
    if done.returncode != 0:
        raise RuntimeError((done.stderr or done.stdout).strip().splitlines()[-1] if (done.stderr or done.stdout).strip() else f"exit {done.returncode}")
    return json.loads(done.stdout)["changes"]


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n", 1)[0])
    parser.add_argument("items", type=Path)
    parser.add_argument("picks", type=Path)
    parser.add_argument("--riffle", default=RIFFLE, help=f"the Riffle CLI command (default: {RIFFLE})")
    args = parser.parse_args()
    items = {str(item["id"]): item for item in json.loads(args.items.read_text())["items"]}
    picks = json.loads(args.picks.read_text())
    # A spotlight band can offer the source of its items too. It catches the items of its rows.
    bands = [{**edition["spotlight"]["follow"],
              "items": list(dict.fromkeys(line["item"] for group in edition["spotlight"]["groups"] for line in group["rows"]))}
             for edition in picks.get("editions", []) if "follow" in edition.get("spotlight", {})]
    sources = [*picks.get("follow", []), *bands]
    if not sources:
        sys.exit("follow_check: the picks file has no \"follow\" entries")

    problems = 0
    for source in sources:
        print(f"== {source['name']} ({source['plugin']}) {source['config']['url']}")
        try:
            changes = preview(args.riffle, source)
        except RuntimeError as error:
            print(f"   PREVIEW FAILED: {error}")
            problems += 1
            continue
        caught = {norm(change["url"]) for change in changes if change.get("url")}
        sample: list[dict] | None = None
        for listed in source["items"]:
            item = items.get(str(listed))
            if item is None:
                print(f"   MISSED {listed}: not in the items file")
                problems += 1
                continue
            reason = ""
            if norm(item["url"]) in caught:
                verdict = "caught"
            elif not fits(source, item):
                verdict, reason = "MISSED", "the source rules reject it"
            else:
                # Without its filters, the source shows which parts of the site it carries.
                if sample is None:
                    unfiltered = {**source, "config": {key: value for key, value in source["config"].items() if key not in ("include_any", "exclude_any")}}
                    try:
                        sample = preview(args.riffle, unfiltered) if unfiltered["config"] != source["config"] else changes
                    except RuntimeError as error:
                        sample = []
                        print(f"   unfiltered preview failed: {error}")
                host, part = section(item["url"])
                seen = {section(change["url"]) for change in sample if change.get("url")}
                if not any(seen_host == host for seen_host, _ in seen):
                    verdict, reason = "MISSED", f"the source brings no story from {host}"
                elif part and (host, part) not in seen:
                    verdict, reason = "UNSURE", f"no story from /{part}/ in the sample; it has {sorted({p or '/' for h, p in seen if h == host})}"
                else:
                    verdict = "fits"
            problems += verdict == "MISSED"
            print(f"   {verdict:6} {listed}: {item['title'][:90]}" + (f"  ({reason})" if reason else ""))
        print(f"   preview: {len(changes)} recent stories" + ("" if changes else ". The source may be dead, or its filters too narrow."))
        for change in changes[:5]:
            print(f"     {change['published_at'][:10]}  {change['title'][:90]}")
    if problems:
        sys.exit(f"follow_check: {problems} problems")
    print(f"follow_check: {len(sources)} sources, every bonus item caught or fits")


if __name__ == "__main__":
    main()
