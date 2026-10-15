"""Print the images of each page URL: the share image, then every image in the article with its caption.

Usage: page_images.py URL [URL ...]

Look at each image before you use it. A share image is often a logo or a title card.
A chart, diagram, screenshot or photo from the article itself usually shows the story better.
"""

import http.client
import sys
import urllib.request
from html.parser import HTMLParser
from urllib.parse import parse_qs, urljoin, urlparse


def real_url(page: str, src: str) -> str:
    """Make a source absolute. Next.js serves images through /_next/image?url=<original>, so unwrap that."""
    url = urljoin(page, src.strip())
    parsed = urlparse(url)
    if parsed.path == "/_next/image" and (original := parse_qs(parsed.query).get("url")):
        return urljoin(page, original[0])
    return url


def best_source(attrs: dict[str, str | None]) -> str | None:
    """The real image of a tag: lazy loaders keep it in data-src or srcset while src holds a placeholder."""
    for key in ("data-src", "data-lazy-src", "data-original"):
        if attrs.get(key):
            return attrs[key]
    src = attrs.get("src")
    if src and not src.startswith("data:"):
        return src
    srcset = attrs.get("srcset") or attrs.get("data-srcset")
    if srcset:
        # The last candidate of a srcset is usually the largest.
        return srcset.split(",")[-1].strip().split(" ")[0]
    return None


class Images(HTMLParser):
    def __init__(self, page: str) -> None:
        super().__init__()
        self.page = page
        self.share: str | None = None
        self.images: list[list[str]] = []  # [url, size, caption]
        self.figure_start: int | None = None  # Index of the first image inside the open <figure>.
        self.in_caption = False
        self.picture_source: str | None = None

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        named = dict(attrs)
        if tag == "meta" and not self.share and (named.get("property") or named.get("name")) in ("og:image", "twitter:image"):
            if content := named.get("content"):
                self.share = real_url(self.page, content)
        elif tag == "figure":
            self.figure_start = len(self.images)
        elif tag == "source" and (srcset := named.get("srcset") or named.get("data-srcset")):
            self.picture_source = srcset.split(",")[-1].strip().split(" ")[0]
        elif tag == "img":
            source = best_source(named) or self.picture_source
            self.picture_source = None
            if source:
                size = f'{named.get("width") or "?"}x{named.get("height") or "?"}'
                self.images.append([real_url(self.page, source), size, ""])
        elif tag == "figcaption":
            self.in_caption = True

    def handle_endtag(self, tag: str) -> None:
        if tag == "figcaption":
            self.in_caption = False
        elif tag == "figure":
            self.figure_start = None
        elif tag == "picture":
            self.picture_source = None

    def handle_data(self, data: str) -> None:
        # A caption belongs to the last image of its own figure, never to an image before the figure.
        inside = self.figure_start is not None and len(self.images) > self.figure_start
        if self.in_caption and inside and data.strip():
            self.images[-1][2] = f"{self.images[-1][2]} {data.strip()}".strip()


def main() -> None:
    if len(sys.argv) < 2:
        sys.exit(__doc__)
    for page in sys.argv[1:]:
        print(page)
        try:
            if urlparse(page).scheme not in ("http", "https"):
                print("  error: only http and https pages are read")
                continue
            request = urllib.request.Request(page, headers={"User-Agent": "Mozilla/5.0 (newspaper skill)"})
            with urllib.request.urlopen(request, timeout=15) as response:
                found = Images(page)
                found.feed(response.read(3_000_000).decode("utf-8", "replace"))
        except (OSError, ValueError, http.client.HTTPException) as error:
            print(f"  error: {error}")
            continue
        print(f"  share\t{found.share or '-'}")
        for url, size, caption in found.images:
            print(f"  image\t{size}\t{url}\t{caption or '-'}")


if __name__ == "__main__":
    main()
