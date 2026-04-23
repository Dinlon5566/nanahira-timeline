#!/usr/bin/env python3
"""List albums/singles that still lack a cover, grouped by year for easy manual fetching."""
import json
from pathlib import Path
from collections import defaultdict

ROOT = Path(__file__).resolve().parent.parent
ALB_COV = ROOT / 'public' / 'covers' / 'album'
TRK_COV = ROOT / 'public' / 'covers' / 'track'

albums = json.loads((ROOT / 'src' / 'data' / 'albums.json').read_text())
tracks = json.loads((ROOT / 'src' / 'data' / 'tracks.json').read_text())

# For each album, figure out if it has a cover (album-level OR track-level when 1-track)
tracks_by_album = defaultdict(list)
for t in tracks:
    tracks_by_album[t['album_id']].append(t)

missing = []
for a in albums:
    aid = a['id']
    alb_jpg = ALB_COV / f'{aid}.jpg'
    tl = tracks_by_album.get(aid, [])
    single = len(tl) == 1
    trk_jpg = TRK_COV / f'{tl[0]["id"]}.jpg' if tl else None
    has = alb_jpg.exists() or (single and trk_jpg and trk_jpg.exists())
    if not has:
        missing.append(a)

# group by year
by_year = defaultdict(list)
for a in missing:
    y = (a['release_date'] or '0000')[:4]
    by_year[y].append(a)

lines = ['# Missing covers — manual fetch list', '']
lines.append(f'**{len(missing)}** of {len(albums)} albums still lack covers.\n')
lines.append('**Workflow**: save image as JPG and drop into:')
lines.append('- `public/covers/album/<album_id>.jpg` for regular albums')
lines.append('- `public/covers/track/<track_id>.jpg` for single-track releases (track_id shown below)')
lines.append('- Then re-run: `python3 scripts/sync_from_research.py`')
lines.append('')
for y in sorted(by_year.keys(), reverse=True):
    lines.append(f'## {y} ({len(by_year[y])})')
    lines.append('')
    for a in by_year[y]:
        catalog = a['catalog'] if a['catalog'] not in ('N/A','') else '—'
        kind = 'album'
        trackid = ''
        tl = tracks_by_album.get(a['id'], [])
        if len(tl) == 1:
            kind = 'track'
            trackid = tl[0]['id']
        file_target = f'album/{a["id"]}.jpg' if kind == 'album' else f'track/{trackid}.jpg'
        vgmdb = a['sources'].get('vgmdb') or ''
        title = a['title_jp'][:60]
        lines.append(f'- `{file_target}` · `{catalog}` · [{title}]({vgmdb})' if vgmdb else f'- `{file_target}` · `{catalog}` · {title}')
    lines.append('')

out = ROOT / 'scripts' / 'missing_covers.md'
out.write_text('\n'.join(lines))
print(f'wrote {out} — {len(missing)} missing')
print(f'breakdown by year:')
for y in sorted(by_year.keys(), reverse=True):
    print(f'  {y}: {len(by_year[y])}')
