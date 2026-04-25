#!/usr/bin/env python3
"""Comprehensive album cover fetcher for all no-cover albums.

Strategy tiers:
  1. Cover Art Archive (MusicBrainz MBID) — free, no auth
  2. og:image scraping — BOOTH, Diverse Direct, Bandcamp, official pages
  3. VGMdb via patchright — existing script handles these
  4. Discogs API — images field
  5. TouhouDB — page scrape
  6. nanahira.jp — special JS page, extract from API/image paths
  7. Web search fallback — for no-url albums
"""
import json, re, time, urllib.request, urllib.error, sys, os
from pathlib import Path
from html.parser import HTMLParser

ROOT = Path(__file__).resolve().parent.parent
ALBUMS_DIR = Path('/home/kali/project/nanahira/research/albums')
COVERS_DIR = ROOT / 'public' / 'covers' / 'album'
COVERS_DIR.mkdir(parents=True, exist_ok=True)

UA = 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36'

with open('/home/kali/project/nanahira/research/albums_index.json') as f:
    INDEX = json.load(f)

stats = {'ok': 0, 'skip': 0, 'fail': 0, 'no_image': 0}
log = []

def has_cover(aid):
    return (COVERS_DIR / f'{aid}.jpg').exists()

def save_image(url: str, dest: Path, referer='') -> bool:
    try:
        req = urllib.request.Request(url, headers={
            'User-Agent': UA,
            'Referer': referer or url,
            'Accept': 'image/*,*/*;q=0.8',
        })
        with urllib.request.urlopen(req, timeout=20) as r:
            data = r.read()
        if len(data) < 3000:
            return False
        # Basic image check
        if not (data[:3] == b'\xff\xd8\xff' or data[:4] == b'\x89PNG' or data[:4] == b'RIFF' or data[:4] == b'GIF8' or data[:4] == b'WEBP'[:-1]):
            # Try anyway if large enough
            if len(data) < 10000:
                return False
        dest.write_bytes(data)
        return True
    except Exception as e:
        return False

def fetch_url(url, referer='', timeout=15) -> str | None:
    try:
        req = urllib.request.Request(url, headers={
            'User-Agent': UA,
            'Referer': referer or url,
            'Accept': 'text/html,application/xhtml+xml,*/*',
            'Accept-Language': 'ja,en;q=0.9',
        })
        with urllib.request.urlopen(req, timeout=timeout) as r:
            raw = r.read()
        try:
            return raw.decode('utf-8')
        except:
            return raw.decode('latin-1', errors='replace')
    except Exception:
        return None

def extract_og_image(html: str) -> str | None:
    patterns = [
        r'<meta[^>]+property=["\']og:image["\'][^>]+content=["\']([^"\']+)["\']',
        r'<meta[^>]+content=["\']([^"\']+)["\'][^>]+property=["\']og:image["\']',
        r'<meta[^>]+name=["\']twitter:image["\'][^>]+content=["\']([^"\']+)["\']',
        r'<meta[^>]+content=["\']([^"\']+)["\'][^>]+name=["\']twitter:image["\']',
    ]
    for pat in patterns:
        m = re.search(pat, html, re.I)
        if m:
            url = m.group(1).strip()
            if url and not url.endswith('.gif') and 'placeholder' not in url.lower():
                return url
    return None

# ─── Tier 1: Cover Art Archive ──────────────────────────────────────────────
def try_coverartarchive(aid, mbid):
    for size in ['front', 'front-500']:
        url = f'https://coverartarchive.org/release/{mbid}/{size}'
        dest = COVERS_DIR / f'{aid}.jpg'
        # CAA redirects to actual image
        try:
            req = urllib.request.Request(url, headers={'User-Agent': UA})
            with urllib.request.urlopen(req, timeout=20) as r:
                data = r.read()
            if len(data) > 3000:
                dest.write_bytes(data)
                return True
        except urllib.error.HTTPError as e:
            if e.code == 404:
                return False
        except Exception:
            pass
    return False

# ─── Tier 2: og:image scraping ───────────────────────────────────────────────
def try_og_image(aid, url):
    html = fetch_url(url)
    if not html:
        return False
    img_url = extract_og_image(html)
    if not img_url:
        return False
    # Make absolute
    if img_url.startswith('//'):
        img_url = 'https:' + img_url
    elif img_url.startswith('/'):
        from urllib.parse import urlparse
        p = urlparse(url)
        img_url = f'{p.scheme}://{p.netloc}{img_url}'
    return save_image(img_url, COVERS_DIR / f'{aid}.jpg', referer=url)

# ─── Tier 3: Discogs API ─────────────────────────────────────────────────────
def try_discogs(aid, url):
    m = re.search(r'discogs\.com/release/(\d+)', url)
    if not m:
        return False
    rid = m.group(1)
    api_url = f'https://api.discogs.com/releases/{rid}'
    html = fetch_url(api_url)
    if not html:
        return False
    try:
        d = json.loads(html)
        images = d.get('images', [])
        if images:
            img_url = images[0].get('uri') or images[0].get('resource_url', '')
            if img_url:
                return save_image(img_url, COVERS_DIR / f'{aid}.jpg', referer=url)
    except Exception:
        pass
    return False

# ─── Tier 4: TouhouDB ────────────────────────────────────────────────────────
def try_touhoudb(aid, url):
    html = fetch_url(url)
    if not html:
        return False
    # TouhouDB has cover in <img class="coverPicture"> or og:image
    img_url = extract_og_image(html)
    if not img_url:
        m = re.search(r'<img[^>]+class="[^"]*coverPicture[^"]*"[^>]+src="([^"]+)"', html, re.I)
        if m:
            img_url = m.group(1)
        if not img_url:
            m = re.search(r'<img[^>]+src="([^"]+(?:cover|jacket|album)[^"]+\.(?:jpg|png|webp))"', html, re.I)
            if m:
                img_url = m.group(1)
    if not img_url:
        return False
    if img_url.startswith('/'):
        img_url = 'https://touhoudb.com' + img_url
    return save_image(img_url, COVERS_DIR / f'{aid}.jpg', referer=url)

# ─── Tier 5: IOSYS official ──────────────────────────────────────────────────
def try_iosys(aid, url):
    html = fetch_url(url)
    if not html:
        return False
    img_url = extract_og_image(html)
    if not img_url:
        # Look for jacket/cover image
        m = re.search(r'<img[^>]+src="([^"]+(?:jacket|cover|jkt)[^"]+\.(?:jpg|png))"', html, re.I)
        if m:
            img_url = m.group(1)
    if not img_url:
        return False
    if img_url.startswith('/'):
        img_url = 'https://www.iosysos.com' + img_url
    return save_image(img_url, COVERS_DIR / f'{aid}.jpg', referer=url)

# ─── Tier 6: orc2000 (ポヤッチオ) ─────────────────────────────────────────────
def try_orc2000(aid, url):
    html = fetch_url(url)
    if not html:
        return False
    img_url = extract_og_image(html)
    if not img_url:
        # orc2000 uses <img src="./jacket.jpg"> or similar
        m = re.search(r'<img[^>]+src="([^"]+\.(?:jpg|png))"[^>]*>', html, re.I)
        if m:
            img_url = m.group(1)
    if not img_url:
        return False
    if not img_url.startswith('http'):
        from urllib.parse import urljoin
        img_url = urljoin(url, img_url)
    return save_image(img_url, COVERS_DIR / f'{aid}.jpg', referer=url)

# ─── Tier 7: Generic page scrape (shojoron, dreamusic, etc.) ─────────────────
def try_generic_page(aid, url):
    # First try og:image
    if try_og_image(aid, url):
        return True
    # Then try largest img on page
    html = fetch_url(url)
    if not html:
        return False
    imgs = re.findall(r'<img[^>]+src="([^"]+\.(?:jpg|jpeg|png|webp))"', html, re.I)
    if not imgs:
        return False
    from urllib.parse import urljoin
    for img in imgs:
        if any(skip in img.lower() for skip in ['icon','logo','btn','button','arrow','banner','bg','background','pixel','1x1']):
            continue
        if not img.startswith('http'):
            img = urljoin(url, img)
        if save_image(img, COVERS_DIR / f'{aid}.jpg', referer=url):
            return True
    return False

# ─── Main loop ───────────────────────────────────────────────────────────────
def process(aid, url):
    if has_cover(aid):
        stats['skip'] += 1
        return 'skip'

    # Determine strategy
    if not url:
        return 'no_url'

    result = False

    mbid_m = re.search(r'musicbrainz\.org/release/([0-9a-f-]{36})', url)
    if mbid_m:
        result = try_coverartarchive(aid, mbid_m.group(1))
        if result:
            return 'coverartarchive'

    if 'discogs.com' in url:
        result = try_discogs(aid, url)
        if result: return 'discogs'

    if 'touhoudb.com' in url:
        result = try_touhoudb(aid, url)
        if result: return 'touhoudb'

    if 'iosysos.com' in url or 'iosys.com' in url:
        result = try_iosys(aid, url)
        if result: return 'iosys'

    if 'orc2000.com' in url:
        result = try_orc2000(aid, url)
        if result: return 'orc2000'

    # og:image works for: booth, diverse.direct, bandcamp, lastfm, shojoron, dreamusic, ototoy, etc.
    result = try_og_image(aid, url)
    if result: return 'og_image'

    # Generic fallback
    result = try_generic_page(aid, url)
    if result: return 'generic'

    return 'fail'

# ─── Run ─────────────────────────────────────────────────────────────────────
if __name__ == '__main__':
    target_ids = set(sys.argv[1:]) if len(sys.argv) > 1 else None

    to_process = []
    for e in INDEX:
        aid = e['album_id']
        if target_ids and aid not in target_ids:
            continue
        if has_cover(aid):
            continue
        fpath = ALBUMS_DIR / f'{aid}.json'
        if not fpath.exists():
            continue
        with open(fpath) as f:
            d = json.load(f)
        url = d.get('url') or ''
        to_process.append((aid, url, e.get('title_jp') or e.get('title', '')))

    # Sort: CAA first, then og_image sources, then vgmdb, then no_url last
    def priority(item):
        _, url, _ = item
        if 'musicbrainz.org' in url: return 0
        if 'discogs' in url: return 1
        if any(x in url for x in ['booth.pm','diverse.direct','bandcamp','iosys','orc2000','shojoron','touhoudb']): return 2
        if url: return 3
        return 9
    to_process.sort(key=priority)

    print(f'Processing {len(to_process)} albums...')
    for i, (aid, url, title) in enumerate(to_process):
        result = process(aid, url)
        icon = '✓' if result not in ('fail','no_url') else '✗'
        print(f'[{i+1:3d}/{len(to_process)}] {icon} {aid} {result:<18} {title[:35]}')
        log.append({'aid': aid, 'result': result, 'url': url[:60]})
        if result not in ('skip', 'no_url', 'fail'):
            stats['ok'] += 1
        elif result == 'fail':
            stats['fail'] += 1
        elif result == 'no_url':
            stats['no_image'] += 1
        time.sleep(0.3)

    print(f'\nDone: ok={stats["ok"]} skip={stats["skip"]} fail={stats["fail"]} no_url={stats["no_image"]}')
    # Save log
    with open(ROOT / 'scripts' / 'cover_fetch_log.json', 'w') as f:
        json.dump(log, f, ensure_ascii=False, indent=2)
