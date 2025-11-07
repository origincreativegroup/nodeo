// jspow.config.mjs
import { injectAssets } from "./src/jspow-plugin-assets.mjs";

function slugify(input) {
  return input
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, "-")
    .replace(/(^-|-$)/g, "");
}

export default {
  tasks: {
    // Inject Cloudflare R2/Stream assets into Markdown (supports global or per-project url maps)
    "assets:inject": async (ctx) => {
      const args = ctx?.args ?? [];
      const projFlagIndex = Math.max(args.indexOf("--project"), args.indexOf("-p"));
      const project = projFlagIndex >= 0 ? args[projFlagIndex + 1] : null;
      const urlsPath = project ? `assets/urls.${project}.json` : undefined;

      const dry = args.includes("--dry") || args.includes("--dry-run");
      const res = await injectAssets({ dryRun: dry, root: process.cwd(), urlsPath });
      const prefix = dry ? "[DRY RUN] " : "";
      console.log(prefix + `Replaced ${res.replaced} placeholders across ${res.files} files.`);
      if (res.missing?.length) {
        console.warn(`[assets:inject] ${res.missing.length} placeholders left unchanged:`);
        res.missing.forEach(item => {
          console.warn(`  - ${item.type.toUpperCase()} ${item.key} (${item.reason}) in ${item.file}`);
        });
      }
    },

    // Launch zero-dep GUI to manage urls.json / urls.<project>.json
    "assets:gui": async () => {
      console.log("Run: node tools/assets-gui/server.mjs  (then open http://localhost:5173)");
    },

    // Build /content/pages/portfolio.md from /content/portfolio/*.md
    "portfolio:update": async (ctx) => {
      const args = ctx?.args ?? [];
      const dry = args.includes("--dry") || args.includes("--dry-run");
      const fs = await import("fs/promises");
      const path = await import("path");

      const contentDir = "content/portfolio";
      const portfolioPage = "content/pages/portfolio.md";
      await fs.mkdir("content/pages", { recursive: true });

      const files = (await fs.readdir(contentDir)).filter(f => f.endsWith(".md"));
      files.sort((a, b) => a.localeCompare(b));

      let output = "# Portfolio\n\n## Featured Work\nBelow is a curated selection of projects demonstrating creative, technical, and strategic versatility.\n";
      const missingMeta = [];

      for (const file of files) {
        const filePath = path.join(contentDir, file);
        const text = await fs.readFile(filePath, "utf-8");
        const titleMatch = text.match(/^# (.+)$/m);
        const summaryMatch = text.match(/\*\*Summary:\*\*\s*(.+)/);
        const tagsMatch = text.match(/\*\*Tags:\*\*\s*(.+)/);

        const baseSlug = path.basename(file, ".md");
        const slug = slugify(baseSlug) || baseSlug;
        const title = titleMatch ? titleMatch[1].trim() : slug;
        const summary = summaryMatch ? summaryMatch[1].trim() : "";
        const tagsRaw = tagsMatch ? tagsMatch[1].trim() : "";
        const tagsArray = tagsRaw
          .split(",")
          .map(s => s.trim())
          .filter(Boolean);
        const tags = tagsArray.length ? tagsArray.map(s => `\`${s}\``).join(", ") : "(missing)";

        if (!titleMatch) missingMeta.push({ slug, field: "title", file });
        if (!summary) missingMeta.push({ slug, field: "summary", file });
        if (!tagsArray.length) missingMeta.push({ slug, field: "tags", file });

        const summaryLine = summary || "Summary pending";

        output += `\n---\n\n### ${title}\n*${summaryLine}*\n\nTags: ${tags}\n\n[View Case Study →](/portfolio/${slug})\n\n{{ASSET:${slug}/hero}}\n\n`;
      }

      if (dry) {
        console.log(output);
      } else {
        await fs.writeFile(portfolioPage, output);
        console.log("✅ Portfolio page updated from case studies.");
      }

      if (missingMeta.length) {
        console.warn("[portfolio:update] Missing metadata detected:");
        missingMeta.forEach(item => {
          console.warn(`  - ${item.slug}: ${item.field} (${item.file})`);
        });
      }
    },
  },
};
