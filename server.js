#!/usr/bin/env node
/**
 * SkinJECT Web Server — by KurrXd
 * Port 80 (fallback 8080) · static web + API
 */

const http = require("http");
const fs = require("fs");
const path = require("path");
const { execFile } = require("child_process");

const ROOT = __dirname;
const WEB = path.join(ROOT, "web");
const CATALOG = path.join(ROOT, "data", "catalog");
const BRIDGE = path.join(ROOT, "src", "web_bridge.py");
const PORT = Number(process.env.PORT || 80);
const PYTHON = process.env.PYTHON || "python";

const MIME = {
  ".html": "text/html; charset=utf-8",
  ".css": "text/css; charset=utf-8",
  ".js": "application/javascript; charset=utf-8",
  ".json": "application/json; charset=utf-8",
  ".png": "image/png",
  ".jpg": "image/jpeg",
  ".webp": "image/webp",
  ".svg": "image/svg+xml",
  ".ico": "image/x-icon",
};

const EFFECT_CATS = [
  { id: "Recall Animations", label: "Recall" },
  { id: "Emotes", label: "Emotes" },
  { id: "TRAIL ANIMATION", label: "Trail" },
  { id: "RESPAWN ANIMATION", label: "Respawn" },
  { id: "PAINTED SKIN", label: "Painted" },
  { id: "ELIMINATED BATTLE", label: "Eliminated" },
];

let catalogCache = null;

function readJson(file) {
  const p = path.join(CATALOG, file);
  if (!fs.existsSync(p)) return null;
  return JSON.parse(fs.readFileSync(p, "utf8"));
}

function loadCatalog() {
  if (catalogCache) return catalogCache;
  catalogCache = {
    heroes: readJson("heroes_groups.json") || {},
    upgradeMenu: readJson("upgrade_menu.json") || [],
    upgradeLabels: readJson("upgrade_labels.json") || [],
    bundles: readJson("custom_bundles.json") || [],
    roles: readJson("role_categories.json") || [],
    heroesByRole: readJson("heroes_by_role.json") || {},
    meta: readJson("meta.json") || {},
  };
  return catalogCache;
}

function pyBridge(cmd, ...args) {
  return new Promise((resolve, reject) => {
    execFile(
      PYTHON,
      [BRIDGE, cmd, ...args],
      { cwd: ROOT, maxBuffer: 16 * 1024 * 1024, timeout: 600000 },
      (err, stdout, stderr) => {
        if (err) {
          reject(new Error(stderr || err.message));
          return;
        }
        try {
          resolve(JSON.parse(stdout.trim() || "null"));
        } catch (e) {
          reject(new Error(stdout || "invalid json"));
        }
      }
    );
  });
}

function sendJson(res, code, data) {
  const body = JSON.stringify(data);
  res.writeHead(code, {
    "Content-Type": "application/json; charset=utf-8",
    "Access-Control-Allow-Origin": "*",
  });
  res.end(body);
}

function parseBody(req) {
  return new Promise((resolve, reject) => {
    let data = "";
    req.on("data", (c) => (data += c));
    req.on("end", () => {
      try {
        resolve(data ? JSON.parse(data) : {});
      } catch (e) {
        reject(e);
      }
    });
    req.on("error", reject);
  });
}

async function handleApi(req, res, url) {
  const cat = loadCatalog();

  if (url.pathname === "/api/status" && req.method === "GET") {
    try {
      const st = await pyBridge("status");
      return sendJson(res, 200, st);
    } catch (e) {
      return sendJson(res, 200, { ok: false, error: String(e) });
    }
  }

  if (url.pathname === "/api/heroes" && req.method === "GET") {
    const heroes = Object.keys(cat.heroes).sort((a, b) => a.localeCompare(b));
    return sendJson(res, 200, { heroes });
  }

  if (url.pathname === "/api/roles" && req.method === "GET") {
    const roles = cat.roles.map((r) => r.name || r).filter(Boolean);
    return sendJson(res, 200, { roles });
  }

  const roleHeroes = url.pathname.match(/^\/api\/roles\/([^/]+)\/heroes$/);
  if (roleHeroes && req.method === "GET") {
    const role = decodeURIComponent(roleHeroes[1]);
    const heroes = cat.heroesByRole[role] || [];
    return sendJson(res, 200, { heroes });
  }

  const heroSkins = url.pathname.match(/^\/api\/heroes\/([^/]+)\/skins$/);
  if (heroSkins && req.method === "GET") {
    const name = decodeURIComponent(heroSkins[1]);
    try {
      const skins = await pyBridge("hero_skins", name);
      return sendJson(res, 200, { skins });
    } catch (e) {
      return sendJson(res, 500, { error: String(e) });
    }
  }

  if (url.pathname === "/api/upgrade" && req.method === "GET") {
    const items = cat.upgradeMenu.map((e, i) => ({
      index: i,
      id: e.id,
      key: e.heroName,
      label: cat.upgradeLabels[i] || e.heroName,
      image_url: e.img || "",
    }));
    return sendJson(res, 200, { items });
  }

  const upSkins = url.pathname.match(/^\/api\/upgrade\/(\d+)\/skins$/);
  if (upSkins && req.method === "GET") {
    try {
      const skins = await pyBridge("upgrade_skins", upSkins[1]);
      return sendJson(res, 200, { skins });
    } catch (e) {
      return sendJson(res, 500, { error: String(e) });
    }
  }

  if (url.pathname === "/api/effects/categories" && req.method === "GET") {
    return sendJson(res, 200, { categories: EFFECT_CATS });
  }

  const fxSkins = url.pathname.match(/^\/api\/effects\/([^/]+)\/skins$/);
  if (fxSkins && req.method === "GET") {
    const catId = decodeURIComponent(fxSkins[1]);
    try {
      const skins = await pyBridge("effect_skins", catId);
      return sendJson(res, 200, { skins });
    } catch (e) {
      return sendJson(res, 500, { error: String(e) });
    }
  }

  if (url.pathname === "/api/custom/bundles" && req.method === "GET") {
    const bundles = cat.bundles.map((b) => ({
      id: String(b.id),
      name: b.name || `Bundle ${b.id}`,
      image_url: b.img || "",
    }));
    return sendJson(res, 200, { bundles });
  }

  const bunSkins = url.pathname.match(/^\/api\/custom\/([^/]+)\/skins$/);
  if (bunSkins && req.method === "GET") {
    try {
      const skins = await pyBridge("bundle_skins", bunSkins[1]);
      return sendJson(res, 200, { skins });
    } catch (e) {
      return sendJson(res, 500, { error: String(e) });
    }
  }

  if (url.pathname === "/api/search" && req.method === "GET") {
    const q = url.searchParams.get("q") || "";
    try {
      const skins = await pyBridge("search", q);
      return sendJson(res, 200, { skins });
    } catch (e) {
      return sendJson(res, 500, { error: String(e) });
    }
  }

  if (url.pathname === "/api/inject" && req.method === "POST") {
    try {
      const body = await parseBody(req);
      const result = await pyBridge("inject", JSON.stringify(body));
      return sendJson(res, 200, result);
    } catch (e) {
      return sendJson(res, 500, { ok: false, message: String(e) });
    }
  }

  if (url.pathname === "/api/meta" && req.method === "GET") {
    return sendJson(res, 200, {
      app: "SkinJECT",
      author: "KurrXd",
      version: "2.0.0",
      meta: cat.meta,
    });
  }

  sendJson(res, 404, { error: "not found" });
}

function serveStatic(req, res, url) {
  let filePath = url.pathname === "/" ? "/index.html" : url.pathname;
  filePath = path.normalize(filePath).replace(/^(\.\.[/\\])+/, "");
  const full = path.join(WEB, filePath);

  if (!full.startsWith(WEB) || !fs.existsSync(full) || fs.statSync(full).isDirectory()) {
    const index = path.join(WEB, "index.html");
    if (fs.existsSync(index)) {
      res.writeHead(200, { "Content-Type": "text/html; charset=utf-8" });
      fs.createReadStream(index).pipe(res);
      return;
    }
    res.writeHead(404);
    res.end("Not found");
    return;
  }

  const ext = path.extname(full).toLowerCase();
  res.writeHead(200, { "Content-Type": MIME[ext] || "application/octet-stream" });
  fs.createReadStream(full).pipe(res);
}

const server = http.createServer(async (req, res) => {
  const url = new URL(req.url, `http://${req.headers.host || "localhost"}`);

  if (req.method === "OPTIONS") {
    res.writeHead(204, {
      "Access-Control-Allow-Origin": "*",
      "Access-Control-Allow-Methods": "GET, POST, OPTIONS",
      "Access-Control-Allow-Headers": "Content-Type",
    });
    return res.end();
  }

  if (url.pathname.startsWith("/api/")) {
    try {
      await handleApi(req, res, url);
    } catch (e) {
      sendJson(res, 500, { error: String(e) });
    }
    return;
  }

  serveStatic(req, res, url);
});

function listen(port) {
  server.listen(port, "0.0.0.0", () => {
    console.log("");
    console.log("  SkinJECT Web — by KurrXd");
    console.log(`  http://localhost:${port}`);
    console.log(`  http://127.0.0.1:${port}`);
    console.log("  Buka dari HP: http://<IP-device>:" + port);
    console.log("");
  });
}

server.on("error", (err) => {
  if (err.code === "EACCES" && PORT === 80) {
    console.warn("Port 80 butuh admin — fallback ke 8080");
    listen(8080);
  } else if (err.code === "EADDRINUSE") {
    console.warn(`Port ${PORT} dipakai — coba 8080`);
    listen(8080);
  } else {
    throw err;
  }
});

listen(PORT);
