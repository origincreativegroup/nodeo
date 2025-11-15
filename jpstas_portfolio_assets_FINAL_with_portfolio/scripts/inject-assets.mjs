#!/usr/bin/env node

import path from "node:path";
import { injectAssets } from "../src/nodeo-plugin-assets.mjs";

const args = process.argv.slice(2);
const dry = args.includes("--dry") || args.includes("--dry-run");
const projFlagIndex = Math.max(args.indexOf("--project"), args.indexOf("-p"));
const project = projFlagIndex >= 0 ? args[projFlagIndex + 1] : null;
const root = path.resolve(process.cwd());

const urlsPath = project ? `assets/urls.${project}.json` : undefined;

try {
  const res = await injectAssets({ dryRun: dry, root, urlsPath });
  const prefix = dry ? "[DRY RUN] " : "";
  console.log(prefix + `Replaced ${res.replaced} placeholders across ${res.files} files.`);
  if (res.missing?.length) {
    console.warn(`[inject-assets] ${res.missing.length} placeholders left unchanged:`);
    res.missing.forEach(item => {
      console.warn(`  - ${item.type.toUpperCase()} ${item.key} (${item.reason}) in ${item.file}`);
    });
  }
} catch (err) {
  console.error("Asset injection failed:", err.message);
  process.exit(1);
}
