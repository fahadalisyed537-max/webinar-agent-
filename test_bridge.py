"""Test the bridge with cached scraper data."""
import sys
sys.path.insert(0, r'D:\real-lead-scraper')
from leadgen_bridge import transform_lead, write_leadgen_format
import json
from pathlib import Path

out_dir = Path(r'D:\real-lead-scraper\scraped_leads')
files = sorted(out_dir.glob('qualified_*.json'), key=lambda f: f.stat().st_mtime)
if not files:
    files = sorted(out_dir.glob('all_*.json'), key=lambda f: f.stat().st_mtime)

if files:
    latest = files[-1]
    with open(latest) as f:
        raw = json.load(f)
    print('Read ' + str(len(raw)) + ' leads from ' + latest.name)
    transformed = [transform_lead(l) for l in raw[:3]]
    for t in transformed:
        print('  ' + t['first_name'] + ' ' + t['last_name'] + ' | ' + t['title'] + ' @ ' + t['company'] + ' | ' + t['email'] + ' | Score: ' + str(t['score']))
    paths = write_leadgen_format(transformed)
    print('Files written: ' + str(paths))
else:
    print('No cached files found')
