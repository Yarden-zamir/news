---
name: newspaper
description: Build a newspaper site (the Gazette) from changelorg profiles or other news items, in the tick3d neo-brutalism style. Each issue has a lead story, ranked cards, press boxes and a note on every link. The site has an archive, a feed and no repeats across issues. Use when the user asks for a news page, a digest, a newspaper, an edition or the Gazette, or asks to publish the weekly issue.
license: MIT
---

# Newspaper

You collect news items, act as the editor, and render one issue of a static news site.
One changelorg profile becomes one edition of the paper.

Files in this folder:

- `changelorg_items.py`: writes an items file from changelorg profiles, through the changelorg CLI.
- `gazette.py render`: renders one issue from an items file and a picks file. It writes `covered.json` next to the page.
- `gazette.py site`: builds the home page, the archive, `feed.xml`, `sitemap.xml`, `404.html` and the fonts from all issues.
- `page_images.py`: prints the share image of each page URL, then every image in the article with its caption.
- `example-picks.json`: the picks file of a real issue. Read it for the tone and for the use of each box.
- `assets/fonts/`: Bricolage Grotesque and JetBrains Mono under the SIL Open Font License. The site serves them itself.

Run each script with `uv run --no-project --python 3.12 python -I <script> <arguments>`.
The scripts use only the standard library. This file calls them by name.

## Setup: a changelorg connection

Do these steps once for each person who makes a paper.

1. Open https://changelorg.yarden-zamir.com and sign in with GitHub. CLI access needs a GitHub account.
2. Add sources. Each profile becomes one edition, so group the sources into profiles such as `dev` and `games`.
   - To add your own sources, use the source editor on the site.
   - To start from the sources of another paper, open its share link and import the sources into a new profile.
     The links of news.yarden-zamir.com are [dev](https://changelorg.yarden-zamir.com/share/m6fTRqPU_Tpy8oo6hBwdCg) and [games](https://changelorg.yarden-zamir.com/share/iEZKXyhEwHhL264-p53VWg).
3. Sign in the CLI. Run it in the background, because it waits up to 10 minutes for the approval:
   ```sh
   uvx --from git+https://github.com/Yarden-zamir/changeLorg changelorg auth login --name "newspaper on <machine>"
   ```
   It prints a link and a code. Send them to the user. The user opens the link, compares the code and approves.
   Read access is enough for the paper. Add `--write` only when you also want to make share links.
4. Check the connection. Take profile names from the output, and do not guess them:
   ```sh
   uvx --from git+https://github.com/Yarden-zamir/changeLorg changelorg auth status
   uvx --from git+https://github.com/Yarden-zamir/changeLorg changelorg api /profiles
   ```
5. Optional: share the sources of each published profile, so that readers can start their own feed. This needs `--write` access:
   ```sh
   uvx --from git+https://github.com/Yarden-zamir/changeLorg changelorg api -X POST /shares -d '{"profile": "dev"}'
   ```
   `changelorg_items.py` then puts the share link in the items file, and the page offers it to readers.
   Anyone with the link sees and imports the enabled sources of the profile. `DELETE /shares/<token>` stops the share.

For a different changelorg server, set `CHANGELORG_SERVER` to its origin. The CLI and `changelorg_items.py` both read it.
Never print the token in `~/.config/changelorg/credentials.json`, and never copy it into files, chats or commits.

## Setup: a site folder

Keep the site in a git repository. The `covered.json` files are the memory of the paper: without them, old stories appear again.

```text
SITE/
├── desk/<date>/items.json    raw items of an issue (keep out of git: it holds read and saved marks)
├── desk/<date>/picks.json    the editorial choices of an issue
├── public/                   the files that the host serves
│   ├── issues/<date>/index.html
│   ├── issues/<date>/covered.json
│   └── og.png                1200 × 630 share card for link previews (optional, made once)
├── deny.txt                  words that must never appear on the page (optional, keep out of git)
└── wrangler.jsonc            host settings (optional)
```

`gazette.py site` writes the other files in `public/`. Do not edit them by hand.

## Steps

Set `SITE` to the site folder and `DATE` to today's date as `YYYY-MM-DD`.

1. Write the items file. List the profiles to publish in edition order. A page can be public, so profiles are opt-in:
   ```sh
   changelorg_items.py $SITE/desk/$DATE/items.json --profiles dev,games --days 8
   ```
   For other sources, write the items yourself from feeds, pages or web search results. See "Items file".
2. Read the candidate items. Before you write about an item, read its full text: the item summary, or the page.
3. Read `$SITE/public/issues/*/covered.json`. An item that an earlier issue showed cannot appear again, but news that continues it can. See "Developments".
4. Optional: add bonus stories from outside the feed. Give each one its real URL and publish time, and set `"bonus": true`. The page marks them.
5. Rank the items by interest to the reader.
6. Write `$SITE/desk/$DATE/picks.json`. Follow "Picks file" and "Editorial rules".
7. For each story that can get a picture, run `page_images.py <url>`. Look at each image. See "Images".
8. Render the issue. Fix each error that the build reports, then render again:
   ```sh
   gazette.py render $SITE/desk/$DATE/items.json $SITE/desk/$DATE/picks.json $SITE/public/issues/$DATE/index.html \
     --history $SITE/public/issues --deny $SITE/deny.txt
   ```
9. Build the site files:
   ```sh
   gazette.py site $SITE/public --site https://news.example.com --title "The changelorg Gazette" --description "<one sentence about the paper>"
   ```
10. Do the steps of "Check".
11. Optional: publish. See "Publish".
12. Commit the issue folder, the picks file and the site files. Run `git status` first. If an earlier issue file shows as deleted or changed, stop and find out why.

## Items file

```json
{
  "fetched": "2026-10-13T21:37:22+03:00",
  "days": 8,
  "home": "https://changelorg.yarden-zamir.com/",
  "shares": {"dev": "https://changelorg.yarden-zamir.com/share/…"},
  "items": [
    {"id": "577653", "section": "dev", "title": "Redesigning source control at Anthropic",
     "url": "https://www.anthropic.com/engineering/redesigning-source-control", "summary": "As our merges per day grew…",
     "published_at": "2026-10-13T00:00:00+00:00", "source": "Anthropic Engineering", "kind": "article",
     "read": false, "saved": false, "bonus": false}
  ]
}
```

- `id` is unique text. `section` names the edition that holds the item.
- Each time needs a UTC offset. The page shows times in the zone of `fetched`.
- `kind` is `article`, `release` or `status`. Release items without a story go into the "Also shipped" ticker. Status items go only into a weather box.
- `read`, `saved`, `bonus`, `home` and `shares` are optional.
- `shares` maps a section to the share link of its profile. The edition banner, the "What is this?" box and the footer then offer readers these sources.
- `changelorg_items.py` sets `kind` from the source name: a name that ends in "Releases" or "Status".

## Picks file

```json
{
  "title": "The changelorg Gazette", "issue": "Vol. 1 · No. 2",
  "motto": "All the feed that fits · eight days of the dev and games desks",
  "word": "agent",
  "colophon": "Built 18 October 2026 from changelorg. An AI agent picked the stories and wrote the headlines; every story links to its source.",
  "audience": "public",
  "site": "https://news.example.com",
  "page": "/issues/2026-10-18/",
  "previous": "/issues/2026-10-14/",
  "archive": "/issues/",
  "contact": "https://github.com/<owner>/<repo>/issues",
  "description": "Issue 2: one sentence that names the top stories. Link previews and the archive show it.",
  "about": "Two or three sentences for a first-time reader: what the paper is and who makes it.",
  "share_image": "/og.png",
  "numbers": [{"value": "12", "label": "ARC Raiders posts", "tip": "Why this number matters", "href": "#games"}],
  "editions": [{
    "section": "dev", "title": "Dev edition", "banner": "Source control has a moment",
    "lead": {"item": "577653", "kicker": "Anthropic", "headline": "…", "deck": "…", "body": "…",
             "image": "https://… (a chart from the article)", "alt": "Bar chart of …", "also": []},
    "side": [{"item": "531163", "kicker": "GitHub", "headline": "…", "deck": "…"}],
    "quote": {"text": "Exact words from the item", "credit": "Who said it", "item": "577706"},
    "dates": [{"day": "27 Oct", "text": "What happens", "item": "577772"}],
    "flow": [
      {"item": "577728", "kicker": "Mistral", "headline": "…", "deck": "…", "tag": "Breaking", "also": ["577726"]},
      {"item": "581190", "kicker": "Cloudflare", "headline": "…", "deck": "…", "follows": "https://blog.cloudflare.com/deno-joins-cloudflare/"},
      {"box": "weather", "title": "Pipeline weather", "note": "…", "rows": [{"head": "⛈ Mon 5", "text": "…", "item": "524252"}]}
    ]
  }]
}
```

- Required: `title`, `issue`, `motto`, `colophon` and `editions`. Each edition needs `section`, `title`, `banner`, `lead` and `flow`.
- In a story, only `item` is required. Without `headline`, the page uses the item title.
- `issue` counts the issues: `Vol. 1 · No. N`, where N is the number of earlier issues plus 1.
- `audience` is `public` (the default) or `private`. A private page also shows read marks and an "On your shelf" box of saved items.
- `site` is the origin of the site, without a slash at the end. With `page`, it makes the canonical link and the share tags.
- `page` is the path of this issue. `previous` is the path of the issue before it. `archive` is the path of the archive page.
- `contact` is a link where readers report a mistake.
- `share_image` is the path of the share card. Without `description`, link previews use the lead deck.
- `also` lists other items about the same story. The card links them by source name.
- The page counts items, sources and read items itself. Put only extra numbers in `numbers`, and count them from the items file.

Box kinds for `flow`:

| `box` | Use it for |
| --- | --- |
| `weather` | Incidents and outages, from status items. Put a weather sign and a day in `head`. |
| `classifieds` | Small items in one line each. Put a short word in `head`, such as WANTED, LOST or FOR RENT. |
| `corrections` | Fixes, regressions, withdrawn alerts and metric errors. |
| `blotter` | Agents, bots or services that did something wrong. Put the place in `head`. |
| `overheard` | Short exact quotes. Put the speaker in `head` and the quote in curly quotes in `text`. |
| `wire` | Feeds that send headlines only. Put the date in `head`. |
| `prolific` | A bar chart of the sources with the most articles. It takes no rows. |

## covered.json

`gazette.py render` writes this file next to each issue. `--history` and `gazette.py site` read it. Do not edit it.

```json
{"issue": "Vol. 1 · No. 1", "page": "/issues/2026-10-14/", "date": "2026-10-14", "built": "2026-10-14T21:37:22+03:00",
 "title": "The changelorg Gazette", "description": "…", "leads": [{"section": "dev", "headline": "…", "anchor": "…"}],
 "items": [{"url": "…", "title": "…", "kind": "article", "source": "…", "published_at": "…", "headline": "…", "anchor": "…"}]}
```

## Reader sync

If the items file has `home`, readers can sign in to changelorg from the page. The page then shows and changes their own state.

- Each block lists the items that it is based on in `data-entries`: the item URLs.
  The blocks are the lead, side stories, cards, the quote, boxes, the release ticker and each In brief row.
  A block without items, such as the numbers or the prolific chart, gets no buttons.
- The page reads the reader's items of the issue window from `/changes`, and matches them by URL. Item ids differ per account.
- A block fades when all of its items are dismissed. Its Viewed and Shelved buttons change every item of the block.
  Links of dismissed items fade, and links of saved items get a highlighter mark. No mark changes the layout.
- On a screen with a pointer, the buttons show in the top right corner of a block while the pointer is on it, or while a button has keyboard focus.
  On a touch screen, a long press on a block opens its buttons in a sheet at the bottom of the screen.
- The page reads the state again when the tab comes back, and every minute while it is open.
- Sign-in and sign-out run on changelorg (`/auth/start?rd=<page>` and `/auth/sign_out?rd=<page>`). The site stores no data and sets no cookie.
- If changelorg does not answer, the page shows no sync bar.

The changelorg server must allow the site:

- `CHANGELORG_CORS_ORIGINS` lists the origin of the site.
- oauth2-proxy has `--whitelist-domain=<site host>`, so that sign-in can return to the page.
- The site and changelorg share a registrable domain, such as `news.example.com` and `changelorg.example.com`. The session cookie is `SameSite=Lax`, so browsers do not send it from another site.

## Editorial rules

- **Rank.** Put the most interesting story first. The page deals cards into columns in rank order.
- **One place per item.** Each item appears once. If two sources tell the same story, make one card with `also`.
- **No repeats across issues.** With `--history`, a picked item that an earlier issue showed stops the build.
  The match uses the URL. For articles it also uses the title, within 36 hours of the earlier item.
  In brief and the release ticker skip such items without an error. The ticker also skips releases older than the newest release that an earlier issue showed for the same source.
- **Developments.** When new news continues an earlier story, pick the new item and set `follows` to the URL of the earlier item, from `covered.json`.
  The story gets a Development sticker and a link to the earlier story. Say in the deck what changed. Do not repeat the old facts.
- **Short decks.** Write one or two sentences, at most 25 words. Do not repeat the headline.
- **True facts.** Take every fact, number and date from the linked item. Copy quotes word for word.
- **Write for strangers.** On a public page, explain names that a new reader does not know. Do not write about private data.
- **Light humor.** Put jokes in banners, box titles, box notes and classifieds. Keep facts plain. Write new jokes for each issue.
- **Small sections.** If an edition has fewer than 8 items, use a lead and side stories only, with an empty `flow`.
- **Status and releases.** Put status items in a weather box. Leave release items to the ticker, unless a release is a story.
- **Links.** Write a link only through the picks. Every link gets a note with its source and original headline.

## Images

- Use about one image for each six cards.
- An image must show the story: a photo, a screenshot, a chart or a diagram.
- Never use a logo, a title card with the headline in it, or a house illustration. Most share images are title cards, so look in the article first.
- Give each image `alt` text that says what the image shows.
- Give the lead an image from its article when one exists. Without one, the lead is text only.
- The page loads each image from the publisher and credits the source. Never copy an image into the site.

## Build gates

The build stops on each of these. Fix the picks, then render again:

- a duplicate, unknown or earlier item, or an unknown key
- a generic image, or an image without `alt`
- a deck over 25 words
- a `flow` in an edition with fewer than 8 items
- a link that is not `https://`, a path on the site, or `#anchor`
- a word from the deny list

## Check

Use a browser that you can control, such as the T3 browser preview or Playwright.

1. Serve the public folder: `uv run --no-project python -m http.server <port> --bind 127.0.0.1 --directory $SITE/public`. Start it detached, so that it lives after the turn.
2. Open `http://127.0.0.1:<port>/`. In T3 Code, use `preview_open`.
3. Measure the columns. Each column total must be close to the others. The lead and the side column must have about the same height:
   ```js
   [...document.querySelectorAll(".edition")].map(ed => [ed.dataset.section,
     [...ed.querySelectorAll(".flow.packed > .col")].map(c => [...c.children].reduce((s, x) => s + x.scrollHeight, 0)),
     ed.querySelector(".lead").offsetHeight, ed.querySelector(".side")?.scrollHeight])
   ```
   Images load lazily. Do not wait for all of them, because images below the screen never load in a hidden tab.
4. Look at the front page of each edition and at the end of each flow.
5. Switch to dark mode and look again. Then switch back to the system setting.
6. Set the width to a phone, such as 390 pixels. Check that the page does not scroll sideways. Then set it back.
7. Open `/issues/` and check that the new issue is at the top.
8. If a box holds one line, or a column ends far above the others, change the picks and render again.
   If the side column is much taller than the lead, move a side story or the quote into the flow.

## Publish

Any static host can serve `public/`. The README of this repository describes the Cloudflare Worker of news.yarden-zamir.com.

After the deploy, check the live site:

- The home page title has the new issue number and date.
- `/issues/`, `/feed.xml` and `/sitemap.xml` list the new issue.
- A missing page returns status 404.
