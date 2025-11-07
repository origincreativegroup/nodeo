#!/usr/bin/env node

import fs from "node:fs";
import fsp from "node:fs/promises";
import path from "node:path";

const ROOT = path.resolve(process.cwd());
const ASSETS_DIR = path.join(ROOT, "assets");
const MANIFEST_PATH = path.join(ASSETS_DIR, "assets.manifest.json");
const DEFAULT_URLS_PATH = path.join(ASSETS_DIR, "urls.json");

const args = process.argv.slice(2);
const dryRun = args.includes("--dry") || args.includes("--dry-run");
const targetIndex = Math.max(args.indexOf("--target"), args.indexOf("-t"));
const targetRoot = targetIndex >= 0
  ? path.resolve(args[targetIndex + 1])
  : path.resolve(ROOT, "..", "..", "jpstas.com");

if (!fs.existsSync(targetRoot)) {
  throw new Error(`Target jpstas.com path not found: ${targetRoot}. Pass --target to override.`);
}

const PROJECT_MAP = {
  "brand-evolution": { file: "brand-evolution.json" },
  "in-house-print-studio": { file: "printstudio.json" },
  "website-redesign": { file: "caribbeanpools.json" },
  "media-campaigns": { file: "drone-media.json" },
  "customer-experience-systems": { file: "formstack.json" }
};

function loadJson(p) {
  return JSON.parse(fs.readFileSync(p, "utf-8"));
}

function mergeUrlMaps(base = {}, overrides = {}) {
  const merged = { ...base };
  for (const [key, value] of Object.entries(overrides)) {
    if (!merged[key]) {
      merged[key] = value;
      continue;
    }
    if (typeof merged[key] === "object" && typeof value === "object") {
      merged[key] = { ...merged[key], ...value };
    } else {
      merged[key] = value;
    }
  }
  return merged;
}

async function loadUrls() {
  if (!fs.existsSync(DEFAULT_URLS_PATH)) {
    throw new Error("Missing assets/urls.json. Generate it before syncing jpstas.com.");
  }
  let urls = loadJson(DEFAULT_URLS_PATH);

  const files = await fsp.readdir(ASSETS_DIR);
  for (const file of files) {
    if (!file.startsWith("urls.") || file === "urls.json" || file === "urls.example.json") continue;
    const overridePath = path.join(ASSETS_DIR, file);
    const override = loadJson(overridePath);
    urls = mergeUrlMaps(urls, override);
  }
  return urls;
}

function groupManifest(manifest, urls) {
  const grouped = new Map();
  const missing = [];

  for (const entry of manifest) {
    const [project, ...rest] = entry.key.split("/");
    if (!project || rest.length === 0) continue;
    const name = rest.join("/");
    const urlEntry = urls[entry.key];

    if (!grouped.has(project)) grouped.set(project, []);
    grouped.get(project).push({ entry, name, urlEntry });

    if (entry.type === "image") {
      if (!urlEntry || !urlEntry.url) {
        missing.push({ key: entry.key, reason: "missing-url" });
      } else if (!urlEntry.url.includes("media.jpstas.com")) {
        missing.push({ key: entry.key, reason: "non-media-domain", value: urlEntry.url });
      }
    } else if (entry.type === "video") {
      if (!urlEntry || !urlEntry.streamId) {
        missing.push({ key: entry.key, reason: "missing-streamId" });
      }
    }
  }

  return { grouped, missing };
}

function buildGalleryPayload(assets) {
  return assets.map(({ entry, urlEntry }) => {
    if (entry.type === "image") {
      return {
        src: urlEntry?.url ?? null,
        alt: entry.alt,
        caption: entry.caption ?? undefined
      };
    }
    return {
      type: "video",
      src: urlEntry?.streamId ?? null,
      poster: urlEntry?.poster ?? undefined,
      alt: entry.alt,
      caption: entry.caption ?? undefined
    };
  });
}

async function syncProject(slug, assets, targetPath, dry) {
  const file = path.join(targetPath, "src", "data", PROJECT_MAP[slug].file);
  if (!fs.existsSync(file)) {
    console.warn(`[sync] Data file not found for ${slug}: ${file}`);
    return { slug, updated: false, reason: "missing-data-file" };
  }

  const original = await fsp.readFile(file, "utf-8");
  const data = JSON.parse(original);

  const heroAsset = assets.find(a => a.name === "hero" && a.entry.type === "image" && a.urlEntry?.url);
  const galleryAssets = assets.filter(a => !(a.name === "hero"));

  if (heroAsset) {
    const heroPayload = {
      src: heroAsset.urlEntry.url,
      alt: heroAsset.entry.alt,
      caption: heroAsset.entry.caption ?? undefined
    };
    data.hero = { ...data.hero, ...heroPayload };
    if (data.cardImage) {
      data.cardImage = { ...data.cardImage, src: heroAsset.urlEntry.url, alt: heroAsset.entry.alt };
    }
  }

  const galleryPayload = buildGalleryPayload(galleryAssets);
  if (data.solution?.gallery) {
    data.solution.gallery = galleryPayload;
  } else if (Array.isArray(data.gallery)) {
    data.gallery = galleryPayload;
  }

  const updated = JSON.stringify(data, null, 2) + "\n";
  if (!dry) {
    await fsp.writeFile(file, updated, "utf-8");
  }

  return {
    slug,
    updated: updated !== original,
    file,
    heroUpdated: Boolean(heroAsset),
    galleryCount: galleryPayload.length
  };
}

async function main() {
  const manifest = loadJson(MANIFEST_PATH);
  const urls = await loadUrls();
  const { grouped, missing } = groupManifest(manifest, urls);

  const results = [];
  for (const [slug, config] of Object.entries(PROJECT_MAP)) {
    if (!grouped.has(slug)) {
      console.warn(`[sync] No manifest entries for ${slug}`);
      continue;
    }
    const res = await syncProject(slug, grouped.get(slug), targetRoot, dryRun);
    results.push(res);
  }

  console.log(dryRun ? "[DRY] jpstas.com sync summary" : "jpstas.com sync summary");
  results.forEach(res => {
    if (!res) return;
    const status = res.updated ? "updated" : "skipped";
    console.log(` - ${res.slug}: ${status} (${res.galleryCount ?? 0} gallery items)`);
  });

  if (missing.length) {
    console.warn("Unresolved asset links:");
    missing.forEach(item => {
      const extra = item.value ? ` → ${item.value}` : "";
      console.warn(` - ${item.key}: ${item.reason}${extra}`);
    });
  }

  console.log(`Target project: ${targetRoot}`);
}

main().catch(err => {
  console.error("sync-jpstacom failed:", err);
  process.exit(1);
});
