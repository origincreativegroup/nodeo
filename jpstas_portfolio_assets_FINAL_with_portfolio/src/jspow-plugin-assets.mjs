// src/jspow-plugin-assets.mjs
import fs from "node:fs";
import path from "node:path";

function loadJson(p) {
  return JSON.parse(fs.readFileSync(p, "utf-8"));
}

function loadJsonIfExists(p) {
  if (!p) return null;
  return fs.existsSync(p) ? loadJson(p) : null;
}

function mergeUrlMaps(base = {}, override = {}) {
  const merged = { ...base };
  for (const [key, value] of Object.entries(override)) {
    const current = merged[key];
    if (current && typeof current === "object" && typeof value === "object") {
      merged[key] = { ...current, ...value };
    } else {
      merged[key] = value;
    }
  }
  return merged;
}

function findMarkdownFiles(dir) {
  return fs.readdirSync(dir)
    .filter(f => f.endsWith(".md"))
    .map(f => path.join(dir, f));
}

function replacePlaceholders(text, manifestIndex, urls, missing, filePath) {
  let replaced = 0;
  const imageRe = /\{\{ASSET:([^\}]+)\}\}/g;
  const videoRe = /\{\{STREAM:([^\}]+)\}\}/g;

  const handleMissing = (key, type, reason) => {
    missing.push({ key, type, reason, file: filePath });
  };

  text = text.replace(imageRe, (m, key) => {
    const meta = manifestIndex.get(key);
    const urlEntry = urls[key];
    if (!meta) {
      handleMissing(key, "asset", "missing-manifest-entry");
      return m;
    }
    if (!urlEntry) {
      handleMissing(key, "asset", "missing-url-entry");
      return m;
    }
    if (!urlEntry.url) {
      handleMissing(key, "asset", "missing-url-value");
      return m;
    }
    const alt = meta.alt || "";
    const caption = meta.caption ? ` "${meta.caption}"` : "";
    replaced++;
    return `![${alt}](${urlEntry.url}${caption})`;
  });

  text = text.replace(videoRe, (m, key) => {
    const meta = manifestIndex.get(key);
    const urlEntry = urls[key];
    if (!meta) {
      handleMissing(key, "stream", "missing-manifest-entry");
      return m;
    }
    if (!urlEntry) {
      handleMissing(key, "stream", "missing-url-entry");
      return m;
    }
    if (!urlEntry.streamId) {
      handleMissing(key, "stream", "missing-stream-id");
      return m;
    }
    const posterParam = urlEntry.poster ? `?poster=${encodeURIComponent(urlEntry.poster)}` : "";
    replaced++;
    return [
      `<div class="video">`,
      `  <iframe`,
      `    src="https://iframe.cloudflarestream.com/${urlEntry.streamId}${posterParam}"`,
      `    loading="lazy" allow="accelerometer; gyroscope; autoplay; encrypted-media; picture-in-picture;"`,
      `    allowfullscreen width="100%" height="480" style="aspect-ratio:16/9;border:0;">`,
      `  </iframe>`,
      `</div>`
    ].join("\n");
  });

  return { text, replaced };
}

export async function injectAssets(opts = {}) {
  const root = opts.root || process.cwd();
  const dryRun = !!opts.dryRun;
  const CONTENT_DIR = path.join(root, opts.contentDir ?? "content/portfolio");
  const MANIFEST_PATH = path.join(root, opts.manifestPath ?? "assets/assets.manifest.json");
  const GLOBAL_URLS_PATH = path.join(root, "assets/urls.json");
  const OVERRIDE_URLS_PATH = opts.urlsPath ? path.join(root, opts.urlsPath) : null;

  if (!fs.existsSync(GLOBAL_URLS_PATH)) {
    throw new Error("Missing assets/urls.json. Copy assets/urls.example.json → assets/urls.json and fill URLs/streamIds.");
  }

  const manifest = loadJson(MANIFEST_PATH);
  const globalUrls = loadJson(GLOBAL_URLS_PATH);
  const overrideUrls = loadJsonIfExists(OVERRIDE_URLS_PATH) || {};
  if (OVERRIDE_URLS_PATH && !fs.existsSync(OVERRIDE_URLS_PATH)) {
    console.warn(`[assets] Override file not found at ${OVERRIDE_URLS_PATH}, falling back to global urls.json.`);
  }
  const urls = mergeUrlMaps(globalUrls, overrideUrls);
  const manifestIndex = new Map(manifest.map(m => [m.key, m]));

  const files = findMarkdownFiles(CONTENT_DIR);
  const missing = [];
  let total = 0, totalFiles = 0;

  files.forEach(file => {
    const original = fs.readFileSync(file, "utf-8");
    const { text, replaced } = replacePlaceholders(original, manifestIndex, urls, missing, path.relative(root, file));
    if (replaced > 0) {
      total += replaced;
      totalFiles += 1;
      if (!dryRun) fs.writeFileSync(file, text, "utf-8");
    }
  });

  return { replaced: total, files: totalFiles, dryRun, missing };
}
