from __future__ import annotations

import json
import os
import re
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Any

from .billing import DEFAULT_CRYPTO_PRICES_USD


@dataclass(frozen=True)
class Source:
    name: str
    url: str
    type: str = "rss"
    rank: int | None = None
    subscribers: int | None = None
    country: str = "ua"
    language: str = ""


def clean_source_display_name(name: str) -> str:
    cleaned = re.sub(r"\s+via\s+Google\s+News\s*$", "", str(name or ""), flags=re.IGNORECASE).strip()
    return cleaned or str(name or "").strip()


@dataclass(frozen=True)
class Config:
    telegram_bot_token: str
    database_path: Path
    sources_path: Path
    mini_app_url: str = ""
    mini_app_host: str = "127.0.0.1"
    mini_app_port: int = 8080
    mini_app_static_path: Path = Path("mini_app")
    mini_app_menu_button: bool = False
    mini_app_menu_button_text: str = "Cabinet"
    poll_interval_seconds: int = 7200
    source_timeout_seconds: int = 15
    user_daily_limit: int = 100
    admin_chat_ids: tuple[int, ...] = ()
    require_onboarding: bool = False
    trial_plan_id: str = ""
    trial_days: int = 7
    nowpayments_api_key: str = ""
    nowpayments_ipn_secret: str = ""
    nowpayments_api_base: str = "https://api.nowpayments.io/v1"
    nowpayments_ipn_callback_url: str = ""
    crypto_price_currency: str = "usd"
    crypto_plan_prices_usd: dict[str, Decimal] | None = None
    crypto_success_url: str = ""
    crypto_cancel_url: str = ""
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
        mini_app_menu_button=_bool(os.getenv("MINI_APP_MENU_BUTTON") or raw.get("mini_app_menu_button", False)),
        mini_app_menu_button_text=str(os.getenv("MINI_APP_MENU_BUTTON_TEXT") or raw.get("mini_app_menu_button_text", "Cabinet")).strip(),
        poll_interval_seconds=int(os.getenv("POLL_INTERVAL_SECONDS") or raw.get("poll_interval_seconds", 7200)),
        source_timeout_seconds=int(os.getenv("SOURCE_TIMEOUT_SECONDS") or raw.get("source_timeout_seconds", 15)),
        user_daily_limit=int(os.getenv("USER_DAILY_LIMIT") or raw.get("user_daily_limit", 100)),
        admin_chat_ids=tuple(int(x) for x in admin_chat_ids),
        require_onboarding=_bool(os.getenv("REQUIRE_ONBOARDING") or raw.get("require_onboarding", False)),
        trial_plan_id=str(os.getenv("TRIAL_PLAN_ID") or raw.get("trial_plan_id", "")).strip().lower(),
        trial_days=int(os.getenv("TRIAL_DAYS") or raw.get("trial_days", 7)),
        nowpayments_api_key=str(os.getenv("NOWPAYMENTS_API_KEY") or raw.get("nowpayments_api_key", "")).strip(),
        nowpayments_ipn_secret=str(os.getenv("NOWPAYMENTS_IPN_SECRET") or raw.get("nowpayments_ipn_secret", "")).strip(),
        nowpayments_api_base=str(
            os.getenv("NOWPAYMENTS_API_BASE") or raw.get("nowpayments_api_base", "https://api.nowpayments.io/v1")
        ).strip().rstrip("/"),
        nowpayments_ipn_callback_url=str(
            os.getenv("NOWPAYMENTS_IPN_CALLBACK_URL") or raw.get("nowpayments_ipn_callback_url", "")
        ).strip(),
        crypto_price_currency=str(os.getenv("CRYPTO_PRICE_CURRENCY") or raw.get("crypto_price_currency", "usd")).strip().lower(),
        crypto_plan_prices_usd=_crypto_prices(raw.get("crypto_plan_prices_usd")),
        crypto_success_url=str(os.getenv("CRYPTO_SUCCESS_URL") or raw.get("crypto_success_url", "")).strip(),
        crypto_cancel_url=str(os.getenv("CRYPTO_CANCEL_URL") or raw.get("crypto_cancel_url", "")).strip(),
        alert_template=alert_template,
    )


def _resolve(base: Path, value: str) -> Path:
    path = Path(value)
    return path if path.is_absolute() else base / path


def _looks_corrupt(value: str) -> bool:
    return value.count("?") > 5 or "Рџ" in value or "Рќ" in value


def _crypto_prices(raw_value: object) -> dict[str, Decimal]:
    prices = dict(DEFAULT_CRYPTO_PRICES_USD)
    raw_env = os.getenv("CRYPTO_PLAN_PRICES_USD", "").strip()
    if raw_env:
        _merge_crypto_price_pairs(prices, raw_env)
    elif isinstance(raw_value, dict):
        for plan_id, value in raw_value.items():
            _set_crypto_price(prices, str(plan_id), value)
    return prices


def _merge_crypto_price_pairs(prices: dict[str, Decimal], raw_value: str) -> None:
    for item in raw_value.split(","):
        plan_id, separator, value = item.partition("=")
        if separator:
            _set_crypto_price(prices, plan_id, value)


def _set_crypto_price(prices: dict[str, Decimal], plan_id: str, value: object) -> None:
    key = plan_id.strip().lower()
    if key not in DEFAULT_CRYPTO_PRICES_USD:
        return
    try:
        amount = Decimal(str(value).strip())
    except (InvalidOperation, ValueError):
        return
    if amount > 0:
        prices[key] = amount.quantize(Decimal("0.01"))


def _bool(value: object) -> bool:
    if isinstance(value, bool):
        return value
    return str(value or "").strip().lower() in {"1", "true", "yes", "on", "так"}
