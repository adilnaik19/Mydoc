"""My Doc+ HTTP server (stdlib only).

Serves the REST API under /api/* and the static SPA for everything else.
"""
import json
import mimetypes
import os
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlparse, parse_qs

import config
from handlers import build_router

ROUTER = build_router()

SECURITY_HEADERS = {
    "X-Content-Type-Options": "nosniff",
    "X-Frame-Options": "DENY",
    "Referrer-Policy": "no-referrer",
}


class Handler(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"

    # ------------------------- helpers -------------------------
    def _set_common(self):
        for k, v in SECURITY_HEADERS.items():
            self.send_header(k, v)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Headers", "Content-Type, Authorization")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, PUT, DELETE, OPTIONS")

    def _send_json(self, status, obj):
        body = json.dumps(obj).encode()
        self.send_response(status)
        self._set_common()
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _read_body(self):
        length = int(self.headers.get("Content-Length", 0) or 0)
        if not length:
            return {}
        raw = self.rfile.read(length)
        try:
            return json.loads(raw.decode() or "{}")
        except json.JSONDecodeError:
            return {}

    # ------------------------- static -------------------------
    def _serve_static(self, path):
        if path == "/" or path == "":
            path = "/index.html"
        # prevent path traversal
        safe = os.path.normpath(path).lstrip("/")
        full = os.path.join(config.FRONTEND_DIR, safe)
        if not full.startswith(config.FRONTEND_DIR) or not os.path.isfile(full):
            # SPA fallback
            full = os.path.join(config.FRONTEND_DIR, "index.html")
            if not os.path.isfile(full):
                self._send_json(404, {"error": "Not found"})
                return
        ctype = mimetypes.guess_type(full)[0] or "application/octet-stream"
        with open(full, "rb") as f:
            data = f.read()
        self.send_response(200)
        self._set_common()
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    # ------------------------- dispatch -------------------------
    def _handle(self, method):
        parsed = urlparse(self.path)
        path = parsed.path
        if path.startswith("/api/"):
            query = {k: v[0] for k, v in parse_qs(parsed.query).items()}
            body = self._read_body() if method in ("POST", "PUT", "DELETE") else {}
            status, result = ROUTER.dispatch(method, path, query, body, self.headers)
            self._send_json(status, result)
        elif method == "GET":
            self._serve_static(path)
        else:
            self._send_json(404, {"error": "Not found"})

    def do_GET(self):
        self._handle("GET")

    def do_POST(self):
        self._handle("POST")

    def do_PUT(self):
        self._handle("PUT")

    def do_DELETE(self):
        self._handle("DELETE")

    def do_OPTIONS(self):
        self.send_response(204)
        self._set_common()
        self.send_header("Content-Length", "0")
        self.end_headers()

    def log_message(self, fmt, *args):  # quieter logs
        pass


def serve():
    httpd = ThreadingHTTPServer((config.HOST, config.PORT), Handler)
    print(f"My Doc+ running at http://{config.HOST}:{config.PORT}")
    httpd.serve_forever()
