#!/usr/bin/env python3
"""Pre-rsync deduplication for cover images.

Problem: Re-fetching covers (different sources, JPEG re-encoders, EXIF strippers)
produces byte-different but pixel-identical files. Each rsync/commit then includes
hundreds of "modified" covers with no real visual change, polluting history.

Solution: Compare working-tree covers to a snapshot of the last-pushed state.
For each that differs in bytes:
  - Load both with PIL, downscale to common size, compare pixel data
  - If pixel-identical (or near-identical via threshold), restore snapshot bytes
  - If genuinely different (new cover or different image), keep working-tree version

Workflow:
  1. After successful push, run:
       python3 scripts/dedupe_covers.py --snapshot
     (saves current state as the next baseline)
  2. Before next rsync/commit, run:
       python3 scripts/dedupe_covers.py --restore
     (reverts pixel-identical covers, prints summary)

Snapshot location: scripts/cover_snapshot/  (gitignored)
"""
import argparse, hashlib, shutil, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
COVERS_DIRS = [ROOT / 'public' / 'covers' / 'album', ROOT / 'public' / 'covers' / 'track']
SNAPSHOT = Path(__file__).resolve().parent / 'cover_snapshot'

def sha(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()

def pixel_match(a: Path, b: Path, max_pixel_diff_ratio: float = 0.001) -> bool:
    """True if a and b are pixel-identical (up to threshold)."""
    try:
        from PIL import Image
    except ImportError:
        print('PIL/Pillow not installed; falling back to byte-exact compare', file=sys.stderr)
        return a.read_bytes() == b.read_bytes()

    try:
        ia = Image.open(a).convert('RGB')
        ib = Image.open(b).convert('RGB')
    except Exception as e:
        print(f'  open error: {e}', file=sys.stderr)
        return False

    if ia.size != ib.size:
        return False

    # Strict pixel compare
    if ia.tobytes() == ib.tobytes():
        return True

    # Tolerant: count differing pixels, allow up to ratio threshold
    # (handles minor JPEG decoder variance)
    da = ia.tobytes()
    db = ib.tobytes()
    if len(da) != len(db):
        return False
    diff_bytes = sum(1 for x, y in zip(da, db) if x != y)
    total = len(da)
    return diff_bytes / total < max_pixel_diff_ratio

def snapshot():
    """Save current covers/ as the baseline."""
    if SNAPSHOT.exists():
        shutil.rmtree(SNAPSHOT)
    n = 0
    for src_dir in COVERS_DIRS:
        if not src_dir.exists(): continue
        rel = src_dir.relative_to(ROOT / 'public')
        dst = SNAPSHOT / rel
        dst.mkdir(parents=True, exist_ok=True)
        for f in src_dir.glob('*'):
            shutil.copy2(f, dst / f.name)
            n += 1
    print(f'Snapshot saved: {n} files → {SNAPSHOT}')

def restore():
    """Restore pixel-identical covers from snapshot."""
    if not SNAPSHOT.exists():
        print('No snapshot found. Run --snapshot first after a clean push.')
        return

    stats = {'unchanged': 0, 'restored': 0, 'kept_real_change': 0, 'new': 0, 'gone': 0}
    examples = {'restored': [], 'kept_real_change': []}

    for src_dir in COVERS_DIRS:
        if not src_dir.exists(): continue
        rel = src_dir.relative_to(ROOT / 'public')
        snap_dir = SNAPSHOT / rel
        if not snap_dir.exists(): continue

        # In current but not snapshot → genuinely new
        for f in src_dir.glob('*'):
            snap = snap_dir / f.name
            if not snap.exists():
                stats['new'] += 1
                continue
            if sha(f) == sha(snap):
                # byte-identical, no change
                stats['unchanged'] += 1
                continue
            # bytes differ — check pixels
            if pixel_match(f, snap):
                shutil.copy2(snap, f)
                stats['restored'] += 1
                if len(examples['restored']) < 3: examples['restored'].append(f.name)
            else:
                stats['kept_real_change'] += 1
                if len(examples['kept_real_change']) < 3: examples['kept_real_change'].append(f.name)

        # In snapshot but not current → file was deleted intentionally
        for f in snap_dir.glob('*'):
            if not (src_dir / f.name).exists():
                stats['gone'] += 1

    print(f'Unchanged (byte-identical):  {stats["unchanged"]}')
    print(f'Restored (pixel-identical):  {stats["restored"]}')
    print(f'Kept (real change):          {stats["kept_real_change"]}')
    print(f'New files:                   {stats["new"]}')
    print(f'Deleted from working tree:   {stats["gone"]}')
    if examples['restored']:
        print(f'  e.g. restored: {", ".join(examples["restored"])}')
    if examples['kept_real_change']:
        print(f'  e.g. kept:     {", ".join(examples["kept_real_change"])}')

def main():
    ap = argparse.ArgumentParser()
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument('--snapshot', action='store_true', help='Save current covers as baseline')
    g.add_argument('--restore',  action='store_true', help='Restore pixel-identical from baseline')
    args = ap.parse_args()
    if args.snapshot: snapshot()
    elif args.restore: restore()

if __name__ == '__main__':
    main()
