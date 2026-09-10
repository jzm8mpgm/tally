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
a plain file).

---

Produce this week's Tally dashboard and email it. This repo (jzm8mpgm/tally)
is already cloned into your working directory.

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

Format the result exactly like this:

```
## Tally Dashboard — {today's date}

### Issues
Group by bug vs feature request (labels, or best judgement from the title
if unlabelled). List each as `#number title`. "None open" if empty.

### Pull Requests
For each: title, check status if available, how long it's been open.
"None open" if empty.

### PRs awaiting your review (>1 week)
PRs open more than 7 days with no review from GitHub user `jzm8mpgm`
(Matt Morgan). "None" if empty.

### Commits to `origin/main` — last 7 days
Count + up to 5 summaries, then "*(N more)*" if there are more.

### Tests
Pass / fail / count. Name any failures.

### Backlog
Numbered open items, priority order.

### Latest Journal Entry
Date + first paragraph.

### GitHub Stats
Stars / Watchers / Forks / Clones (14d) / Unique cloners, small table.
```

Send it via the Gmail MCP tool to **drmattmorgan@gmail.com**, subject
`Tally Dashboard — {today's date}`. End your final message with whether the
send succeeded.
