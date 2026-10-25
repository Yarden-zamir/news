# Weekly issue

A T3 Code scheduled task runs these steps every Sunday at 09:00 local time.
The task prompt is one line: "Weekly Riffle: in ~/Github/news/main, run `git pull --ff-only`, then read site/schedule.md and do its steps."
To change the weekly run, change this file.

## Steps

Make this week's issue of The Riffle and publish it on https://news.yarden-zamir.com. The site is public.
Use the `newspaper` skill (its steps, rules, images and Check) and the `riffle` skill.

Paths: `REPO=~/Github/news/main`, `SITE=$REPO/site`, `SKILL=$REPO/skills/newspaper`.
Run each script as `uv run --no-project --python 3.12 python -I $SKILL/<script>`.

1. If `git pull --ff-only` failed, or `git status` shows changes, stop. Reply with the output.
2. Set `DATE` to today's local date as `YYYY-MM-DD`. Run:
   ```sh
   riffle_items.py $SITE/desk/$DATE/items.json --profiles dev,games --days 8
   ```
   If Riffle needs a sign-in, run the login of the `riffle` skill with `--write`, because the user keeps write access.
   Post the link and the code in this thread. Run the login at most three times.
   If the user does not approve, stop, and reply that the issue is skipped because the sign-in was not approved.
3. Read `$SITE/public/issues/*/covered.json`: every item that earlier issues showed. No item from these files may appear again.
4. Add 2 to 5 bonus stories from outside the feed. Find them with web search: news from this week that the feed does not have and that no earlier issue showed.
   Interests: coding agents and Claude Code, T3 Code, herdr and terminals, git and worktrees, Cloudflare, Python and uv, self-hosting, OpenStreetMap, Minecraft and ARC Raiders.
   Read each page. Append each story to `items.json` with `"bonus": true`, the matching section, a unique id such as `bonus-1`, its real URL and its publish time.
   Find the rows of the police blotter of step 6 in the same way. They do not count toward the 5.
5. Find developments: new items that continue a story of an earlier issue. Set `follows` to the URL of the earlier item, and say in the deck what changed.
6. Write `$SITE/desk/$DATE/picks.json`. Read `$SKILL/example-picks.json` for the tone. Write new banners, notes and jokes, not the ones of earlier issues.
   - `issue`: `Vol. 1 · No. N`, where N is the number of folders in `$SITE/public/issues/` plus 1.
   - `page`: `/issues/$DATE/`. `previous`: the page of the newest earlier issue.
   - `site`: `https://news.yarden-zamir.com`. `archive`: `/issues/`. `contact`: `https://github.com/Yarden-zamir/news/issues`. `share_image`: `/og.png`. `audience`: `public`.
   - `description`: one sentence that names the top stories. `about`: copy it from the picks of the previous issue.
   - `motto`: name eight days and the sections. `colophon`: keep the line about cookies from the previous issue.
   - Each image needs `alt`.
   - Put a `blotter` box with the title `Police blotter` in the dev edition of every issue.
     Give it 3 to 5 rows about AI agents and models that did unintended or undesired things. Do not use other bugs or outages.
     Write the rows alarmed but playful: start each `text` with a charge in capitals, such as `BREAK-IN:` or `FALSE ALARM:`.
   - `spotlight` in the dev edition: a band for the source `T3 Code Fork Daily Release`, Yarden's fork of T3 Code. Follow "Spotlight" of the `newspaper` skill.
     Copy `source`, `title`, `link` and `follow` from the picks of the previous issue. Name the releases of the week in `kicker`.
     Make two groups, `Fork changes` and `Upstream changes`, from the sections of the same names in each daily release.
     Give each change a row: its name in `head`, and its sentence from the release notes, word for word, in `text`.
     Copy the sentences from the release page with a script, not by hand. Quote every daily release at least once.
     An `image` is optional: a screenshot of a fork change from a release of the week, without private paths or names.
     If a daily release of the window is not in `items.json`, add it from https://github.com/Yarden-zamir/t3code/releases as a bonus item.
   - `follow`: a Riffle source for each bonus item, the blotter rows included. Follow "Follow sources" of the `newspaper` skill.
     Reuse the source of an earlier issue for the same publication: copy it from the picks of that issue.
     Run `follow_check.py $SITE/desk/$DATE/items.json $SITE/desk/$DATE/picks.json`. Fix every MISSED item. Check every UNSURE item in the feed.
     If no Riffle plugin can catch a publication, open a pull request in `~/Github/riffle` that adds the ability, with tests and spec changes.
     Merge it after its checks pass and its review findings are fixed. Wait until https://riffle.yarden-zamir.com runs it, then run `follow_check.py` again.
7. Render. If the build stops, fix the picks: pick another item, make it a development, or give a bonus item its source. Then render again.
   ```sh
   gazette.py render $SITE/desk/$DATE/items.json $SITE/desk/$DATE/picks.json $SITE/public/issues/$DATE/index.html \
     --history $SITE/public/issues --deny $SITE/deny.txt
   ```
8. Build the site files:
   ```sh
   gazette.py site $SITE/public --site https://news.yarden-zamir.com --title "The Riffle" \
     --description "A weekly paper about developer tools, AI agents and games, edited by an AI agent from open feeds. Every story links to its source."
   ```
9. Do the Check steps of the `newspaper` skill in the T3 browser preview. Fix problems, then do steps 7 and 8 again.
10. Run `git status`. Only these files may change: the new issue folder, the new desk picks file, and the files of step 8.
    If a file of an earlier issue shows as changed or deleted, stop and reply with the list.
11. Deploy:
    ```sh
    cd $SITE && npx --yes wrangler@4.151.0 deploy --config wrangler.jsonc
    ```
    If the wrangler login expired, run `npx --yes wrangler@4.151.0 login`, and post in this thread that it waits for approval in the browser.
12. Check the live site:
    - The title of https://news.yarden-zamir.com/ has the new issue number and date.
    - https://news.yarden-zamir.com/issues/ and https://news.yarden-zamir.com/feed.xml list the new issue.
    - https://news.yarden-zamir.com/no-such-page returns status 404.
    - Right after a deploy, new files can return 404 for a short time. If a check fails, wait one minute, then check again once.
13. Commit with the message `feat(site): issue No. N of $DATE`, and push.
14. Reply in a few lines: the link, the lead headline of each edition, the developments and what they follow, the bonus stories and their Riffle sources, any Riffle pull request,
    the duplicate check line from the build output ("checked against N earlier issues"), and anything that failed.

Do not change Riffle data in this run: no saves and no dismissals.
