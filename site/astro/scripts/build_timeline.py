#!/usr/bin/env python3
"""Aggregate albums + milestones → timeline.json (year-bucketed, sorted desc)."""
import json
from pathlib import Path
from collections import defaultdict

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / 'src' / 'data'

albums = json.loads((DATA / 'albums.json').read_text())
milestones = json.loads((DATA / 'milestones.json').read_text())

def year_of(date: str) -> int:
    return int((date or '0000')[:4])

year_events = defaultdict(list)
year_release = defaultdict(int)
year_milestone = defaultdict(int)

for a in albums:
    y = year_of(a['release_date'])
    if y == 0:
        continue
    year_events[y].append({
        'type': 'release',
        'date': a['release_date'],
        'album_id': a['id'],
    })
    year_release[y] += 1

for m in milestones:
    y = year_of(m['date'])
    year_events[y].append(m)
    year_milestone[y] += 1

years_out = []
for y in sorted(year_events.keys(), reverse=True):
    evs = year_events[y]
    # sort: date desc; within same date, milestone before release
    evs.sort(key=lambda e: (e['date'], 0 if e['type'] == 'milestone' else 1), reverse=True)
    years_out.append({
        'year': y,
        'release_count': year_release[y],
        'milestone_count': year_milestone[y],
        'events': evs,
    })

timeline = {
    'years': years_out,
    'total_releases': sum(year_release.values()),
    'total_milestones': sum(year_milestone.values()),
}

(DATA / 'timeline.json').write_text(json.dumps(timeline, ensure_ascii=False, indent=2))
print(f"years: {len(years_out)} ({years_out[-1]['year']} – {years_out[0]['year']})")
print(f"total: {timeline['total_releases']} releases, {timeline['total_milestones']} milestones")
