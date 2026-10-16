"""Write a newspaper items file from Riffle, through the Riffle CLI and its agent access.

Usage: riffle_items.py OUT.json --profiles dev,games [--days 7]

Each listed profile becomes one section. A page can be public, so profiles are opt-in: profiles that are not
listed stay out, and the script names them. A listed profile with a share link gets that link in "shares", so the
page can offer its sources to readers. The CLI must be signed in: run `riffle auth login` first.

Environment:
  RIFFLE_SERVER  origin of the Riffle server (default https://riffle.yarden-zamir.com)
  RIFFLE_CLI     pip spec of the CLI for uvx --from (default: the pinned commit below)
"""

import argparse
import json
import os
import subprocess
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from urllib.parse import quote

# A pinned CLI keeps the weekly run stable when Riffle main moves. Bump it when the API changes.
CLI_SPEC = os.environ.get("RIFFLE_CLI", "git+https://github.com/Yarden-zamir/riffle@8da103912562316a8178bbe7e706f9b4bc288b2d")
SERVER = os.environ.get("RIFFLE_SERVER", "https://riffle.yarden-zamir.com").rstrip("/")
LIMIT = 500
MIN_WINDOW = timedelta(seconds=1)


def fail(message: str) -> None:
    sys.exit(f"riffle_items: {message}")


def api(path: str) -> object:
    result = subprocess.run(["uvx", "--from", CLI_SPEC, "riffle", "api", path], capture_output=True, text=True)
    if result.returncode != 0:
        fail(f"riffle api {path} failed: {result.stderr.strip() or result.stdout.strip()}")
    try:
        return json.loads(result.stdout)
    except json.JSONDecodeError:
        fail(f"riffle api {path} did not return JSON")


def window(profile: str, start: datetime, end: datetime) -> list[dict]:
    """A full page means a cut window, so split it in halves. The server includes both ends, so halves can share items."""
    items = api(f"/changes?profile={quote(profile)}&since={quote(start.isoformat())}&until={quote(end.isoformat())}"
                f"&include_dismissed=true&limit={LIMIT}")
    if not isinstance(items, list):
        fail("/changes did not return a list")
    if len(items) < LIMIT:
        return items
    if end - start <= MIN_WINDOW:
        fail(f"profile {profile!r} has {LIMIT} or more items within one second near {start.isoformat()}; the window cannot split further")
    middle = start + (end - start) / 2
    return window(profile, start, middle) + window(profile, middle, end)


def kind(source_name: str) -> str:
    # Riffle has no source type field, so the source name decides. Revisit when sources get a type,
    # or when a release feed or a status page does not follow the "... Releases" or "... Status" name.
    if source_name.endswith("Releases"):
        return "release"
    if source_name.endswith("Status"):
        return "status"
    return "article"


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n", 1)[0])
    parser.add_argument("out", type=Path)
    parser.add_argument("--profiles", required=True, help="comma-separated Riffle profiles to publish, in edition order")
    parser.add_argument("--days", type=int, default=7)
    args = parser.parse_args()
    if args.days < 1:
        fail("--days must be at least 1")
    wanted = [name.strip() for name in args.profiles.split(",") if name.strip()]
    if not wanted:
        fail("--profiles names no profile")

    profiles = api("/profiles")
    if not isinstance(profiles, list) or not all(isinstance(p, dict) and isinstance(p.get("name"), str) for p in profiles):
        fail("unexpected /profiles response")
    by_name = {p["name"]: p for p in profiles}
    if missing := [name for name in wanted if name not in by_name]:
        fail(f"no such profiles: {missing}. Profiles on the server: {sorted(by_name)}")

    now = datetime.now(timezone.utc).astimezone()
    items, seen, shares = [], set(), {}
    for name in wanted:
        for row in window(name, now - timedelta(days=args.days), now):
            if row["id"] in seen:
                continue
            seen.add(row["id"])
            items.append({
                "id": str(row["id"]), "section": name, "title": row["title"], "url": row.get("url"),
                "summary": row.get("summary") or row.get("content") or "", "published_at": row["published_at"],
                "source": row["source_name"], "kind": kind(row["source_name"]),
                "read": bool(row.get("dismissed")), "saved": bool(row.get("saved")),
            })
        token = by_name[name].get("share_token")
        if token is not None and not isinstance(token, str):
            fail("unexpected share_token in /profiles")
        if token:
            shares[name] = f"{SERVER}/share/{quote(token, safe='')}"
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps({"fetched": now.isoformat(), "days": args.days, "home": f"{SERVER}/",
                                    "shares": shares, "items": items}, indent=1))
    counts = {name: sum(item["section"] == name for item in items) for name in wanted}
    skipped = sorted(set(by_name) - set(wanted))
    print(f"wrote {args.out}: {counts}; share links for {sorted(shares) or 'no profiles'}; "
          f"left out {skipped or 'no profiles'}")


if __name__ == "__main__":
    main()
