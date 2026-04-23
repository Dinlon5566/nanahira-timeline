# Nanahira Discography Timeline — Astro site

Fan-made timeline of ななひら (Nanahira)'s discography.
Static site, deployed to GitHub Pages.

## Development

```bash
cd site/astro
npm install
npm run dev           # http://localhost:4321/
```

## Data pipeline

Data lives under `src/data/` and is generated from `/home/kali/project/nanahira/research/`.

```bash
python3 scripts/sync_from_research.py   # produces albums.json + tracks.json
python3 scripts/build_timeline.py       # produces timeline.json
```

`src/data/milestones.json` and `src/data/aliases.json` are hand-edited.

## Covers

Place covers in `public/covers/album/<album_id>.jpg` or `public/covers/track/<track_id>.jpg`
and re-run `scripts/sync_from_research.py` — the `cover` field will be filled
automatically. Missing covers gracefully degrade to cover-less layout.

Use `/home/kali/project/nanahira/research/fetch_covers.py` (iTunes search API,
no auth needed) to bulk-fetch covers.

## Build & deploy

```bash
npm run build         # dist/
```

GitHub Pages deploy is wired via `.github/workflows/deploy.yml` (at repo root).
Set `ASTRO_BASE=/<repo-name>` for project pages, or leave `/` for user pages.

## i18n

Default locale `ja`. Stubs for `en` and `zh`. UI strings live in `src/i18n/{ja,en,zh}.json`.
Song/album titles are kept in Japanese original — only UI chrome is translated.
