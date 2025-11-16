# Syncing jpstas.com Media

Use `scripts/sync-jpstacom.mjs` after assets are staged and URLs are available.

## Prerequisites

- `assets/assets.manifest.json` contains the project entries with alt/caption.
- `assets/urls.json` (and optional `urls.<project>.json`) include public `https://media.jpstas.com/...` URLs or Cloudflare Stream IDs.
- `nodeo.staging.config.json` processed the latest batch so filenames match the manifest keys.
- The `jpstas.com` repository lives at `../jpstas.com` (override with `--target`).

## Commands

```bash
# Preview changes without writing
node scripts/sync-jpstacom.mjs --dry

# Write updates into ../jpstas.com/src/data
node scripts/sync-jpstacom.mjs

# Custom target path
node scripts/sync-jpstacom.mjs --target /path/to/jpstas.com
```

## What the Script Does

- Merges `assets/urls.json` with any `assets/urls.<project>.json` overrides.
- Groups manifest entries by project slug and checks for missing URLs/Stream IDs.
- Updates the corresponding `jpstas.com/src/data/*.json` files:
  - `hero` / `cardImage` sources use the manifest hero asset.
  - `solution.gallery` (or top-level `gallery`) rewrites to match manifest order, including Cloudflare Stream videos.
- Warns when URLs are missing or point outside `media.jpstas.com`.

## After Sync

1. Review `git status` in `jpstas.com` to inspect JSON diffs.
2. Run `npm run build:check` (or your preferred validation command) inside `jpstas.com`.
3. Commit both repositories once media URLs are confirmed.
