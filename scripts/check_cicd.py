import urllib.request
import json
import sys

url = 'https://api.github.com/repos/harshith1432/setu/actions/runs?per_page=6'
req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})

try:
    with urllib.request.urlopen(req) as resp:
        data = json.loads(resp.read().decode('utf-8'))
        runs = data.get('workflow_runs', [])
        print(f"Total latest runs retrieved: {len(runs)}\n")
        for r in runs:
            w_name = r.get('name', 'Workflow')
            msg = r.get('head_commit', {}).get('message', '').split('\n')[0]
            sha = r.get('head_sha', '')[:7]
            status = r.get('status')
            conclusion = r.get('conclusion')
            html_url = r.get('html_url')
            created_at = r.get('created_at')
            print(f"[{status.upper()}] Conclusion: {str(conclusion).upper()}")
            print(f"  Workflow: {w_name}")
            print(f"  Commit:   {sha} - {msg}")
            print(f"  Time:     {created_at}")
            print(f"  URL:      {html_url}\n")
except Exception as e:
    print("Error fetching GitHub Actions runs:", e)
