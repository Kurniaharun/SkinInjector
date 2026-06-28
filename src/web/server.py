"""HTTP server — static web + REST API (stdlib only)."""

from __future__ import annotations

import json
import logging
import mimetypes
import re
import socket
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any
from urllib.parse import parse_qs, unquote, urlparse

from ..config import ROOT_DIR
from ..ui.branding import APP_NAME, AUTHOR
from .api import get_web_api

LOG = logging.getLogger(__name__)

WEB_DIR = ROOT_DIR / "web"

MIME_OVERRIDES = {
    ".html": "text/html; charset=utf-8",
    ".css": "text/css; charset=utf-8",
    ".js": "application/javascript; charset=utf-8",
    ".json": "application/json; charset=utf-8",
    ".svg": "image/svg+xml",
}


def _json_response(handler: BaseHTTPRequestHandler, code: int, data: Any) -> None:
    body = json.dumps(data, ensure_ascii=False).encode("utf-8")
    handler.send_response(code)
    handler.send_header("Content-Type", "application/json; charset=utf-8")
    handler.send_header("Content-Length", str(len(body)))
    handler.send_header("Access-Control-Allow-Origin", "*")
    handler.end_headers()
    handler.wfile.write(body)


def _read_body(handler: BaseHTTPRequestHandler) -> dict[str, Any]:
    length = int(handler.headers.get("Content-Length", 0))
    if length <= 0:
        return {}
    raw = handler.rfile.read(length)
    return json.loads(raw.decode("utf-8"))


class SkinjectHTTPServer(ThreadingHTTPServer):
    allow_reuse_address = True
    allow_reuse_port = True


def _bind_error(exc: BaseException) -> bool:
    if isinstance(exc, PermissionError):
        return True
    if isinstance(exc, OSError):
        code = getattr(exc, "winerror", None) or getattr(exc, "errno", None)
        return code in (13, 98, 10013, 10048)
    return False


def _bind_reason(exc: BaseException) -> str:
    code = getattr(exc, "winerror", None) or getattr(exc, "errno", None)
    if code in (13, 10013):
        return "permission denied (butuh root/admin untuk port <1024)"
    if code in (98, 10048):
        return "port sudah dipakai"
    return str(exc)


def _can_bind(host: str, port: int) -> tuple[bool, str | None]:
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        sock.bind((host, port))
        return True, None
    except (PermissionError, OSError) as e:
        return False, _bind_reason(e)
    finally:
        try:
            sock.close()
        except OSError:
            pass


def resolve_listen_port(host: str, preferred: int) -> int:
    """Cari port pertama yang bisa di-bind (fallback otomatis)."""
    fallbacks = (8080, 8765, 8888)
    candidates: list[int] = []
    for p in (preferred, *fallbacks):
        if p not in candidates:
            candidates.append(p)

    errors: list[str] = []
    for port in candidates:
        ok, reason = _can_bind(host, port)
        if ok:
            if port != preferred:
                print(f"Port {preferred} gagal ({errors[0] if errors else 'tidak tersedia'}) — pakai {port}")
            return port
        errors.append(f"{port}: {reason}")
        LOG.warning("Bind gagal port %s — %s", port, reason)

    msg = "Tidak bisa bind port:\n  " + "\n  ".join(errors)
    msg += "\nCoba: python server.py --port 8080"
    msg += "\nAtau matikan proses lama: python killserver.py"
    raise OSError(msg)


class SkinjectHandler(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"

    def log_message(self, fmt: str, *args: Any) -> None:
        LOG.info("%s - %s", self.address_string(), fmt % args)

    def do_OPTIONS(self) -> None:
        self.send_response(204)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()

    def do_GET(self) -> None:
        parsed = urlparse(self.path)
        if parsed.path.startswith("/api/"):
            self._handle_api("GET", parsed)
            return
        self._serve_static(parsed.path)

    def do_POST(self) -> None:
        parsed = urlparse(self.path)
        if parsed.path.startswith("/api/"):
            self._handle_api("POST", parsed)
            return
        self.send_error(405, "Method Not Allowed")

    def _handle_api(self, method: str, parsed) -> None:
        api = get_web_api()
        path = parsed.path
        qs = parse_qs(parsed.query)

        try:
            if path == "/api/status" and method == "GET":
                return _json_response(self, 200, api.status())
            if path == "/api/meta" and method == "GET":
                return _json_response(self, 200, api.meta())
            if path == "/api/heroes" and method == "GET":
                return _json_response(self, 200, api.heroes())
            if path == "/api/roles" and method == "GET":
                return _json_response(self, 200, api.roles())
            if path == "/api/upgrade" and method == "GET":
                return _json_response(self, 200, api.upgrade_menu())
            if path == "/api/effects/categories" and method == "GET":
                return _json_response(self, 200, api.effect_categories())
            if path == "/api/custom/bundles" and method == "GET":
                return _json_response(self, 200, api.custom_bundles())
            if path == "/api/search" and method == "GET":
                q = (qs.get("q") or [""])[0]
                return _json_response(self, 200, api.search(q))

            m = re.match(r"^/api/roles/([^/]+)/heroes$", path)
            if m and method == "GET":
                role = unquote(m.group(1))
                return _json_response(self, 200, api.role_heroes(role))

            m = re.match(r"^/api/heroes/([^/]+)/skins$", path)
            if m and method == "GET":
                name = unquote(m.group(1))
                return _json_response(self, 200, api.hero_skins(name))

            m = re.match(r"^/api/upgrade/(\d+)/skins$", path)
            if m and method == "GET":
                return _json_response(self, 200, api.upgrade_skins(int(m.group(1))))

            m = re.match(r"^/api/effects/([^/]+)/skins$", path)
            if m and method == "GET":
                cat = unquote(m.group(1))
                return _json_response(self, 200, api.effect_skins(cat))

            m = re.match(r"^/api/custom/([^/]+)/skins$", path)
            if m and method == "GET":
                bid = unquote(m.group(1))
                return _json_response(self, 200, api.bundle_skins(bid))

            if path == "/api/inject" and method == "POST":
                body = _read_body(self)
                return _json_response(self, 200, api.inject(body))

            return _json_response(self, 404, {"error": "not found"})
        except Exception as e:
            LOG.exception("API error: %s", path)
            return _json_response(self, 500, {"error": str(e)})

    def _serve_static(self, url_path: str) -> None:
        rel = url_path if url_path != "/" else "/index.html"
        rel = Path(unquote(rel.lstrip("/")))
        if ".." in rel.parts:
            self.send_error(403)
            return

        full = (WEB_DIR / rel).resolve()
        if not str(full).startswith(str(WEB_DIR.resolve())):
            self.send_error(403)
            return

        if not full.is_file():
            fallback = WEB_DIR / "index.html"
            if fallback.is_file():
                full = fallback
            else:
                self.send_error(404)
                return

        ext = full.suffix.lower()
        ctype = MIME_OVERRIDES.get(ext) or mimetypes.guess_type(str(full))[0] or "application/octet-stream"
        data = full.read_bytes()
        self.send_response(200)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)


def run_server(host: str = "0.0.0.0", port: int = 8080) -> None:
    from ..fs_utils import setup_logging
    from ..config import LOG_DIR

    setup_logging(LOG_DIR, quiet_console=True)
    port = resolve_listen_port(host, port)

    server = SkinjectHTTPServer((host, port), SkinjectHandler)
    print("")
    print(f"  {APP_NAME} Web — by {AUTHOR}")
    print(f"  http://localhost:{port}")
    print(f"  http://127.0.0.1:{port}")
    print(f"  Buka dari HP: http://<IP-device>:{port}")
    if port != 80:
        print(f"  [i] Port 80 butuh root — jalankan: python server.py --port 80")
    print("")
    server.serve_forever()
