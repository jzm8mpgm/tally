Run the following commands in parallel:

1. `gh issue list --repo jzm8mpgm/tally --state open --json number,title,labels,createdAt`
2. `gh pr list --repo jzm8mpgm/tally --state open --json number,title,createdAt,reviews,statusCheckRollup`
3. `git fetch origin main && git log origin/main --since="7 days ago" --oneline`
4. `gh repo view jzm8mpgm/tally --json stargazerCount,watchers,forkCount`
5. `python3 -m unittest discover -s tests -t . 2>&1 | tail -5`
6. `gh api repos/jzm8mpgm/tally/traffic/clones --jq '{count, uniques}'` (14-day rolling window; requires push access, which the authenticated account has)

Also read these files in parallel:
- `docs/BACKLOG.md` — the open (not Done) items, one line each, in priority order
- `docs/JOURNAL.md` — the most recent entry only (date + first paragraph)

Format the output using the shared skeleton — see `Dashboards/FORMAT.md` in `~/Projects/Dashboards`: fixed section order, alerts first and only when non-empty, omit any section with nothing to show.

## Tally Dashboard — {today's date}

### ⚠ Alerts
Only include this section if any test fails, or any open PR has a failing check. List each plainly. Omit the whole section otherwise.

### Status
Tests: pass/fail counts. If any fail, name them (and they belong in Alerts too).

### Activity
One line: `Issues open: N · PRs open: N · Commits to origin/main (7 days): N`, followed by:
- Open issues, grouped bug vs feature request (use labels; if unlabelled, best judgement from the title)
- Open PRs: title, check status (passing/failing/pending), how long open
- PRs awaiting review >1 week: open more than 7 days with no review from GitHub user `jzm8mpgm` (Matt Morgan)
- Commit list: up to 5 summaries, then "*(N more)*" if more

### Metrics
GitHub Stats as a small table: Stars / Watchers / Forks / Clones (14 days, total and unique).

### Open Items
Backlog — numbered open items from `docs/BACKLOG.md`, in priority order.

### Notes
Latest Journal Entry — date + first paragraph of the most recent entry in `docs/JOURNAL.md`.

### Stack
Static — only update if the stack actually changes:
- GitHub — repo hosting, releases, CI (macOS test runner) — https://github.com/jzm8mpgm/tally

### Links
- Repository — https://github.com/jzm8mpgm/tally

## Publish the hosted artifact

Render the report above into the shared shell (`Dashboards/template/dashboard-artifact.html.tmpl`'s structure — same sections/order, accent `#4A63E0` light / `#7B93FF` dark). The header must include the "Run now ↗" button linking to `https://claude.ai/code/routines/trig_018tiWit297qbHwwcjsR93nq` (a published page can't fire a cloud run itself, so this deep-links to the routine's own page where one click does) — keep rendering it every time, it's easy to drop when regenerating the page from scratch. Publish via the `Artifact` tool with `url` set to `https://claude.ai/code/artifact/7fb1aebe-650f-4ee9-b948-a84342fc0c36` so it updates in place.

Then refresh the hub's registry: `Artifact` `write_db`, url `https://claude.ai/code/artifact/d67645f3-650a-4668-99dd-b9aac1409f82`, `collection: "dashboards"`, `doc_id: "tally"`, `data: {name: "Tally", url: "https://claude.ai/code/artifact/7fb1aebe-650f-4ee9-b948-a84342fc0c36", last_updated: <now, ISO>, has_alerts: <true if the Alerts section is non-empty>}`.
