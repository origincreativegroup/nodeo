# Cursor Agent — jpstas Assets + Portfolio Integrator (FINAL)

## Objective
Unify jpstas.com’s content and asset pipeline:
1) Automate Markdown → portfolio page generation from `/content/portfolio/*.md`.
2) Integrate Cloudflare R2/Stream asset mapping with global and per‑project workflows.
3) Keep GUI controls for Tabs, Missing filter, Missing Summary, and Inject/Dry‑Run.

## Must-Exist Files
- `src/jspow-plugin-assets.mjs` (export `injectAssets({ dryRun, root, urlsPath })`).
- `jspow.config.mjs` (tasks: `assets:inject`, `assets:gui`, `portfolio:update`).
- `assets/assets.manifest.json`, `assets/urls.example.json`, optional per‑project `assets/urls.<slug>.json`.
- GUI: `tools/assets-gui/server.mjs`, `tools/assets-gui/public/index.html` (tabs, filters, summary, inject buttons).

## Portfolio Page Replacement
Target: `/content/pages/portfolio.md`

Build the page by parsing each file in `/content/portfolio/*.md`:
- Title from `# Title`
- Summary from `**Summary:**`
- Tags from `**Tags:**`
- Slug = kebab‑case filename without `.md`
- Emit a block per project using this template:
```
---

### {Title}
*{Summary}*

Tags: `tag1`, `tag2`, ...

[View Case Study →](/portfolio/{slug})

{{ASSET:{slug}/hero}}
```

## Commands to Expose
```bash
# Regenerate portfolio page from case studies
node -e "import('./jspow.config.mjs').then(m => m.default.tasks['portfolio:update']({ args: [] }))"
node -e "import('./jspow.config.mjs').then(m => m.default.tasks['portfolio:update']({ args: ['--dry'] }))"  # preview

# Asset injection (global or per-project)
node scripts/inject-assets.mjs
node scripts/inject-assets.mjs --project brand-evolution
node scripts/inject-assets.mjs --dry --project media-campaigns

# GUI for URLs/Stream IDs
npm run assets:gui   # http://localhost:5173

# Sync jpstas.com JSON
node scripts/sync-jpstacom.mjs --dry
node scripts/sync-jpstacom.mjs
```
