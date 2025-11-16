# nodeo Asset Staging

This project owns the source-of-truth manifest for portfolio assets. Use nodeo to normalize raw uploads, emit a manifest, and prep delivery files before syncing into jpstas.com.

## Folder Layout

```
assets/
  _incoming/          # drop raw uploads from shoots or exports here
  processed/          # jspow-renamed masters grouped by project and section
  exports/            # delivery-ready derivatives (webp/avif) by project and size
  assets.manifest.json# curated manifest consumed by injectAssets()
  urls.json           # resolved CDN URLs (per project overrides allowed)
```

Recommended project sections:

- `hero` — primary hero image (21:9)
- `gallery` — case study gallery frames (3:2, 4:3, 1:1, etc.)
- `process` — behind-the-scenes or workflow imagery
- `detail` — close-ups and supporting visuals
- `motion` — Cloudflare Stream IDs

## nodeo.staging.config.json

Run nodeo against the staging directories to rename files predictably and emit a manifest for downstream tooling.

```json
{
  "incomingDir": "assets/_incoming",
  "processedDir": "assets/processed",
  "pattern": "{project}-{section}-{descriptor}-{width}px{--variant}.{ext}",
  "defaults": {
    "project": "unsorted",
    "section": "gallery",
    "width": 1600,
    "ext": "webp"
  },
  "manifest": {
    "path": "data/nodeo.manifest.json",
    "format": "json"
  },
  "rules": [
    { "match": "*/hero/*", "section": "hero", "width": 2400 },
    { "match": "*/process/*", "section": "process", "width": 1600 },
    { "match": "*/thumbs/*", "section": "thumb", "width": 400 }
  ]
}
```

- Keep the `project` folder name aligned with the case study slug (e.g. `brand-evolution`).
- Use descriptive `descriptor` tokens so downstream exports inherit readable names.
- The generated `data/nodeo.manifest.json` is the bridge between nodeo and jpstas.com—store it under version control.

## Workflow

1. Drop new RAW/WebP files into `assets/_incoming/<project>/<section>/`.
2. Run `nodeo run --config nodeo.staging.config.json` to rename and relocate files to `assets/processed/`.
3. Generate WebP/AVIF exports (see `docs/exporting.md` TBD) into `assets/exports/<project>/`.
4. Update `assets/assets.manifest.json` with new keys, alt text, captions, and notes.
5. When CDN URLs are available, record them in `assets/urls.json` (or `assets/urls.<project>.json`).
6. Use `nodeo run assets:inject` (dry-run first) to push URLs into Markdown placeholders.
7. Run the jpstas.com sync step (see `docs/sync-jpstas.md`) to update the site JSON or Builder.io records.

## QA Checklist

- Manifest entry exists for every processed asset (hero + gallery + motion).
- Alt text and captions follow accessibility guidance before syncing.
- Tags in Markdown stay aligned with manifest keywords to improve search.
- Keep `_incoming` clean by archiving processed files in version control or NAS.
