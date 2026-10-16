# news

The changelorg Gazette at https://news.yarden-zamir.com: a weekly newspaper that an AI agent edits from [changelorg](https://changelorg.yarden-zamir.com) feeds.
This repository holds the renderer, the agent skill, and the site with every issue.

## How it works

1. [changelorg](https://github.com/Yarden-zamir/changeLorg) collects news from feeds, release pages and status pages into profiles, such as `dev` and `games`.
2. `changelorg_items.py` reads the profiles through the changelorg CLI and writes an items file.
3. An AI agent reads the items, ranks them, and writes a picks file: the lead, headlines, decks, images and boxes.
4. `gazette.py render` checks the picks and renders one static HTML issue.
   It writes `covered.json` next to the issue, the list of every item that the issue shows.
   Later issues read these files, so that no story appears twice.
5. `gazette.py site` builds the home page, the archive, the Atom feed, the sitemap and the 404 page.
6. A Cloudflare Worker serves the static files.

Each story links to its source. Images load from the publishers' websites and credit them. The site sets no cookies.

Readers can sign in to changelorg with GitHub from the page. The page then marks what they viewed and shelved in their own changelorg.
To mark the items of a block as viewed or shelved, point at the block, or press and hold it on a phone. The changes go straight to changelorg.
[`SKILL.md`](skills/newspaper/SKILL.md#reader-sync) describes how a block finds its items.

## Make your own paper

You need [uv](https://docs.astral.sh/uv/), Node.js for the deploy, and an agent that reads skills, such as Claude Code.

1. Open https://changelorg.yarden-zamir.com and sign in with GitHub.
2. Add sources in the source editor. One profile becomes one edition of the paper.
   To start from the sources of this paper, open a share link and import the sources into a new profile:
   [dev](https://changelorg.yarden-zamir.com/share/m6fTRqPU_Tpy8oo6hBwdCg), [games](https://changelorg.yarden-zamir.com/share/iEZKXyhEwHhL264-p53VWg).
3. Clone this repository and give the skill to your agent:
   ```sh
   git clone https://github.com/Yarden-zamir/news.git
   ln -s "$PWD/news/skills/newspaper" ~/.claude/skills/newspaper
   ```
4. Make an empty site folder for your paper, outside this repository, and put it in git:
   ```sh
   mkdir -p ~/my-paper/public/issues ~/my-paper/desk && git -C ~/my-paper init
   ```
5. Ask the agent: "Make an issue of the Gazette in ~/my-paper from my changelorg profiles dev and games."
   The skill signs the changelorg CLI in, writes the items and picks, renders the issue and checks it.
   The first sign-in prints a link and a code. Open the link and approve.

[`skills/newspaper/SKILL.md`](skills/newspaper/SKILL.md) describes the setup, the steps, the file formats and the editorial rules.

## Repository layout

```text
skills/newspaper/          the agent skill
├── SKILL.md               steps, file formats, editorial rules and checks
├── changelorg_items.py    changelorg profiles → items file
├── gazette.py             items file + picks file → issue; issues → site files
├── page_images.py         lists the images of an article, to pick one
├── example-picks.json     the picks of issue 1
└── assets/fonts/          Bricolage Grotesque and JetBrains Mono (SIL Open Font License)
site/                      news.yarden-zamir.com
├── desk/<date>/picks.json the editorial choices of each issue
├── public/                the deployed files: issues, archive, feed, sitemap, 404 page, fonts, share card
├── schedule.md            the steps of the weekly run
└── wrangler.jsonc         the Cloudflare Worker settings
```

`site/desk/<date>/items.json` and `site/deny.txt` stay out of git. The items file holds read and saved marks.
The deny list holds words that must never appear on the public page.

## Deployment

The site is a Cloudflare Worker with static assets only. It runs no Worker code.

- Worker name: `news-site`. Custom domain: `news.yarden-zamir.com`. Settings: [`site/wrangler.jsonc`](site/wrangler.jsonc).
- `not_found_handling` is `404-page`, so a missing page returns `public/404.html` with status 404.
- `preview_urls` is off. The Worker has no preview URLs.
- Cloudflare Web Analytics counts visits. Cloudflare adds its script at the edge. It sets no cookies.
- Reader sync needs the changelorg deployment to allow this site: `https://news.yarden-zamir.com` in its CORS origins, and in the `--whitelist-domain` of its oauth2-proxy. The `compose.yml` of [changeLorg](https://github.com/Yarden-zamir/changeLorg) sets both.

To deploy, run this from the repository root:

```sh
cd site && npx --yes wrangler@4.151.0 deploy --config wrangler.jsonc
```

If the Cloudflare login expired, run `npx --yes wrangler@4.151.0 login` first. The Cloudflare account must own the `yarden-zamir.com` zone.

To host your own paper on Cloudflare, copy `wrangler.jsonc` into your site folder. Then change `name` and the `pattern` of the route to your Worker name and domain.
Any static host also works: serve the `public/` folder, and serve `404.html` for missing pages.

The deny list is local only. In the worktree layout of the maintainer, it is `_shared/site/deny.txt`, and a git hook links it to `site/deny.txt`.

## Weekly schedule

A T3 Code scheduled task makes a new issue every Sunday at 09:00 local time. It looks back 8 days.
Its prompt is one line that points to [`site/schedule.md`](site/schedule.md), so the steps live in this repository.
The run renders the issue, checks it in a browser, deploys it, checks the live site, then commits and pushes.

## License

The code is under the [MIT License](LICENSE). The fonts are under the SIL Open Font License: see `skills/newspaper/assets/fonts/OFL-*.txt`.
Headlines and summaries link to their sources. The articles and images belong to their publishers.
