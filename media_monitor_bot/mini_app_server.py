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
from .rss_discovery import RssDiscoveryError, discover_rss_feed

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

        def do_POST(self) -> None:
            parsed = urlparse(self.path)
            if not parsed.path.startswith("/api/"):
                self.send_error(404)
                return
            if not db or not bot_token:
                self.send_json({"error": "api_unavailable"}, status=503)
                return
            chat_id = self.chat_id_from_init_data()
            if chat_id is None:
                self.send_json({"error": "unauthorized"}, status=401)
                return
            length = int(self.headers.get("Content-Length") or 0)
            raw_body = self.rfile.read(min(length, 65536))
            try:
                payload = json.loads(raw_body.decode("utf-8") or "{}")
            except json.JSONDecodeError:
                self.send_json({"error": "bad_json"}, status=400)
                return
            if parsed.path == "/api/action":
                self.send_json(api_action(chat_id, payload, db, source_list, require_business))
                return
            self.send_json({"error": "not_found"}, status=404)

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
            self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
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
    selected_country_sources = db.get_enabled_sources(chat_id, sources, {settings.country_code})
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
            "active_sources": len(selected_country_sources),
            "monitoring_sources": len(enabled_sources),
            "monitoring_countries": sorted(keyword_countries),
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
            "standard_items": source_items(standard_sources, disabled, limit=60),
            "custom_items": source_items(custom_sources, disabled, limit=100),
            "paid_telegram_items": source_items(paid_tg, disabled, limit=100),
            "tg_blocks": tg_blocks_state(paid_tg, disabled),
        },
    }


def api_action(chat_id: int, payload: dict, db: Database, sources: list[Source], require_business: bool) -> dict:
    action = str(payload.get("action") or "").strip()
    value = str(payload.get("value") or "").strip()
    settings = db.get_user_settings(chat_id)

    if action == "set_language":
        db.set_language(chat_id, str(payload.get("language") or value))
    elif action == "set_country":
        db.set_country(chat_id, str(payload.get("country") or value))
    elif action == "add_keyword":
        plan = db.get_active_plan(chat_id)
        if len(db.get_user_monitoring(chat_id).keywords) >= plan.max_keywords:
            return {"ok": False, "error": "keyword_limit", "state": api_state(chat_id, db, sources, require_business)}
        db.add_keyword(chat_id, value)
    elif action == "remove_keyword":
        db.remove_keyword(chat_id, value)
    elif action == "add_stop_word":
        db.add_stop_word(chat_id, value)
    elif action == "remove_stop_word":
        db.remove_stop_word(chat_id, value)
    elif action == "add_plus_word":
        db.add_plus_word(chat_id, value)
    elif action == "remove_plus_word":
        db.remove_plus_word(chat_id, value)
    elif action == "auto_monitoring":
        db.set_auto_monitoring_enabled(chat_id, bool(payload.get("enabled")))
    elif action == "fulltext":
        enabled = bool(payload.get("enabled"))
        plan = db.get_active_plan(chat_id)
        if enabled and not plan.full_text:
            return {
                "ok": False,
                "error": "fulltext_unavailable",
                "state": api_state(chat_id, db, sources, require_business),
            }
        db.set_full_text_enabled(chat_id, enabled)
    elif action == "tg_block":
        try:
            block_number = int(payload.get("block") or 0)
        except (TypeError, ValueError):
            block_number = 0
        enabled = bool(payload.get("enabled"))
        if block_number <= 0:
            return {"ok": False, "error": "bad_block", "state": api_state(chat_id, db, sources, require_business)}
        paid_tg = paid_tg_sources(chat_id, db, sources)
        block = paid_tg[(block_number - 1) * 50 : block_number * 50]
        urls = [source.url for source in block]
        if enabled:
            db.enable_sources(chat_id, urls)
        else:
            db.disable_sources(chat_id, urls)
    elif action == "add_rss":
        plan = db.get_active_plan(chat_id)
        if len(db.get_user_monitoring(chat_id).custom_sources) >= plan.max_custom_sources:
            return {"ok": False, "error": "custom_source_limit", "state": api_state(chat_id, db, sources, require_business)}
        try:
            feed = discover_rss_feed(value)
        except RssDiscoveryError:
            return {"ok": False, "error": "invalid_rss_url", "state": api_state(chat_id, db, sources, require_business)}
        db.add_user_source(
            chat_id,
            Source(feed.title or source_name_from_value(feed.url), feed.url, "rss", country=settings.country_code),
        )
    elif action == "add_tg":
        plan = db.get_active_plan(chat_id)
        if len(db.get_user_monitoring(chat_id).custom_sources) >= plan.max_custom_sources:
            return {"ok": False, "error": "custom_source_limit", "state": api_state(chat_id, db, sources, require_business)}
        url = telegram_source_url(value)
        if not valid_http_url(url) or "t.me/s/" not in url:
            return {"ok": False, "error": "invalid_tg_url", "state": api_state(chat_id, db, sources, require_business)}
        db.add_user_source(
            chat_id,
            Source(source_name_from_value(value), url, "telegram", country=settings.country_code),
        )
    else:
        return {"ok": False, "error": "unknown_action", "state": api_state(chat_id, db, sources, require_business)}
    return {"ok": True, "state": api_state(chat_id, db, sources, require_business)}


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


def source_items(sources: list[Source], disabled: set[str], limit: int) -> list[dict]:
    return [
        {
            "name": source.name,
            "url": source.url,
            "type": source.type,
            "rank": source.rank,
            "subscribers": source.subscribers,
            "active": normalize_url(source.url) not in disabled,
        }
        for source in sources[:limit]
    ]


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


def paid_tg_sources(chat_id: int, db: Database, sources: list[Source]) -> list[Source]:
    settings = db.get_user_settings(chat_id)
    plan = db.get_active_plan(chat_id)
    return [
        source
        for source in sources
        if normalize_country(source.country) == settings.country_code
        and source.type == "telegram_paid"
        and source_allowed_for_plan(source, plan.id)
    ]


def telegram_source_url(value: str) -> str:
    raw = value.strip()
    if raw.startswith("@"):
        return "https://t.me/s/" + raw[1:].strip("/")
    if "t.me/" in raw and "/s/" not in raw:
        parsed = urlparse(raw)
        username = parsed.path.strip("/").split("/", 1)[0]
        if username:
            return "https://t.me/s/" + username
    return raw


def source_name_from_value(value: str) -> str:
    raw = value.strip()
    if raw.startswith("@"):
        return "Telegram " + raw
    parsed = urlparse(raw)
    if parsed.netloc:
        return parsed.netloc.removeprefix("www.")
    return raw[:60] or "My source"


def valid_http_url(value: str) -> bool:
    parsed = urlparse(value.strip())
    return parsed.scheme in {"http", "https"} and bool(parsed.netloc)
