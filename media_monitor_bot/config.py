from __future__ import annotations

import json
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class Source:
    name: str
    url: str
    type: str = "rss"
    rank: int | None = None
    subscribers: int | None = None
    country: str = "ua"
    language: str = ""


@dataclass(frozen=True)
class Config:
    telegram_bot_token: str
    database_path: Path
    sources_path: Path
    mini_app_url: str = ""
    mini_app_host: str = "127.0.0.1"
    mini_app_port: int = 8080
    mini_app_static_path: Path = Path("mini_app")
    poll_interval_seconds: int = 7200
    source_timeout_seconds: int = 15
    user_daily_limit: int = 100
    admin_chat_ids: tuple[int, ...] = ()
    require_onboarding: bool = False
    trial_plan_id: str = ""
    trial_days: int = 7
    alert_template: str = (
        "\U0001f4f0 \u041d\u043e\u0432\u0430 \u0437\u0433\u0430\u0434\u043a\u0430\n\n"
        "\u041a\u043b\u044e\u0447: {keyword}\n"
        "\u0414\u0436\u0435\u0440\u0435\u043b\u043e: {source}\n"
        "\u0417\u0430\u0433\u043e\u043b\u043e\u0432\u043e\u043a: {title}\n"
        "\u0414\u0430\u0442\u0430: {published_at}\n\n"
        "{url}"
    )


def load_config(path: str | Path) -> Config:
    config_path = Path(path)
    raw: dict[str, Any] = json.loads(config_path.read_text(encoding="utf-8-sig"))
    base = config_path.parent

    token = str(os.getenv("TELEGRAM_BOT_TOKEN") or raw.get("telegram_bot_token", "")).strip()
    if not token or token == "PUT_YOUR_TELEGRAM_BOT_TOKEN_HERE":
        raise RuntimeError(
            "\u0412\u043a\u0430\u0436\u0456\u0442\u044c telegram_bot_token \u0443 config.json. "
            "\u0422\u043e\u043a\u0435\u043d \u0441\u0442\u0432\u043e\u0440\u044e\u0454\u0442\u044c\u0441\u044f \u0447\u0435\u0440\u0435\u0437 @BotFather."
        )

    admin_chat_ids = raw.get("admin_chat_ids", [])
    admin_chat_ids_env = os.getenv("ADMIN_CHAT_IDS", "").strip()
    if admin_chat_ids_env:
        admin_chat_ids = [
            item.strip()
            for item in admin_chat_ids_env.split(",")
            if item.strip()
        ]

    alert_template = str(os.getenv("ALERT_TEMPLATE") or raw.get("alert_template", Config.alert_template))
    alert_template = alert_template.replace("\\n", "\n")
    if _looks_corrupt(alert_template):
        alert_template = Config.alert_template

    return Config(
        telegram_bot_token=token,
        database_path=_resolve(base, os.getenv("DATABASE_PATH") or raw.get("database_path", "data/media_monitor.sqlite3")),
        sources_path=_resolve(base, os.getenv("SOURCES_PATH") or raw.get("sources_path", "data/sources.csv")),
        mini_app_url=str(os.getenv("MINI_APP_URL") or raw.get("mini_app_url", "")).strip(),
        mini_app_host=str(os.getenv("MINI_APP_HOST") or raw.get("mini_app_host", "127.0.0.1")).strip(),
        mini_app_port=int(os.getenv("MINI_APP_PORT") or raw.get("mini_app_port", 8080)),
        mini_app_static_path=_resolve(base, os.getenv("MINI_APP_STATIC_PATH") or raw.get("mini_app_static_path", "mini_app")),
        poll_interval_seconds=int(os.getenv("POLL_INTERVAL_SECONDS") or raw.get("poll_interval_seconds", 7200)),
        source_timeout_seconds=int(os.getenv("SOURCE_TIMEOUT_SECONDS") or raw.get("source_timeout_seconds", 15)),
        user_daily_limit=int(os.getenv("USER_DAILY_LIMIT") or raw.get("user_daily_limit", 100)),
        admin_chat_ids=tuple(int(x) for x in admin_chat_ids),
        require_onboarding=_bool(os.getenv("REQUIRE_ONBOARDING") or raw.get("require_onboarding", False)),
        trial_plan_id=str(os.getenv("TRIAL_PLAN_ID") or raw.get("trial_plan_id", "")).strip().lower(),
        trial_days=int(os.getenv("TRIAL_DAYS") or raw.get("trial_days", 7)),
        alert_template=alert_template,
    )


def _resolve(base: Path, value: str) -> Path:
    path = Path(value)
    return path if path.is_absolute() else base / path


def _looks_corrupt(value: str) -> bool:
    return value.count("?") > 5 or "Рџ" in value or "Рќ" in value


def _bool(value: object) -> bool:
    if isinstance(value, bool):
        return value
    return str(value or "").strip().lower() in {"1", "true", "yes", "on", "так"}
