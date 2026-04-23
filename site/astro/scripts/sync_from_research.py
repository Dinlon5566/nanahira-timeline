#!/usr/bin/env python3
"""ETL: convert /home/kali/project/nanahira/research/albums/*.json +
albums_index.json into site/src/data/albums.json + tracks.json (site schema)."""
import json, re
from pathlib import Path

RESEARCH = Path('/home/kali/project/nanahira/research')
SITE_DATA = Path(__file__).resolve().parent.parent / 'src' / 'data'
SITE_DATA.mkdir(parents=True, exist_ok=True)

INDEX = json.loads((RESEARCH / 'albums_index.json').read_text())
ALBUMS_DIR = RESEARCH / 'albums'

# catalog prefix → publisher/circle name
PUBLISHER_MAP = {
    'CFCD': 'Confetto', 'COFB': 'Confetto', 'COMG': 'Confetto',
    'CO7U': 'Confetto', 'NNSU': 'Confetto',
    'KCCD': 'ななひら × かめりあ',
    'LCCD': 'Lovelicot',
    'PMCD': "pomme'tto",
    'NNPC': 'Nanapomi', 'NNMM': 'ななmega',
    'NLCD': 'forestpireo',
    'KTHT': '秋葉工房',
    'CHS': 't+pazolite (C.H.S)',
    'NBDL': 'Notebook Records',
    'TNKC': 'Trinity Note',
    'MMCD': '556mm',
    'HLZY': 'Halozy', 'HLEX': 'Halozy',
    'DWCD': 'DiGiTAL WiNG',
    'AMRC': 'Amateras Records', 'AMRS': 'Amateras Records', 'AMRM': 'Amateras Records', 'ARMM': 'Amateras Records',
    'IO':   'IOSYS',
    'CHCF': 'Alice\'s Emotion',
}

LEAD_ROLES = {"Performer", "Featured Artist", "Artist"}

def pretty_publisher(catalog: str, roles: list, her_ratio: str) -> str | None:
    if not catalog or catalog in ('N/A', 'TIE-IN', 'DIGITAL-ONLY'):
        return None
    if '-' in catalog:
        prefix = catalog.split('-')[0]
    else:
        prefix = re.match(r'^[A-Z]+', catalog).group(0) if re.match(r'^[A-Z]+', catalog) else ''
    return PUBLISHER_MAP.get(prefix)

def extract_event(info: dict) -> str | None:
    rd = info.get('Release Date', '') or ''
    # formats: "Dec 29, 2017 C93" or "Apr 30, 2023 M3-2023春"
    m = re.search(r'\d{4}\s+(.+)$', rd)
    if m:
        ev = m.group(1).strip()
        # known event patterns
        if re.match(r'^(C\d+|M3|Reitaisai|Mikotoba|Comiket)', ev, re.I):
            return ev
    return None

def her_ratio(manual) -> str:
    if manual == 'ALL': return 'all'
    if manual == 'NONE' or manual is None: return 'none' if manual == 'NONE' else 'some'
    if isinstance(manual, list):
        return 'some' if manual else 'none'
    return 'some'

def display_role(roles: list, ratio: str, catalog: str) -> str:
    if catalog == 'TIE-IN':
        return 'tiein'
    if catalog == 'DIGITAL-ONLY':
        return 'lead' if ratio == 'all' else 'guest'
    # If she's on every track → lead (it's her album / a unit album)
    if ratio == 'all':
        return 'lead'
    return 'guest'

def cover_info(album_id: str) -> dict | None:
    """Look up public/covers/album/{id}.jpg — populated later."""
    p = Path(__file__).resolve().parent.parent / 'public' / 'covers' / 'album' / f'{album_id}.jpg'
    if p.exists():
        return {
            'url': f'covers/album/{album_id}.jpg',
            'source': 'local',
            'size': p.stat().st_size,
        }
    return None

def track_cover(track_id: str) -> dict | None:
    p = Path(__file__).resolve().parent.parent / 'public' / 'covers' / 'track' / f'{track_id}.jpg'
    if p.exists():
        return {
            'url': f'covers/track/{track_id}.jpg',
            'source': 'local',
            'size': p.stat().st_size,
        }
    return None

albums_out = []
tracks_out = []

for entry in INDEX:
    aid = entry['album_id']
    path = ALBUMS_DIR / f'{aid}.json'
    if not path.exists():
        continue
    d = json.loads(path.read_text())
    info = d.get('info', {})
    tl = d.get('tracklist', [])
    manual = d.get('manual_her_tracks')
    ratio = her_ratio(manual)

    # Build her_tracks set for matching
    her_pairs: set[tuple[int, int]] = set()
    if manual == 'ALL':
        for t in tl:
            her_pairs.add((t.get('disc', 1), t.get('track')))
    elif manual == 'NONE' or manual is None:
        pass
    elif isinstance(manual, list):
        # Either [int] or [[disc, track]]
        pair_mode = any(isinstance(x, list) for x in manual)
        if pair_mode:
            for x in manual:
                if isinstance(x, list) and len(x) == 2:
                    her_pairs.add((int(x[0]), int(x[1])))
        else:
            nums = {int(x) for x in manual}
            for t in tl:
                if t.get('track') in nums:
                    her_pairs.add((t.get('disc', 1), t.get('track')))

    her_count = len(her_pairs)
    ratio = 'all' if her_count == len(tl) and len(tl) > 0 else ('some' if her_count > 0 else 'none')

    catalog = entry.get('catalog') or info.get('Catalog Number') or ''
    publisher = pretty_publisher(catalog, entry.get('roles') or [], ratio)
    event = extract_event(info)
    fmt = info.get('Media Format') or info.get('Publish Format')

    album_obj = {
        'id': aid,
        'title_jp': entry.get('title_jp') or entry.get('title') or '(untitled)',
        'title_romaji': entry.get('title_romaji') or None,
        'title_en': entry.get('title') if entry.get('title') != entry.get('title_jp') else None,
        'release_date': entry.get('date') or '',
        'catalog': catalog,
        'event': event,
        'format': fmt,
        'publisher': publisher,
        'tracks_count': len(tl),
        'her_tracks_count': her_count,
        'her_ratio': ratio,
        'roles': entry.get('roles') or [],
        'display_role': display_role(entry.get('roles') or [], ratio, catalog),
        'cover': cover_info(aid),
        'sources': {
            'vgmdb': entry.get('url') if 'vgmdb.net' in (entry.get('url') or '') else None,
        },
        'external_links': d.get('external_links') or {},
    }
    albums_out.append(album_obj)

    # Emit all tracks (her or not)
    for t in tl:
        disc = t.get('disc', 1)
        tno = t.get('track')
        tid = f"ALB{aid}_D{disc}T{tno}"
        is_her = (disc, tno) in her_pairs
        tracks_out.append({
            'id': tid,
            'album_id': aid,
            'disc': disc,
            'track_no': tno,
            'title': t.get('title', ''),
            'duration': t.get('duration') or None,
            'her': is_her,
            'her_role': 'lead' if is_her else None,
            'vocal_credits': [],
            'cover': track_cover(tid),
        })

albums_out.sort(key=lambda x: x['release_date'] or '0000')
tracks_out.sort(key=lambda x: (x['album_id'], x['disc'], x['track_no']))

(SITE_DATA / 'albums.json').write_text(json.dumps(albums_out, ensure_ascii=False, indent=2))
(SITE_DATA / 'tracks.json').write_text(json.dumps(tracks_out, ensure_ascii=False, indent=2))

# Summary
her_total = sum(1 for t in tracks_out if t['her'])
print(f'albums: {len(albums_out)}')
print(f'tracks total: {len(tracks_out)}; her: {her_total}')
print(f'display_role: {sum(1 for a in albums_out if a["display_role"]=="lead")} lead / '
      f'{sum(1 for a in albums_out if a["display_role"]=="guest")} guest / '
      f'{sum(1 for a in albums_out if a["display_role"]=="tiein")} tiein')
print(f'covers: {sum(1 for a in albums_out if a["cover"])} album / '
      f'{sum(1 for t in tracks_out if t["cover"])} track')
