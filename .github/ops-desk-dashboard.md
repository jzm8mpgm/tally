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

---

After printing the dashboard, post a status update to ops-desk.

You own all the decisions: pick a `status` of `ok`, `warn`, or `error` based on what you actually found; write a one-line `summary` that captures the most important thing right now; and include whichever 2–5 numbers from this analysis are worth tracking over time as named fields (e.g. `open_issues`, `open_prs`, `tests_passing`, `backlog_items`, `commits_last_7d`). Leave out anything that isn't genuinely signal. If the situation is so routine there's nothing worth flagging, a clean `ok` with a quiet summary is still useful data.

Consider frequency: if the project is in a quiet period, say so in the summary. If something needs attention, make the status reflect that.

Post the update using this pattern — it includes the full dashboard text as a `report` field so it can be viewed by clicking through on ops-desk. Use Python to build the JSON safely (handles newlines and quotes in the report):

First, write the full dashboard output you printed above to `/tmp/tally_report.md`.

Then run:

```bash
python3 -c "
import json, os, subprocess
report = open('/tmp/tally_report.md').read()
payload = {
    'status': 'FILL_IN',
    'summary': 'FILL_IN',
    'report': report,
    # include your chosen metric fields, e.g.:
    # 'open_issues': 0,
    # 'open_prs': 0,
    # 'commits_last_7d': 16,
    # 'tests_passing': 37,
    # 'backlog_items': 5,
}
open('/tmp/tally_payload.json', 'w').write(json.dumps(payload))
"

curl -s -o /dev/null -w "%{http_code}" -X POST \
  https://ops-desk.mattmorgan.workers.dev/status/tally \
  -H "Authorization: Bearer $OPS_DESK_TOKEN" \
  -H "Content-Type: application/json" \
  -d @/tmp/tally_payload.json
```

Fill in the real status, summary, and metric values before running. Report the HTTP response code after posting.
