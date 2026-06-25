from __future__ import annotations

import logging
import mimetypes
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from threading import Thread
from urllib.parse import unquote, urlparse

log = logging.getLogger(__name__)


def start_static_server(host: str, port: int, static_path: Path) -> ThreadingHTTPServer:
    root = static_path.resolve()

    class Handler(BaseHTTPRequestHandler):
        def do_GET(self) -> None:
            parsed = urlparse(self.path)
            path = unquote(parsed.path)
            if path in {"", "/", "/miniapp"}:
                relative = "index.html"
            elif path.startswith("/miniapp/"):
                relative = path.removeprefix("/miniapp/").lstrip("/") or "index.html"
            else:
                relative = path.lstrip("/")
            file_path = (root / relative).resolve()
            if not _is_inside(file_path, root) or not file_path.is_file():
                self.send_error(404)
                return
            content_type = mimetypes.guess_type(file_path.name)[0] or "application/octet-stream"
            body = file_path.read_bytes()
            self.send_response(200)
            self.send_header("Content-Type", content_type)
            self.send_header("Content-Length", str(len(body)))
            self.send_header("Cache-Control", "no-store")
            self.end_headers()
            self.wfile.write(body)

        def log_message(self, fmt: str, *args) -> None:
            log.debug("Mini App HTTP: " + fmt, *args)

    server = ThreadingHTTPServer((host, port), Handler)
    Thread(target=server.serve_forever, daemon=True, name="mini-app-server").start()
    log.info("Mini App server started on %s:%s from %s", host, port, root)
    return server


def _is_inside(path: Path, root: Path) -> bool:
    try:
        path.relative_to(root)
        return True
    except ValueError:
        return False
