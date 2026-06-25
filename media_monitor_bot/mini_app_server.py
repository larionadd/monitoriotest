from __future__ import annotations

import hashlib
import hmac
import json
import logging
import mimetypes
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from threading import Thread
from urllib.parse import parse_qsl, unquote, urlparse

from .billing import plan_text
from .config import Source
from .db import Database, normalize_url, source_allowed_for_plan
from .locales import (
    COUNTRIES,
    LANGUAGES,
    country_button_text,
    country_name,
    language_button_text,
    language_name,
    normalize_country,
    normalize_language,
)

log = logging.getLogger(__name__)


def start_static_server(
    host: str,
    port: int,
    static_path: Path,
    bot_token: str = "",
    db: Database | None = None,
    sources: list[Source] | None = None,
    require_business: bool = True,
) -> ThreadingHTTPServer:
    root = static_path.resolve()
    source_list = sources or []

    class Handler(BaseHTTPRequestHandler):
        def do_OPTIONS(self) -> None:
            parsed = urlparse(self.path)
            if not parsed.path.startswith("/api/"):
                self.send_error(404)
                return
            self.send_response(204)
            self.send_cors_headers()
            self.send_header("Cache-Control", "no-store")
            self.end_headers()

        def do_GET(self) -> None:
            parsed = urlparse(self.path)
            if parsed.path.startswith("/api/"):
                self.handle_api(parsed.path)
                return
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

        def handle_api(self, path: str) -> None:
            if not db or not bot_token:
                self.send_json({"error": "api_unavailable"}, status=503)
                return
            chat_id = self.chat_id_from_init_data()
            if chat_id is None:
                self.send_json({"error": "unauthorized"}, status=401)
                return
            if path == "/api/state":
                self.send_json(api_state(chat_id, db, source_list, require_business))
                return
            if path == "/api/recent":
                self.send_json(api_recent(chat_id, db))
                return
            self.send_json({"error": "not_found"}, status=404)

        def chat_id_from_init_data(self) -> int | None:
            init_data = self.headers.get("X-Telegram-Init-Data", "")
            return validate_init_data(init_data, bot_token)

        def send_json(self, payload: dict, status: int = 200) -> None:
            body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
            self.send_response(status)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.send_header("Cache-Control", "no-store")
            self.send_cors_headers()
            self.end_headers()
            self.wfile.write(body)

        def send_cors_headers(self) -> None:
            self.send_header("Access-Control-Allow-Origin", "*")
            self.send_header("Access-Control-Allow-Methods", "GET, OPTIONS")
            self.send_header("Access-Control-Allow-Headers", "X-Telegram-Init-Data, Content-Type")

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


def validate_init_data(init_data: str, bot_token: str) -> int | None:
    if not init_data or not bot_token:
        return None
    items = dict(parse_qsl(init_data, keep_blank_values=True))
    received_hash = items.pop("hash", "")
    if not received_hash:
        return None
    data_check_string = "\n".join(f"{key}={items[key]}" for key in sorted(items))
    secret_key = hmac.new(b"WebAppData", bot_token.encode("utf-8"), hashlib.sha256).digest()
    calculated = hmac.new(secret_key, data_check_string.encode("utf-8"), hashlib.sha256).hexdigest()
    if not hmac.compare_digest(calculated, received_hash):
        return None
    try:
        user = json.loads(items.get("user") or "{}")
        return int(user["id"])
    except (KeyError, TypeError, ValueError, json.JSONDecodeError):
        return None


def api_state(chat_id: int, db: Database, sources: list[Source], require_business: bool) -> dict:
    settings = db.get_user_settings(chat_id)
    monitoring = db.get_user_monitoring(chat_id)
    plan = db.get_active_plan(chat_id)
    language = normalize_language(settings.language_code)
    disabled = set(monitoring.disabled_source_urls)
    keyword_countries = {keyword.country_code for keyword in monitoring.keywords} or {settings.country_code}
    enabled_sources = db.get_enabled_sources(chat_id, sources, keyword_countries)
    country_sources = [source for source in sources if normalize_country(source.country) == settings.country_code]
    paid_tg = [
        source
        for source in country_sources
        if source.type == "telegram_paid" and source_allowed_for_plan(source, plan.id)
    ]
    standard_sources = [
        source
        for source in country_sources
        if source.type != "telegram_paid" and source_allowed_for_plan(source, plan.id)
    ]
    custom_sources = list(monitoring.custom_sources)
    return {
        "locked": require_business and plan.id != "business",
        "language": {
            "code": language,
            "name": language_name(language),
        },
        "languages": [
            {
                "code": code,
                "label": language_button_text(code),
                "name": language_name(code),
            }
            for code in LANGUAGES
        ],
        "country": {
            "code": settings.country_code,
            "name": country_name(settings.country_code, language),
            "label": country_button_text(settings.country_code, language),
        },
        "countries": [
            {
                "code": code,
                "label": country_button_text(code, language),
                "name": country_name(code, language),
            }
            for code in COUNTRIES
        ],
        "plan": {
            "id": plan.id,
            "name": plan.name,
            "full_text": plan.full_text,
            "max_keywords": plan.max_keywords,
            "max_custom_sources": plan.max_custom_sources,
            "alerts_per_day": plan.alerts_per_day,
            "description": plan_text(plan),
        },
        "monitoring": {
            "auto": monitoring.auto_monitoring_enabled,
            "full_text": monitoring.full_text_enabled,
            "sent_today": db.sent_today_count(chat_id),
            "active_sources": len(enabled_sources),
            "keywords": [
                {
                    "phrase": keyword.phrase,
                    "country_code": keyword.country_code,
                    "country": country_name(keyword.country_code, language),
                }
                for keyword in monitoring.keywords
            ],
            "stop_words": list(monitoring.stop_words),
            "plus_words": list(monitoring.plus_words),
        },
        "sources": {
            "standard": summarize_sources(standard_sources, disabled),
            "custom": summarize_sources(custom_sources, disabled),
            "paid_telegram": summarize_sources(paid_tg, disabled),
            "tg_blocks": tg_blocks_state(paid_tg, disabled),
        },
    }


def api_recent(chat_id: int, db: Database) -> dict:
    rows = db.recent_matches(chat_id, limit=40)
    return {
        "items": [
            {
                "sent_at": row["sent_at"],
                "keyword": row["keyword"],
                "source": row["source"],
                "title": row["title"],
                "published_at": row["published_at"],
                "url": row["url"],
                "summary": row["summary"],
            }
            for row in rows
        ]
    }


def summarize_sources(sources: list[Source], disabled: set[str]) -> dict:
    total = len(sources)
    active = sum(1 for source in sources if normalize_url(source.url) not in disabled)
    return {"total": total, "active": active}


def tg_blocks_state(sources: list[Source], disabled: set[str]) -> list[dict]:
    blocks = [sources[index : index + 50] for index in range(0, len(sources), 50)]
    result = []
    for index, block in enumerate(blocks, start=1):
        start = (index - 1) * 50 + 1
        end = start + len(block) - 1
        active = sum(1 for source in block if normalize_url(source.url) not in disabled)
        result.append(
            {
                "number": index,
                "label": f"{start}-{end}",
                "active": active,
                "total": len(block),
            }
        )
    return result
