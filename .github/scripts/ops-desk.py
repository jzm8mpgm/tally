import subprocess, json, os, urllib.request
from datetime import datetime, timezone


def run(cmd):
    r = subprocess.run(cmd, shell=True, capture_output=True, text=True)
    return r.stdout.strip()


# --- collect ---
issues = json.loads(run('gh issue list --repo jzm8mpgm/tally --state open --json number,title,labels,createdAt') or '[]')
prs    = json.loads(run('gh pr list --repo jzm8mpgm/tally --state open --json number,title,createdAt,statusCheckRollup') or '[]')
repo   = json.loads(run('gh repo view jzm8mpgm/tally --json stargazerCount,forkCount') or '{}')

commits_raw = run('git log main --since="7 days ago" --oneline')
commits = [l for l in commits_raw.splitlines() if l]

test_proc = subprocess.run('python3 -m unittest discover -s tests -t . 2>&1', shell=True, capture_output=True, text=True)
test_out  = (test_proc.stdout + test_proc.stderr).strip()
tests_ok  = test_proc.returncode == 0

backlog_items = 0
try:
    backlog_items = open('docs/BACKLOG.md').read().count('- [ ]')
except FileNotFoundError:
    pass

journal_snippet = ''
try:
    lines = open('docs/JOURNAL.md').read().strip().splitlines()
    journal_snippet = next((l for l in lines if l.strip()), '')
except FileNotFoundError:
    pass

# --- status ---
if not tests_ok:
    status  = 'error'
    summary = f'Tests failing — {len(issues)} open issues, {len(prs)} open PRs'
elif len(issues) > 3:
    status  = 'warn'
    summary = f'{len(issues)} open issues need attention, {len(commits)} commits this week'
else:
    status  = 'ok'
    summary = f'{len(commits)} commits this week, {len(issues)} issues, {len(prs)} PRs'

# --- report ---
today = datetime.now().strftime('%Y-%m-%d')
now   = datetime.now(timezone.utc)


def fmt_issues(lst):
    if not lst:
        return 'None open.'
    out = []
    for i in lst:
        labels = [l['name'] for l in i.get('labels', [])]
        tag = f' [{", ".join(labels)}]' if labels else ''
        out.append(f"#{i['number']} {i['title']}{tag}")
    return '\n'.join(out)


def fmt_prs(lst):
    if not lst:
        return 'None open.'
    out = []
    for p in lst:
        created = datetime.fromisoformat(p['createdAt'].replace('Z', '+00:00'))
        age = (now - created).days
        checks = p.get('statusCheckRollup') or []
        if not checks:
            cs = 'no checks'
        elif all(c.get('conclusion') == 'SUCCESS' or c.get('state') == 'SUCCESS' for c in checks):
            cs = 'passing'
        elif any(c.get('conclusion') == 'FAILURE' or c.get('state') == 'FAILURE' for c in checks):
            cs = 'FAILING'
        else:
            cs = 'pending'
        out.append(f"#{p['number']} {p['title']} — {cs}, {age}d old")
    return '\n'.join(out)


commit_list = '\n'.join(commits[:5])
if len(commits) > 5:
    commit_list += f'\n*(+{len(commits)-5} more)*'

test_summary = test_out.splitlines()[-1] if test_out else ''

report = f"""## Tally Dashboard — {today}

### Issues
{fmt_issues(issues)}

### Pull Requests
{fmt_prs(prs)}

### Commits to `main` — last 7 days
{len(commits)} commits
{commit_list}

### Tests
{'Passing' if tests_ok else 'FAILING'}
{test_summary}

### Backlog
{backlog_items} open items

### Latest Journal Entry
{journal_snippet}

### GitHub Stats
Stars: {repo.get('stargazerCount', '?')} | Forks: {repo.get('forkCount', '?')}"""

payload = {
    'status':          status,
    'summary':         summary,
    'report':          report,
    'open_issues':     len(issues),
    'open_prs':        len(prs),
    'commits_last_7d': len(commits),
    'backlog_items':   backlog_items,
}

req = urllib.request.Request(
    'https://ops-desk.mattmorgan.workers.dev/status/tally',
    data=json.dumps(payload).encode(),
    headers={
        'Authorization': f'Bearer {os.environ["OPS_DESK_TOKEN"]}',
        'Content-Type':  'application/json',
    },
    method='POST',
)
with urllib.request.urlopen(req) as resp:
    print(f'ops-desk: {resp.status}')
