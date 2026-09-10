Run the following commands in parallel and format the results as a short scannable dashboard:

1. `gh issue list --repo jzm8mpgm/tally --state open --json number,title,labels,createdAt`
2. `gh pr list --repo jzm8mpgm/tally --state open --json number,title,createdAt,reviews,statusCheckRollup`
3. `git log main --since="7 days ago" --oneline`
4. `gh repo view jzm8mpgm/tally --json stargazerCount,watchers,forkCount`
5. `python3 -m unittest discover -s tests -t . 2>&1 | tail -5`

Also read these files in parallel:
- `docs/BACKLOG.md` — show only the open (not Done) items, one line each, in priority order
- `docs/JOURNAL.md` — show the most recent entry only (date + first paragraph)

Format the output as:

## Tally Dashboard — {today's date}

### Issues
Group open issues by bug vs feature request (use labels; if unlabelled, use your best judgement from the title). List each as `#number title`. If none, say "none open".

### Pull Requests
For each open PR: title, check status (passing/failing/pending), and how long it has been open. If none, say "None open".

### PRs awaiting your review (>1 week)
PRs open more than 7 days with no review from Matt Morgan. If none, say "None".

### Commits to `main` — last 7 days
Count + short list of commit summaries (show up to 5, then "*(N more)*" if there are more).

### Tests
Pass / fail / count. If any fail, name them.

### Backlog
Numbered open items in priority order.

### Latest Journal Entry
Date + first paragraph of the most recent entry.

### GitHub Stats
Stars / Watchers / Forks in a small table.
