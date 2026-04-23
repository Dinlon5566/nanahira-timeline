#!/usr/bin/env python3
"""Bulk-fetch album covers via iTunes Search API (no auth needed).
Resume-safe: skips albums whose cover already exists."""
import json, urllib.request, urllib.parse, re, time, random, sys, argparse, os
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
ALBUMS_DIR = ROOT / 'public' / 'covers' / 'album'
TRACK_DIR = ROOT / 'public' / 'covers' / 'track'
ALBUMS_DIR.mkdir(parents=True, exist_ok=True)
TRACK_DIR.mkdir(parents=True, exist_ok=True)
RESEARCH = Path('/home/kali/project/nanahira/research')
INDEX = json.loads((RESEARCH / 'albums_index.json').read_text())
def cache_path(worker_id: int) -> Path:
    return ROOT / 'scripts' / f'covers_tried_w{worker_id}.json'

SESSION_UA = 'Mozilla/5.0 (Linux) NanahiraSite/1.0'

def itunes_search(q: str, entity: str = 'album', limit: int = 5):
    url = 'https://itunes.apple.com/search?' + urllib.parse.urlencode({
        'term': q, 'media': 'music', 'entity': entity, 'limit': limit, 'country': 'JP'
    })
    req = urllib.request.Request(url, headers={'User-Agent': SESSION_UA})
    try:
        with urllib.request.urlopen(req, timeout=12) as r:
            return json.loads(r.read())
    except Exception as e:
        return {'error': str(e)}

def hi_res(url_100: str) -> str | None:
    if not url_100: return None
    return re.sub(r'/\d+x\d+bb?\.jpg', '/1000x1000bb.jpg', url_100)

def dl(url: str, dest: Path) -> int | str:
    try:
        req = urllib.request.Request(url, headers={'User-Agent': SESSION_UA})
        with urllib.request.urlopen(req, timeout=15) as r:
            data = r.read()
        if len(data) < 1000:
            return 'too small'
        dest.write_bytes(data)
        return dest.stat().st_size
    except Exception as e:
        return str(e)

def try_album(entry: dict) -> dict:
    """Attempt multiple query strategies to find album cover."""
    aid = entry['album_id']
    title = entry.get('title', '') or entry.get('title_jp', '')
    title_jp = entry.get('title_jp', '') or ''
    catalog = entry.get('catalog', '') or ''

    queries = []
    # Strategy 1: Nanahira + first keywords of title
    strip_title = re.sub(r'[/／].*$', '', title).strip()[:40]
    if strip_title:
        queries.append(f'Nanahira {strip_title}')
        queries.append(f'ななひら {strip_title}')
    # Strategy 2: catalog number
    if catalog and '-' in catalog and catalog not in ('N/A', 'TIE-IN', 'DIGITAL-ONLY'):
        queries.append(f'Nanahira {catalog}')
    # Strategy 3: title_jp standalone
    if title_jp and title_jp != strip_title:
        strip_jp = re.sub(r'[/／].*$', '', title_jp).strip()[:30]
        if strip_jp:
            queries.append(f'ななひら {strip_jp}')

    for q in queries:
        data = itunes_search(q, 'album')
        if 'error' in data:
            continue
        results = data.get('results', []) or []
        # Look for match where artist contains Nanahira
        for r in results:
            artist = (r.get('artistName') or '').lower()
            if 'nanahira' in artist or 'ななひら' in artist:
                u = hi_res(r.get('artworkUrl100'))
                if u:
                    return {'query': q, 'match': r, 'cover_url': u}
        time.sleep(random.uniform(0.2, 0.4))
    return {}

def try_track(entry: dict) -> dict:
    """For 1-track digital singles, try the track search."""
    title = entry.get('title', '') or entry.get('title_jp', '')
    strip_title = re.sub(r'[/／].*$', '', title).strip()[:40]
    if not strip_title:
        return {}
    queries = [f'Nanahira {strip_title}', f'ななひら {strip_title}']
    for q in queries:
        data = itunes_search(q, 'musicTrack')
        if 'error' in data:
            continue
        for r in (data.get('results', []) or []):
            artist = (r.get('artistName') or '').lower()
            if 'nanahira' in artist or 'ななひら' in artist:
                u = hi_res(r.get('artworkUrl100'))
                if u:
                    return {'query': q, 'match': r, 'cover_url': u}
        time.sleep(random.uniform(0.2, 0.4))
    return {}

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--worker', type=int, default=0)
    ap.add_argument('--workers', type=int, default=1)
    args = ap.parse_args()

    CACHE = cache_path(args.worker)
    tried: dict = json.loads(CACHE.read_text()) if CACHE.exists() else {}

    resume_only_missing = True
    to_process = [e for i, e in enumerate(INDEX) if i % args.workers == args.worker]
    total = len(to_process)
    saved = 0
    miss = 0
    skipped = 0

    for i, entry in enumerate(to_process, 1):
        aid = entry['album_id']
        album_cover = ALBUMS_DIR / f'{aid}.json'  # we write .jpg; here we check existence pattern
        # check existing jpg / previous attempt
        existing_album_jpg = ALBUMS_DIR / f'{aid}.jpg'
        existing_track_jpg = TRACK_DIR / f'ALB{aid}_D1T1.jpg'
        # single-track detection — assume 1 track if cover not used; we try track dir for singles
        is_single = False
        track_count = 0
        # Load the album JSON to check track count
        alb_path = RESEARCH / 'albums' / f'{aid}.json'
        if alb_path.exists():
            d = json.loads(alb_path.read_text())
            track_count = len(d.get('tracklist', []))
            is_single = track_count == 1

        # resume: skip if we have an image already
        if existing_album_jpg.exists() or existing_track_jpg.exists():
            skipped += 1
            continue
        if tried.get(aid) == 'miss' and resume_only_missing:
            # tried before, no luck — skip to save API calls
            miss += 1
            continue

        date = entry.get('date', '')
        title = (entry.get('title') or entry.get('title_jp') or '')[:50]
        print(f'[w{args.worker} {i}/{total}] {aid} ({date}) {title}', flush=True)

        result = try_album(entry)
        dest = None
        if result and is_single:
            # Single-track release: store as track cover
            dest = TRACK_DIR / f'ALB{aid}_D1T1.jpg'
        elif result:
            dest = ALBUMS_DIR / f'{aid}.jpg'
        elif is_single:
            # no album match — try track search
            result = try_track(entry)
            if result:
                dest = TRACK_DIR / f'ALB{aid}_D1T1.jpg'

        if dest and result:
            sz = dl(result['cover_url'], dest)
            if isinstance(sz, int):
                saved += 1
                tried[aid] = 'hit'
                print(f'    ✓ {dest.name} {sz}B  [{result["query"]}]')
            else:
                miss += 1
                tried[aid] = 'miss'
                print(f'    ✗ download failed: {sz}')
        else:
            miss += 1
            tried[aid] = 'miss'

        # periodic cache flush
        if i % 20 == 0:
            CACHE.write_text(json.dumps(tried, ensure_ascii=False, indent=2))
        time.sleep(random.uniform(0.35, 0.65))

    CACHE.write_text(json.dumps(tried, ensure_ascii=False, indent=2))
    print(f'\n[w{args.worker}] saved={saved} miss={miss} skipped={skipped} / {total}')

if __name__ == '__main__':
    main()
