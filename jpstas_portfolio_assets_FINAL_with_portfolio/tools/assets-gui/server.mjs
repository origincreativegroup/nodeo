// tools/assets-gui/server.mjs
import http from "node:http";
import fs from "node:fs";
import path from "node:path";
import url from "node:url";

const __dirname = path.dirname(url.fileURLToPath(import.meta.url));
const ROOT = path.resolve(__dirname, "..", "..");
const ASSETS_DIR = path.join(ROOT, "assets");
const PUBLIC_DIR = path.join(__dirname, "public");
const PORT = process.env.PORT || 5173;

function send(res, code, type, body) {
  res.writeHead(code, { "Content-Type": type, "Access-Control-Allow-Origin": "*" });
  res.end(body);
}

function serveStatic(req, res) {
  let p = req.url.split("?")[0];
  if (p === "/") p = "/index.html";
  const filePath = path.join(PUBLIC_DIR, p.replace(/^\//, ""));
  if (!filePath.startsWith(PUBLIC_DIR)) return send(res, 403, "text/plain", "Forbidden");
  fs.readFile(filePath, (err, buf) => {
    if (err) return send(res, 404, "text/plain", "Not found");
    const ext = path.extname(filePath).slice(1);
    const types = { html: "text/html", css: "text/css", js: "text/javascript", json: "application/json" };
    send(res, 200, types[ext] || "text/plain", buf);
  });
}

const server = http.createServer(async (req, res) => {
  const parsed = new URL(req.url, `http://localhost:${PORT}`);
  const project = parsed.searchParams.get("project");

  // Manifest
  if (req.method === "GET" && parsed.pathname === "/api/manifest") {
    const p = path.join(ASSETS_DIR, "assets.manifest.json");
    return fs.readFile(p, (e, b) => e ? send(res, 500, "text/plain", e.message) : send(res, 200, "application/json", b));
  }

  // URLs (GET)
  if (req.method === "GET" && parsed.pathname === "/api/urls") {
    const name = project ? `urls.${project}.json` : "urls.json";
    const primary = path.join(ASSETS_DIR, name);
    const globalFile = path.join(ASSETS_DIR, "urls.json");
    const fallback = path.join(ASSETS_DIR, "urls.example.json");
    const file = fs.existsSync(primary) ? primary : (fs.existsSync(globalFile) ? globalFile : fallback);
    return fs.readFile(file, (e, b) => e ? send(res, 500, "text/plain", e.message) : send(res, 200, "application/json", b));
  }

  // URLs (POST)
  if (req.method === "POST" && parsed.pathname === "/api/urls") {
    let body = "";
    req.on("data", chunk => body += chunk);
    req.on("end", () => {
      try {
        const data = JSON.parse(body || "{}");
        const name = project ? `urls.${project}.json` : "urls.json";
        const p = path.join(ASSETS_DIR, name);
        fs.writeFile(p, JSON.stringify(data, null, 2), (e) => {
          if (e) return send(res, 500, "text/plain", e.message);
          send(res, 200, "application/json", JSON.stringify({ ok: true, file: name }));
        });
      } catch (err) {
        send(res, 400, "text/plain", "Invalid JSON");
      }
    });
    return;
  }

  // Inject (POST)
  if (req.method === "POST" && parsed.pathname === "/api/inject") {
    const dry = parsed.searchParams.get("dry") === "1";
    const proj = project ? ` --project ${project}` : "";
    const { exec } = await import("node:child_process");
    const cmd = dry ? `jspow run assets:inject --dry${proj}` : `jspow run assets:inject${proj}`;
    exec(cmd, { cwd: ROOT }, (err, stdout, stderr) => {
      const body = JSON.stringify({
        ok: !err,
        cmd,
        stdout: stdout?.toString() || "",
        stderr: stderr?.toString() || (err && err.message) || ""
      });
      send(res, err ? 500 : 200, "application/json", body);
    });
    return;
  }

  // CORS preflight
  if (req.method === "OPTIONS") {
    res.writeHead(204, {
      "Access-Control-Allow-Origin": "*",
      "Access-Control-Allow-Methods": "GET,POST,OPTIONS",
      "Access-Control-Allow-Headers": "Content-Type",
    });
    return res.end();
  }

  return serveStatic(req, res);
});

server.listen(PORT, () => {
  console.log(`Assets GUI running at http://localhost:${PORT}`);
  console.log(`Reads: assets/assets.manifest.json & assets/urls*.json`);
  console.log(`POST /api/urls?project=slug to save per-project mapping.`);
  console.log(`POST /api/inject?project=slug to run injection for that mapping.`);
});
