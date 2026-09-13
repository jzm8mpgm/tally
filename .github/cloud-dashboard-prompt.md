# Weekly dashboard — cloud routine prompt

This is the prompt given to the Claude Code cloud routine ("tally-weekly-dashboard")
that runs this every Sunday and emails the result. It is checked in so the
automation is auditable like everything else here, but the routine's own
config is the thing that actually runs it — editing this file does not
change the routine; update the routine too if you change this.

It differs from the local `/dashboard` command (`.claude/commands/dashboard.md`)
because the cloud sandbox has no `gh` CLI — GitHub access there is through an
MCP connector instead, and it can't reach the traffic/clones endpoint at all
(see `.github/workflows/clone-stats.yml`, which feeds that one number in as
a plain file). Both follow the shared skeleton in `Dashboards/FORMAT.md`
(`~/Projects/Dashboards` locally, or ask for it if this session doesn't have
that repo checked out) so the two stay in the same shape even though the
data-gathering differs.

---

Produce this week's Tally dashboard, email it, and update its hosted page.
This repo (jzm8mpgm/tally) is already cloned into your working directory.

There is no `gh` CLI here — use the GitHub MCP tools instead (search the tool
catalog if you're unsure of exact names or fields). Everything else is Bash
or Read against the local checkout.

Gather, in parallel where possible:

1. Open issues in jzm8mpgm/tally — number, title, labels, created date.
2. Open PRs in jzm8mpgm/tally — number, title, created date, and check/review
   status if the MCP tools expose it. If they don't, say so rather than
   guessing — don't fabricate a check status.
3. `git fetch origin main && git log origin/main --since="7 days ago" --oneline`
4. Repo stats — stars, watchers, forks — via GitHub MCP.
5. Clone traffic — read `docs/metrics/clones.json` (committed weekly by the
   `clone-stats` GitHub Actions workflow, since nothing available here can
   reach that endpoint directly). Report `count` and `uniques`. If
   `fetched_at` is more than ~8 days old, say so explicitly — it likely
   means that workflow failed and the number is stale, not current.
6. `python3 -m unittest discover -s tests -t . 2>&1 | tail -5`
7. Read `docs/BACKLOG.md` — open (not Done) items only, numbered, in
   priority order.
8. Read `docs/JOURNAL.md` — most recent entry only (date + first paragraph).

If any single step fails, don't abort the rest — note the failure in that
section and keep going; a partial dashboard is more useful than none.

Format the result using the shared skeleton — fixed section order, alerts
first and only when non-empty, omit a section entirely rather than writing
"none"/"N/A":

```
## Tally Dashboard — {today's date}

### ⚠ Alerts
Only if any test fails, or any open PR has a failing check. Omit otherwise.

### Status
Tests: pass / fail / count. Name any failures.

### Activity
One line: `Issues open: N · PRs open: N · Commits to origin/main (7 days): N`,
then:
- Open issues, grouped bug vs feature request (labels, or best judgement
  from the title if unlabelled)
- Open PRs: title, check status if available, how long open
- PRs awaiting review >1 week (no review from GitHub user `jzm8mpgm`)
- Commits: up to 5 summaries, then "*(N more)*" if there are more

### Metrics
GitHub Stats: Stars / Watchers / Forks / Clones (14d) / Unique cloners,
small table.

### Open Items
Backlog — numbered open items, priority order.

### Notes
Latest Journal Entry — date + first paragraph.

### Stack
Static — only update if the stack actually changes:
- GitHub — repo hosting, releases, CI (macOS test runner) — https://github.com/jzm8mpgm/tally

### Links
- Repository — https://github.com/jzm8mpgm/tally
```

Send it via the Gmail MCP tool to **mattmorgan@me.com**, subject
`Tally Dashboard — {today's date}`.

Then publish the hosted page: render the same content into the shared shell
(`Dashboards/template/dashboard-artifact.html.tmpl`'s structure — accent
`#4A63E0` light / `#7B93FF` dark). The header must include the "Run now ↗"
button linking to `https://claude.ai/code/routines/trig_018tiWit297qbHwwcjsR93nq`
(a published page can't fire a cloud run itself, so this deep-links to the
routine's own page where one click does) — keep rendering it every run, it's
easy to drop when regenerating the page from scratch. Use the `Artifact`
tool to publish it with `url` set to
`https://claude.ai/code/artifact/7fb1aebe-650f-4ee9-b948-a84342fc0c36`
so it updates in place rather than creating a new page.

Then refresh the hub's registry: `Artifact` `write_db`, url
`https://claude.ai/code/artifact/d67645f3-650a-4668-99dd-b9aac1409f82`,
`collection: "dashboards"`, `doc_id: "tally"`, `data: {name: "Tally", url:
"https://claude.ai/code/artifact/7fb1aebe-650f-4ee9-b948-a84342fc0c36",
last_updated: <now, ISO 8601>, has_alerts: <true if the Alerts section is
non-empty>}`.

End your final message with whether the email send succeeded and whether
both artifact updates succeeded.
