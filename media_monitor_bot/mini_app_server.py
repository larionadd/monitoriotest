from __future__ import annotations

import hashlib
import hmac
import csv
import io
import json
import logging
import mimetypes
import time
import zipfile
from datetime import datetime, timedelta, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from threading import Thread
from typing import Callable, Mapping
from urllib.parse import parse_qsl, unquote, urlparse
from xml.sax.saxutils import escape as xml_escape

from .billing import clamp_monitor_interval_minutes, monitor_interval_bounds, plan_text
from .config import Source, clean_source_display_name
from .db import Database, free_source_urls, normalize_url, source_allowed_for_plan
from .importance import calculate_importance
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

THREADS_CABINET_ENABLED = False


def start_static_server(
    host: str,
    port: int,
    static_path: Path,
    bot_token: str = "",
    db: Database | None = None,
    sources: list[Source] | None = None,
    require_business: bool = True,
    nowpayments_ipn_handler: Callable[[bytes, Mapping[str, str]], tuple[int, dict]] | None = None,
    payment_options_handler: Callable[[int], dict] | None = None,
    checkout_handler: Callable[[int, dict], dict] | None = None,
    ai_digest_handler: Callable[[int, dict], dict] | None = None,
    ai_digest_enabled: bool = False,
    ai_digest_plan_ids: tuple[str, ...] = ("pro", "business"),
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
                self.handle_api(parsed)
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
            if parsed.path == "/api/nowpayments/ipn":
                if not nowpayments_ipn_handler:
                    self.send_json({"error": "crypto_unavailable"}, status=503)
                    return
                length = int(self.headers.get("Content-Length") or 0)
                raw_body = self.rfile.read(min(length, 262144))
                status, payload = nowpayments_ipn_handler(raw_body, dict(self.headers.items()))
                self.send_json(payload, status=status)
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
                self.send_json(
                    api_action(
                        chat_id,
                        payload,
                        db,
                        source_list,
                        require_business,
                        payment_options_handler,
                        ai_digest_enabled,
                        ai_digest_plan_ids,
                    )
                )
                return
            if parsed.path == "/api/checkout":
                if not checkout_handler:
                    self.send_json({"ok": False, "error": "checkout_unavailable"}, status=503)
                    return
                self.send_json(checkout_handler(chat_id, payload))
                return
            if parsed.path == "/api/digest":
                if not ai_digest_handler:
                    self.send_json({"ok": False, "error": "ai_digest_unavailable"}, status=503)
                    return
                self.send_json(ai_digest_handler(chat_id, payload))
                return
            self.send_json({"error": "not_found"}, status=404)

        def handle_api(self, parsed) -> None:
            if not db or not bot_token:
                self.send_json({"error": "api_unavailable"}, status=503)
                return
            chat_id = self.chat_id_from_init_data()
            if chat_id is None:
                self.send_json({"error": "unauthorized"}, status=401)
                return
            if parsed.path == "/api/state":
                self.send_json(
                    api_state(
                        chat_id,
                        db,
                        source_list,
                        require_business,
                        payment_options_handler,
                        ai_digest_enabled,
                        ai_digest_plan_ids,
                    )
                )
                return
            if parsed.path == "/api/recent":
                params = dict(parse_qsl(parsed.query, keep_blank_values=True))
                self.send_json(api_recent(chat_id, db, source_list, params))
                return
            if parsed.path.startswith("/api/report."):
                params = dict(parse_qsl(parsed.query, keep_blank_values=True))
                try:
                    body, filename, content_type = api_report_file(chat_id, db, source_list, params, parsed.path)
                except ValueError:
                    self.send_json({"error": "not_found"}, status=404)
                    return
                self.send_bytes(body, content_type=content_type, filename=filename)
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

        def send_bytes(
            self,
            body: bytes,
            status: int = 200,
            content_type: str = "application/octet-stream",
            filename: str | None = None,
        ) -> None:
            self.send_response(status)
            self.send_header("Content-Type", content_type)
            self.send_header("Content-Length", str(len(body)))
            self.send_header("Cache-Control", "no-store")
            if filename:
                self.send_header("Content-Disposition", f'attachment; filename="{filename}"')
            self.send_cors_headers()
            self.end_headers()
            self.wfile.write(body)

        def send_cors_headers(self) -> None:
            self.send_header("Access-Control-Allow-Origin", "*")
            self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
            self.send_header("Access-Control-Allow-Headers", "X-Telegram-Init-Data, Content-Type")
            self.send_header("Access-Control-Expose-Headers", "Content-Disposition")

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


def validate_init_data(init_data: str, bot_token: str, max_age_seconds: int = 86400) -> int | None:
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
    if max_age_seconds > 0:
        # Відкидаємо застарілий initData, щоб перехоплений токен не можна було відтворювати безстроково.
        try:
            issued_at = int(items.get("auth_date", ""))
        except (TypeError, ValueError):
            return None
        if time.time() - issued_at > max_age_seconds:
            return None
    try:
        user = json.loads(items.get("user") or "{}")
        return int(user["id"])
    except (KeyError, TypeError, ValueError, json.JSONDecodeError):
        return None


def api_state(
    chat_id: int,
    db: Database,
    sources: list[Source],
    require_business: bool,
    payment_options_handler: Callable[[int], dict] | None = None,
    ai_digest_enabled: bool = False,
    ai_digest_plan_ids: tuple[str, ...] = ("pro", "business"),
) -> dict:
    settings = db.get_user_settings(chat_id)
    monitoring = db.get_user_monitoring(chat_id)
    plan = db.get_active_plan(chat_id)
    language = normalize_language(settings.language_code)
    disabled = set(monitoring.disabled_source_urls)
    active_keywords = [keyword for keyword in monitoring.keywords if not keyword.paused]
    keyword_countries = {keyword.country_code for keyword in active_keywords} or {settings.country_code}
    enabled_sources = db.get_enabled_sources(chat_id, sources, keyword_countries)
    country_sources = [source for source in sources if normalize_country(source.country) == settings.country_code]
    free_urls = free_source_urls(country_sources) if plan.id == "free" else None
    paid_tg = [
        source
        for source in country_sources
        if source.type == "telegram_paid" and source_allowed_for_plan(source, plan.id, free_urls)
    ]
    registry_types = {"registry", "prozorro", "prozorro_plan", "prozorro_sale", "rada_bills"}
    registry_sources = [
        source
        for source in country_sources
        if source.type in registry_types and source_allowed_for_plan(source, plan.id, free_urls)
    ]
    standard_sources = [
        source
        for source in country_sources
        if source.type not in {"telegram_paid", *registry_types} and source_allowed_for_plan(source, plan.id, free_urls)
    ]
    custom_sources = list(monitoring.custom_sources)
    interval_minutes = clamp_monitor_interval_minutes(monitoring.monitor_interval_minutes or None, plan.id)
    interval_min, interval_max = monitor_interval_bounds(plan.id)
    ai_digest_allowed_plans = {item.strip().lower() for item in ai_digest_plan_ids}
    importance_rating_available = plan.id in {"pro", "business"}
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
            "interval_minutes": interval_minutes,
            "interval_min": interval_min,
            "interval_max": interval_max,
            "interval_step": 1,
            "full_text": monitoring.full_text_enabled and plan.full_text,
            "importance_rating": monitoring.importance_rating_enabled and importance_rating_available,
            "sent_today": db.sent_today_count(chat_id),
            "active_sources": len(enabled_sources),
            "monitoring_sources": len(enabled_sources),
            "monitoring_countries": sorted(keyword_countries),
            "source_breakdown": source_breakdown_by_country(enabled_sources, language),
            "active_keywords": len(active_keywords),
            "keywords": [
                {
                    "phrase": keyword.phrase,
                    "country_code": keyword.country_code,
                    "country": country_name(keyword.country_code, language),
                    "paused": keyword.paused,
                    "silent": keyword.silent,
                }
                for keyword in monitoring.keywords
            ],
            "stop_words": list(monitoring.stop_words),
            "plus_words": list(monitoring.plus_words),
        },
        "threads": {
            "available": THREADS_CABINET_ENABLED and plan.id == "business",
            "enabled": THREADS_CABINET_ENABLED and monitoring.threads_search_enabled and plan.id == "business",
            "hours": monitoring.threads_search_hours,
            "media_filter": monitoring.threads_media_filter,
            "link_filter": monitoring.threads_link_filter,
            "result_limit": monitoring.threads_result_limit,
            "search_type": monitoring.threads_search_type,
            "limit_max": 100,
            "hours_min": 1,
            "hours_max": 24,
        },
        "features": {
            "ai_digest": ai_digest_enabled and (not ai_digest_allowed_plans or plan.id in ai_digest_allowed_plans),
            "importance_rating": importance_rating_available,
        },
        "ai_digest": latest_ai_digest_payload(db, chat_id),
        "sources": {
            "standard": summarize_sources(standard_sources, disabled),
            "registry": summarize_sources(registry_sources, disabled),
            "custom": summarize_sources(custom_sources, disabled),
            "paid_telegram": summarize_sources(paid_tg, disabled),
            "standard_items": source_items(standard_sources, disabled, limit=500, language=language),
            "registry_items": source_items(registry_sources, disabled, limit=500, language=language),
            "custom_items": source_items(custom_sources, disabled, limit=500, language=language),
            "paid_telegram_items": source_items(paid_tg, disabled, limit=500, language=language),
        },
        "payments": payment_options_handler(chat_id) if payment_options_handler else {"plans": [], "methods": {}},
    }


def latest_ai_digest_payload(db: Database, chat_id: int) -> dict:
    row = db.latest_ai_digest(chat_id)
    if not row:
        return {"last": None}
    try:
        digest = json.loads(row["digest_json"] or "{}")
        params = json.loads(row["params_json"] or "{}")
    except (TypeError, ValueError, json.JSONDecodeError):
        return {"last": None}
    if not isinstance(digest, dict):
        return {"last": None}
    if isinstance(params, dict):
        digest.setdefault("params", params)
    digest.setdefault("created_at", row["created_at"] or "")
    return {"last": digest}


def source_breakdown_by_country(sources: list[Source], language: str) -> list[dict[str, object]]:
    counts: dict[str, int] = {}
    for source in sources:
        code = normalize_country(source.country)
        counts[code] = counts.get(code, 0) + 1
    return [
        {
            "country_code": code,
            "country": country_name(code, language),
            "count": count,
        }
        for code, count in sorted(
            counts.items(),
            key=lambda item: (-item[1], country_name(item[0], language)),
        )
    ]


def api_action(
    chat_id: int,
    payload: dict,
    db: Database,
    sources: list[Source],
    require_business: bool,
    payment_options_handler: Callable[[int], dict] | None = None,
    ai_digest_enabled: bool = False,
    ai_digest_plan_ids: tuple[str, ...] = ("pro", "business"),
) -> dict:
    action = str(payload.get("action") or "").strip()
    value = str(payload.get("value") or "").strip()
    settings = db.get_user_settings(chat_id)

    def current_state() -> dict:
        return api_state(
            chat_id,
            db,
            sources,
            require_business,
            payment_options_handler,
            ai_digest_enabled,
            ai_digest_plan_ids,
        )

    if action == "set_language":
        db.set_language(chat_id, str(payload.get("language") or value))
    elif action == "set_country":
        db.set_country(chat_id, str(payload.get("country") or value))
    elif action == "add_keyword":
        plan = db.get_active_plan(chat_id)
        if db.active_keyword_count(chat_id) >= plan.max_keywords:
            return {"ok": False, "error": "keyword_limit", "state": current_state()}
        db.add_keyword(chat_id, value)
    elif action == "remove_keyword":
        db.remove_keyword(chat_id, value, str(payload.get("country_code") or ""))
    elif action == "keyword_pause":
        db.set_keyword_paused(
            chat_id,
            value,
            str(payload.get("country_code") or settings.country_code),
            bool(payload.get("enabled")),
        )
    elif action == "keyword_silent":
        db.set_keyword_silent(
            chat_id,
            value,
            str(payload.get("country_code") or settings.country_code),
            bool(payload.get("enabled")),
        )
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
    elif action == "monitor_interval":
        plan = db.get_active_plan(chat_id)
        try:
            minutes = int(payload.get("minutes") or value)
        except (TypeError, ValueError):
            return {
                "ok": False,
                "error": "bad_interval",
                "state": current_state(),
            }
        db.set_monitor_interval_minutes(chat_id, clamp_monitor_interval_minutes(minutes, plan.id))
    elif action == "fulltext":
        enabled = bool(payload.get("enabled"))
        plan = db.get_active_plan(chat_id)
        if enabled and not plan.full_text:
            return {
                "ok": False,
                "error": "fulltext_unavailable",
                "state": current_state(),
            }
        db.set_full_text_enabled(chat_id, enabled)
    elif action == "importance_rating":
        enabled = bool(payload.get("enabled"))
        plan = db.get_active_plan(chat_id)
        if enabled and plan.id not in {"pro", "business"}:
            return {
                "ok": False,
                "error": "importance_rating_unavailable",
                "state": current_state(),
            }
        db.set_importance_rating_enabled(chat_id, enabled)
    elif action == "threads_settings":
        plan = db.get_active_plan(chat_id)
        if not THREADS_CABINET_ENABLED or plan.id != "business":
            return {
                "ok": False,
                "error": "threads_unavailable",
                "state": current_state(),
            }
        db.set_threads_settings(
            chat_id,
            enabled=bool(payload.get("enabled")) if "enabled" in payload else None,
            hours=_optional_int(payload.get("hours")),
            media_filter=str(payload.get("media_filter") or "") or None,
            link_filter=str(payload.get("link_filter") or "") or None,
            result_limit=_optional_int(payload.get("result_limit")),
            search_type=str(payload.get("search_type") or "") or None,
        )
    elif action == "source_toggle":
        url = str(payload.get("url") or value).strip()
        enabled = bool(payload.get("enabled"))
        if not url:
            return {"ok": False, "error": "bad_source", "state": current_state()}
        if enabled:
            db.enable_source(chat_id, url)
        else:
            db.disable_source(chat_id, url)
    elif action == "standard_sources_toggle":
        enabled = bool(payload.get("enabled"))
        plan = db.get_active_plan(chat_id)
        country_sources = [source for source in sources if normalize_country(source.country) == settings.country_code]
        free_urls = free_source_urls(country_sources) if plan.id == "free" else None
        urls = [
            source.url
            for source in country_sources
            if source_allowed_for_plan(source, plan.id, free_urls)
        ]
        if enabled:
            db.enable_sources(chat_id, urls)
        else:
            db.disable_sources(chat_id, urls)
    elif action == "remove_source":
        url = str(payload.get("url") or value).strip()
        if not url:
            return {"ok": False, "error": "bad_source", "state": current_state()}
        db.remove_user_source(chat_id, url)
        db.enable_source(chat_id, url)
    elif action == "add_rss":
        plan = db.get_active_plan(chat_id)
        if len(db.get_user_monitoring(chat_id).custom_sources) >= plan.max_custom_sources:
            return {"ok": False, "error": "custom_source_limit", "state": current_state()}
        try:
            feed = discover_rss_feed(value)
        except RssDiscoveryError:
            return {"ok": False, "error": "invalid_rss_url", "state": current_state()}
        db.add_user_source(
            chat_id,
            Source(feed.title or source_name_from_value(feed.url), feed.url, "rss", country=settings.country_code),
        )
    elif action == "add_tg":
        plan = db.get_active_plan(chat_id)
        if len(db.get_user_monitoring(chat_id).custom_sources) >= plan.max_custom_sources:
            return {"ok": False, "error": "custom_source_limit", "state": current_state()}
        url = telegram_source_url(value)
        if not valid_http_url(url) or "t.me/s/" not in url:
            return {"ok": False, "error": "invalid_tg_url", "state": current_state()}
        db.add_user_source(
            chat_id,
            Source(source_name_from_value(value), url, "telegram", country=settings.country_code),
        )
    else:
        return {"ok": False, "error": "unknown_action", "state": current_state()}
    return {"ok": True, "state": current_state()}


def api_recent(chat_id: int, db: Database, sources: list[Source], params: Mapping[str, str] | None = None) -> dict:
    params = params or {}
    settings = db.get_user_settings(chat_id)
    language = normalize_language(settings.language_code)
    countries = source_country_lookup(db, chat_id, sources, language)
    source_types = source_type_lookup(db, chat_id, sources)
    source_meta = source_meta_lookup(db, chat_id, sources)
    plan = db.get_active_plan(chat_id)
    show_importance = settings.importance_rating_enabled and plan.id in {"pro", "business"}
    source_type_filter = normalize_source_kind(params.get("source_type") or "")
    source_type_sql = source_type_filter_values(source_type_filter)
    since = recent_since(params.get("date") or "")
    has_filters = any(
        str(params.get(key) or "").strip()
        for key in ("country", "date", "keyword", "source", "source_type")
    )
    rows = (
        db.filtered_matches(
            chat_id,
            limit=5000,
            since=since,
            keyword=(params.get("keyword") or "").strip() or None,
            source=(params.get("source") or "").strip() or None,
            source_types=source_type_sql,
        )
        if has_filters
        else db.recent_matches(chat_id, limit=300)
    )
    items: list[dict] = []
    for row in rows:
        source_type = source_type_for_row(source_types, row["source"], row["source_type"])
        if is_hidden_cabinet_mention(source_type, row["source"], row["url"]):
            continue
        source_country = country_for_source(countries, row["source"])
        country_filter = (params.get("country") or "").strip()
        if country_filter and country_filter != source_country.get("code", ""):
            continue
        if source_type_filter and source_type_filter != source_type:
            continue
        source = source_for_row(source_meta, row["source"], row["url"])
        importance = (
            calculate_importance(
                keyword=row["keyword"],
                title=row["title"],
                summary=row["summary"] or "",
                published_at=row["published_at"] or "",
                source_type=source_type,
                source=source,
            )
            if show_importance
            else None
        )
        items.append(
            {
                "sent_at": row["sent_at"],
                "keyword": row["keyword"],
                "source": row["source"],
                "source_type": source_type,
                "source_country": source_country.get("name", ""),
                "source_country_code": source_country.get("code", ""),
                "title": row["title"],
                "published_at": row["published_at"],
                "url": row["url"],
                "summary": row["summary"],
                "importance": (
                    {
                        "score": importance.score,
                        "level": importance.level,
                        "reasons": list(importance.reasons),
                    }
                    if importance
                    else None
                ),
            }
        )
    return {
        "items": items
    }


def recent_since(value: str) -> str | None:
    text = str(value or "").strip().lower()
    if text == "day":
        return (datetime.now(timezone.utc) - timedelta(days=1)).isoformat()
    if text == "week":
        return (datetime.now(timezone.utc) - timedelta(days=7)).isoformat()
    return None


def source_type_filter_values(source_type: str) -> list[str]:
    if source_type == "telegram":
        return ["telegram", "telegram_paid"]
    if source_type == "rss":
        return ["rss"]
    if source_type == "prozorro":
        return ["prozorro", "prozorro_plan", "prozorro_sale", "rada_bills", "registry"]
    if source_type in {"threads", "reddit"}:
        return [source_type]
    return []


def summarize_sources(sources: list[Source], disabled: set[str]) -> dict:
    total = len(sources)
    active = sum(1 for source in sources if normalize_url(source.url) not in disabled)
    return {"total": total, "active": active}


def source_items(sources: list[Source], disabled: set[str], limit: int, language: str) -> list[dict]:
    return [
        {
            "name": source_display_name(source),
            "url": source.url,
            "type": source.type,
            "rank": source.rank,
            "subscribers": source.subscribers,
            "country_code": normalize_country(source.country),
            "country": country_name(source.country, language),
            "active": normalize_url(source.url) not in disabled,
        }
        for source in sources[:limit]
    ]


def source_display_name(source: Source) -> str:
    name = clean_source_display_name(source.name)
    if source.type in {"telegram", "telegram_paid"} and name.lower() in {"t.me", "telegram.me"}:
        username = telegram_username_from_url(source.url)
        if username:
            return f"Telegram @{username}"
    return name or source_name_from_value(source.url)


REPORT_COLUMNS = ["sent_at", "country", "keyword", "source", "title", "published_at", "url"]


def api_report_file(
    chat_id: int,
    db: Database,
    sources: list[Source],
    params: dict[str, str],
    path: str,
) -> tuple[bytes, str, str]:
    if path == "/api/report.csv":
        body, filename = api_report_csv(chat_id, db, sources, params)
        return body, filename, "text/csv; charset=utf-8"
    if path == "/api/report.xlsx":
        body, filename = api_report_xlsx(chat_id, db, sources, params)
        return body, filename, "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    if path == "/api/report.pdf":
        body, filename = api_report_pdf(chat_id, db, sources, params)
        return body, filename, "application/pdf"
    raise ValueError("unknown report format")


def api_report_csv(chat_id: int, db: Database, sources: list[Source], params: dict[str, str]) -> tuple[bytes, str]:
    days, rows = report_rows_for_export(chat_id, db, sources, params, limit=5000)
    buffer = io.StringIO()
    writer = csv.writer(buffer)
    writer.writerow(REPORT_COLUMNS)
    writer.writerows(rows)
    filename = f"monitorio-report-{chat_id}-{days}d.csv"
    return ("\ufeff" + buffer.getvalue()).encode("utf-8"), filename


def api_report_xlsx(chat_id: int, db: Database, sources: list[Source], params: dict[str, str]) -> tuple[bytes, str]:
    days, rows = report_rows_for_export(chat_id, db, sources, params, limit=5000)
    body = build_xlsx([REPORT_COLUMNS, *rows])
    return body, f"monitorio-report-{chat_id}-{days}d.xlsx"


def api_report_pdf(chat_id: int, db: Database, sources: list[Source], params: dict[str, str]) -> tuple[bytes, str]:
    days, rows = report_rows_for_export(chat_id, db, sources, params, limit=5000)
    body = build_pdf_report(days, rows)
    return body, f"monitorio-report-{chat_id}-{days}d.pdf"


def report_rows_for_export(
    chat_id: int,
    db: Database,
    sources: list[Source],
    params: dict[str, str],
    limit: int,
) -> tuple[int, list[list[str]]]:
    days = 7 if str(params.get("days") or "").strip() == "7" else 1
    since_dt = datetime.now(timezone.utc).replace(microsecond=0) - timedelta(days=days)
    rows = db.report_rows(chat_id, limit=limit, since=since_dt.isoformat())
    settings = db.get_user_settings(chat_id)
    language = normalize_language(settings.language_code)
    countries = source_country_lookup(db, chat_id, sources, language)
    source_types = source_type_lookup(db, chat_id, sources)
    country_filter = str(params.get("country") or "").strip()
    keyword_filter = str(params.get("keyword") or "").strip()
    source_filter = str(params.get("source") or "").strip()
    source_type_filter = normalize_source_kind(params.get("source_type") or "")
    exported: list[list[str]] = []
    for row in rows:
        country = country_for_source(countries, row["source"])
        source_type = source_type_for_row(source_types, row["source"], row["source_type"])
        if is_hidden_cabinet_mention(source_type, row["source"], row["url"]):
            continue
        if country_filter and country.get("code", "") != country_filter:
            continue
        if keyword_filter and safe_cell(row["keyword"]) != keyword_filter:
            continue
        if source_filter and safe_cell(row["source"]) != source_filter:
            continue
        if source_type_filter and source_type != source_type_filter:
            continue
        exported.append(
            [safe_cell(row["sent_at"]), country.get("name", ""), safe_cell(row["keyword"]),
             clean_source_display_name(safe_cell(row["source"])), safe_cell(row["title"]),
             safe_cell(row["published_at"]), safe_cell(row["url"])]
        )
    return days, exported


def safe_cell(value: object) -> str:
    return "" if value is None else str(value)


def build_xlsx(rows: list[list[str]]) -> bytes:
    sheet_rows = []
    for row_index, row in enumerate(rows, start=1):
        cells = []
        for column_index, value in enumerate(row, start=1):
            ref = f"{xlsx_column(column_index)}{row_index}"
            cells.append(
                f'<c r="{ref}" t="inlineStr"><is><t>{xml_escape(safe_cell(value))}</t></is></c>'
            )
        sheet_rows.append(f'<row r="{row_index}">{"".join(cells)}</row>')
    sheet_xml = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">'
        '<sheetViews><sheetView workbookViewId="0"/></sheetViews>'
        '<sheetFormatPr defaultRowHeight="15"/>'
        '<cols><col min="1" max="7" width="24" customWidth="1"/></cols>'
        f'<sheetData>{"".join(sheet_rows)}</sheetData>'
        '</worksheet>'
    )
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        archive.writestr(
            "[Content_Types].xml",
            '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
            '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">'
            '<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>'
            '<Default Extension="xml" ContentType="application/xml"/>'
            '<Override PartName="/xl/workbook.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet.main+xml"/>'
            '<Override PartName="/xl/worksheets/sheet1.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml"/>'
            '</Types>',
        )
        archive.writestr(
            "_rels/.rels",
            '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
            '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
            '<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="xl/workbook.xml"/>'
            '</Relationships>',
        )
        archive.writestr(
            "xl/workbook.xml",
            '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
            '<workbook xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" '
            'xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships">'
            '<sheets><sheet name="Report" sheetId="1" r:id="rId1"/></sheets>'
            '</workbook>',
        )
        archive.writestr(
            "xl/_rels/workbook.xml.rels",
            '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
            '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
            '<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet" Target="worksheets/sheet1.xml"/>'
            '</Relationships>',
        )
        archive.writestr("xl/worksheets/sheet1.xml", sheet_xml)
    return buffer.getvalue()


def xlsx_column(index: int) -> str:
    value = ""
    while index:
        index, remainder = divmod(index - 1, 26)
        value = chr(65 + remainder) + value
    return value


def build_pdf_report(days: int, rows: list[list[str]]) -> bytes:
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
    from reportlab.lib.units import mm
    from reportlab.pdfbase import pdfmetrics
    from reportlab.pdfbase.ttfonts import TTFont
    from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer

    font_name = register_report_font()
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        leftMargin=14 * mm,
        rightMargin=14 * mm,
        topMargin=14 * mm,
        bottomMargin=14 * mm,
        title="Monitorio report",
    )
    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        "MonitorioTitle",
        parent=styles["Title"],
        fontName=font_name,
        fontSize=18,
        leading=22,
        spaceAfter=10,
    )
    meta_style = ParagraphStyle(
        "MonitorioMeta",
        parent=styles["BodyText"],
        fontName=font_name,
        fontSize=9,
        leading=12,
        textColor="#5b6472",
        spaceAfter=8,
    )
    row_style = ParagraphStyle(
        "MonitorioRow",
        parent=styles["BodyText"],
        fontName=font_name,
        fontSize=8,
        leading=10,
        spaceAfter=6,
    )
    story = [
        Paragraph("Monitorio report", title_style),
        Paragraph(f"Period: last {days} day(s). Rows: {len(rows)}.", meta_style),
    ]
    if not rows:
        story.append(Paragraph("No mentions found for the selected period.", row_style))
    for row in rows:
        sent_at, country, keyword, source, title, published_at, url = [pdf_escape(cell) for cell in row]
        story.append(
            Paragraph(
                f"<b>{sent_at}</b> | {country} | {keyword} | {source}<br/>{title}<br/>{published_at}<br/>{url}",
                row_style,
            )
        )
        story.append(Spacer(1, 2))
    doc.build(story)
    return buffer.getvalue()


def register_report_font() -> str:
    from reportlab.pdfbase import pdfmetrics
    from reportlab.pdfbase.ttfonts import TTFont

    font_name = "MonitorioSans"
    if font_name in pdfmetrics.getRegisteredFontNames():
        return font_name
    for path in (
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        "/usr/share/fonts/truetype/liberation2/LiberationSans-Regular.ttf",
        "C:/Windows/Fonts/arial.ttf",
    ):
        if Path(path).is_file():
            pdfmetrics.registerFont(TTFont(font_name, path))
            return font_name
    return "Helvetica"


def pdf_escape(value: object) -> str:
    return xml_escape(safe_cell(value)).replace("\n", "<br/>")


def source_country_lookup(
    db: Database,
    chat_id: int,
    sources: list[Source],
    language: str,
) -> dict[str, dict[str, str]]:
    lookup: dict[str, dict[str, str]] = {}
    all_sources = [*sources, *db.get_user_monitoring(chat_id).custom_sources]
    for source in all_sources:
        code = normalize_country(source.country)
        payload = {"code": code, "name": country_name(code, language)}
        lookup[normalize_url(source.url)] = payload
        lookup.setdefault(clean_source_display_name(source.name).lower(), payload)
    return lookup


def source_type_lookup(
    db: Database,
    chat_id: int,
    sources: list[Source],
) -> dict[str, str]:
    lookup: dict[str, str] = {}
    all_sources = [*sources, *db.get_user_monitoring(chat_id).custom_sources]
    for source in all_sources:
        kind = normalize_source_kind(source.type)
        lookup[normalize_url(source.url)] = kind
        lookup.setdefault(clean_source_display_name(source.name).lower(), kind)
    return lookup


def source_meta_lookup(
    db: Database,
    chat_id: int,
    sources: list[Source],
) -> dict[str, Source]:
    lookup: dict[str, Source] = {}
    all_sources = [*sources, *db.get_user_monitoring(chat_id).custom_sources]
    for source in all_sources:
        lookup[normalize_url(source.url)] = source
        lookup.setdefault(clean_source_display_name(source.name).lower(), source)
    return lookup


def source_for_row(lookup: dict[str, Source], source_name: str, url: str) -> Source | None:
    return lookup.get(normalize_url(url)) or lookup.get(clean_source_display_name(source_name).lower())


def source_type_for_row(lookup: dict[str, str], source_name: str, stored_type: str | None = "") -> str:
    stored = normalize_source_kind(stored_type or "")
    if stored:
        return stored
    source = clean_source_display_name(source_name).lower()
    if source.startswith("threads"):
        return "threads"
    return lookup.get(source, "")


def is_hidden_cabinet_mention(source_type: str, source_name: str, url: str) -> bool:
    source_kind = normalize_source_kind(source_type)
    source = clean_source_display_name(source_name).lower()
    link = str(url or "").lower()
    return (
        source_kind in {"threads", "reddit"}
        or source.startswith("threads")
        or source.startswith("reddit")
        or "threads.net" in link
        or "reddit.com/" in link
    )


def normalize_source_kind(value: object) -> str:
    text = str(value or "").strip().lower()
    if text in {"telegram", "telegram_paid"}:
        return "telegram"
    if text in {"registry", "prozorro", "prozorro_plan", "prozorro_sale", "rada_bills"}:
        return "prozorro"
    if text in {"rss", "threads", "reddit"}:
        return text
    return ""


def country_for_source(lookup: dict[str, dict[str, str]], source_name: str) -> dict[str, str]:
    return lookup.get(clean_source_display_name(source_name).lower(), {})


def _optional_int(value: object) -> int | None:
    if value is None or value == "":
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


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


def telegram_username_from_url(value: str) -> str:
    parsed = urlparse(value.strip())
    if parsed.netloc not in {"t.me", "telegram.me", "www.t.me", "www.telegram.me"}:
        return ""
    parts = [part for part in parsed.path.strip("/").split("/") if part]
    if not parts:
        return ""
    if parts[0] == "s" and len(parts) > 1:
        return parts[1]
    return parts[0]


def source_name_from_value(value: str) -> str:
    raw = value.strip()
    if raw.startswith("@"):
        return "Telegram " + raw
    username = telegram_username_from_url(raw)
    if username:
        return "Telegram @" + username
    parsed = urlparse(raw)
    if parsed.netloc:
        return parsed.netloc.removeprefix("www.")
    return raw[:60] or "My source"


def valid_http_url(value: str) -> bool:
    parsed = urlparse(value.strip())
    return parsed.scheme in {"http", "https"} and bool(parsed.netloc)
