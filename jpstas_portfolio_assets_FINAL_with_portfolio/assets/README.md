# Assets Pipeline

This repository owns the manifest and URL mappings for the jpstas.com portfolio. Use it to stage assets, manage Cloudflare URLs/Stream IDs, and push updates into Markdown + jpstas.com.

## Workflow

1. **Stage files with JSPow**
   - Drop raw files in `assets/_incoming/<project>/<section>/`.
   - Run `jspow` using `jspow.staging.config.json` to rename and move files into `assets/processed/` while updating `data/jspow.manifest.json`.

2. **Update the manifest**
   - Add new entries (alt, caption, notes) to `assets/assets.manifest.json`.

3. **Generate delivery assets**
   - Export WebP/AVIF versions into `assets/exports/<project>/` (see `docs/staging-pipeline.md`).

4. **Fill CDN URLs / Stream IDs**
   - Copy `assets/urls.example.json` → `assets/urls.json` if you haven’t already.
   - Launch the GUI: `npm run assets:gui` → http://localhost:5173
   - Pick a project (or global) and paste Cloudflare R2 URLs / Stream IDs. Use the Missing filter to track progress.

5. **Inject into Markdown**
   - Preview: `node scripts/inject-assets.mjs --dry`
   - Write updates: `node scripts/inject-assets.mjs`
   - Scope to a project: `node scripts/inject-assets.mjs --project brand-evolution`

6. **Sync jpstas.com**
   - Preview: `node scripts/sync-jpstacom.mjs --dry`
   - Apply: `node scripts/sync-jpstacom.mjs`
   - Review diffs in `../jpstas.com/src/data/*.json`, then run site checks.

## References

- `docs/staging-pipeline.md` — staging folders, jspow config, QA checklist
- `docs/sync-jpstas.md` — jpstas.com sync instructions
- `tools/assets-gui/` — lightweight GUI for managing URL maps and running inject jobs
