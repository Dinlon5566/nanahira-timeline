#!/usr/bin/env python3
"""Fetch album cover images from VGMdb using patchright (bypasses Cloudflare).
Only targets albums that still lack a cover locally.

Strategy: fetch the VGMdb album page, parse for the large cover image URL,
then download it with correct Referer header."""
import json, sys, re, time, random, argparse, urllib.request
from pathlib import Path

sys.path.insert(0, '/home/kali/project/nanahira/research')
from scrape_vgmdb import launch, fetch  # reuses patchright + Chromium setup

ROOT = Path(__file__).resolve().parent.parent
ALB_COV = ROOT / 'public' / 'covers' / 'album'
TRK_COV = ROOT / 'public' / 'covers' / 'track'
ALB_COV.mkdir(parents=True, exist_ok=True)
TRK_COV.mkdir(parents=True, exist_ok=True)

albums = json.loads((ROOT / 'src' / 'data' / 'albums.json').read_text())
tracks = json.loads((ROOT / 'src' / 'data' / 'tracks.json').read_text())
tracks_by_album = {}
for t in tracks:
    tracks_by_album.setdefault(t['album_id'], []).append(t)

def cache_path(w: int) -> Path:
    return ROOT / 'scripts' / f'vgmdb_covers_tried_w{w}.json'

def existing_cover_path(a: dict):
    aid = a['id']
    alb_jpg = ALB_COV / f'{aid}.jpg'
    if alb_jpg.exists(): return alb_jpg
    tl = tracks_by_album.get(aid, [])
    if len(tl) == 1:
        p = TRK_COV / f'{tl[0]["id"]}.jpg'
        if p.exists(): return p
    return None

def target_path(a: dict) -> Path:
    aid = a['id']
    tl = tracks_by_album.get(aid, [])
    if len(tl) == 1:
        return TRK_COV / f'{tl[0]["id"]}.jpg'
    return ALB_COV / f'{aid}.jpg'

NSFW_PLACEHOLDER = re.compile(r'album-nsfw|noalbum|no_cover', re.I)

def extract_cover_url(html: str) -> str | None:
    # 1. Highslide hires link (exists for some albums)
    m = re.search(r'class="highslide"[^>]*href="([^"]+\.(?:jpg|jpeg|png))"', html)
    if m and not NSFW_PLACEHOLDER.search(m.group(1)):
        return m.group(1)
    # 2. coverart div background-image
    m = re.search(r'id="coverart"[^>]*background-image:\s*url\(\s*[\'"]?([^\'")]+)[\'"]?\s*\)', html)
    if m:
        url = m.group(1)
        if NSFW_PLACEHOLDER.search(url):
            return None  # NSFW placeholder, skip
        # Upgrade medium-media → media (hires)
        if 'medium-media.vgm.io' in url:
            url = url.replace('medium-media.vgm.io', 'media.vgm.io')
        elif 'thumb-media.vgm.io' in url:
            url = url.replace('thumb-media.vgm.io', 'media.vgm.io')
        return url
    return None

def download(url: str, dest: Path, referer: str) -> int | str:
    try:
        req = urllib.request.Request(url, headers={
            'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64) Gecko/20100101 Firefox/125.0',
            'Referer': referer,
            'Accept': 'image/webp,image/apng,image/*,*/*;q=0.8',
        })
        with urllib.request.urlopen(req, timeout=20) as r:
            data = r.read()
        if len(data) < 2000:
            return 'image too small'
        dest.write_bytes(data)
        return dest.stat().st_size
    except Exception as e:
        return str(e)

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--worker', type=int, default=0)
    ap.add_argument('--workers', type=int, default=1)
    ap.add_argument('--max', type=int, default=0)
    args = ap.parse_args()

    CACHE = cache_path(args.worker)
    tried: dict = json.loads(CACHE.read_text()) if CACHE.exists() else {}

    todo = []
    for i, a in enumerate(albums):
        if existing_cover_path(a):
            continue
        vgmdb_url = (a.get('sources') or {}).get('vgmdb')
        if not vgmdb_url:
            continue
        if tried.get(a['id']) == 'miss':
            continue
        if i % args.workers != args.worker:
            continue
        todo.append(a)
    if args.max:
        todo = todo[:args.max]
    print(f'[w{args.worker}] {len(todo)} albums to try', flush=True)

    from patchright.sync_api import sync_playwright
    saved = 0; miss = 0
    with sync_playwright() as p:
        browser, ctx = launch(p)
        page = ctx.new_page()
        for i, a in enumerate(todo, 1):
            aid = a['id']
            url = a['sources']['vgmdb']
            print(f'[w{args.worker} {i}/{len(todo)}] {aid} {a["title_jp"][:40]}', flush=True)
            try:
                html = fetch(page, url)
            except Exception as e:
                print(f'  fetch err {e}', flush=True)
                tried[aid] = 'miss'; miss += 1
                continue
            cover_url = extract_cover_url(html)
            if not cover_url:
                tried[aid] = 'miss'; miss += 1
                print('  no cover in page', flush=True)
                continue
            dest = target_path(a)
            sz = download(cover_url, dest, url)
            if isinstance(sz, int):
                print(f'  ✓ {dest.name} {sz}B', flush=True)
                tried[aid] = 'hit'; saved += 1
            else:
                tried[aid] = 'miss'; miss += 1
                print(f'  ✗ download failed: {sz}', flush=True)
            if i % 10 == 0:
                CACHE.write_text(json.dumps(tried, ensure_ascii=False, indent=2))
            time.sleep(random.uniform(1.5, 2.5))
        browser.close()
    CACHE.write_text(json.dumps(tried, ensure_ascii=False, indent=2))
    print(f'\n[w{args.worker}] saved={saved} miss={miss}', flush=True)

if __name__ == '__main__':
    main()
