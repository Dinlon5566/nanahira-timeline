#!/usr/bin/env python3
"""Generate WebP thumbnails for timeline cards.

Reads  public/covers/{album,track}/*.jpg
Writes public/covers/thumb/{album,track}/<id>.webp

Cards render covers at 96x96 CSS px (72 on mobile); 192px covers 2x DPR.
Cover.astro points card <img> at the thumb and falls back to the original
via onerror, so run this after adding new covers.

Idempotent: a thumb is skipped when it is newer than its source jpg.
"""
from pathlib import Path

from PIL import Image, ImageOps

ROOT = Path(__file__).resolve().parent.parent
COVERS = ROOT / "public" / "covers"
SIZE = 192
QUALITY = 80


def main() -> None:
    made = skipped = 0
    for kind in ("album", "track"):
        src_dir = COVERS / kind
        if not src_dir.is_dir():
            continue
        out_dir = COVERS / "thumb" / kind
        out_dir.mkdir(parents=True, exist_ok=True)
        for jpg in sorted(src_dir.glob("*.jpg")):
            out = out_dir / (jpg.stem + ".webp")
            if out.exists() and out.stat().st_mtime >= jpg.stat().st_mtime:
                skipped += 1
                continue
            im = Image.open(jpg)
            im = ImageOps.exif_transpose(im)
            if im.mode != "RGB":
                im = im.convert("RGB")
            im = ImageOps.fit(im, (SIZE, SIZE), Image.LANCZOS)
            im.save(out, "WEBP", quality=QUALITY, method=6)
            made += 1
    print(f"thumbs: {made} generated, {skipped} up-to-date")


if __name__ == "__main__":
    main()
