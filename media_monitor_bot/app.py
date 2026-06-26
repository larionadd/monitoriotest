from __future__ import annotations

import argparse
import csv
import json
import logging
import re
import shutil
import sys
import threading
import time
from pathlib import Path
from urllib.parse import parse_qs, urlparse

from .billing import PLANS, Plan, paid_plans, plan_by_id
from .config import Source, load_config
from .db import Database, normalize_url, source_allowed_for_plan
from .locales import (
    COUNTRIES,
    LANGUAGES,
    country_button_text,
    country_from_button,
    country_name,
    language_button_text,
    language_from_button,
    language_name,
    text as locale_text,
)
from .mini_app_server import start_static_server
from .monitor import Monitor, fetch_rss, fetch_telegram_channel, telegram_preview_url
from .reports import write_csv_report
from .sources import load_sources
from .telegram_api import TelegramApi, escape

BTN_ADD = "➕ Додати ключ"
BTN_REMOVE = "➖ Видалити ключ"
BTN_INFO = "📋 Мій моніторинг"
BTN_CHECK = "🔎 Перевірити зараз"
BTN_SOURCES = "📰 Джерела"
BTN_REPORT = "📄 Звіт"
BTN_FILTERS = "⚙️ Фільтри"
BTN_TEXT_MODE = "🧾 Режим тексту"
BTN_PLANS = "💳 Тарифи"
BTN_HELP = "ℹ️ Допомога"
BTN_APP = "\U0001f4f1 \u041a\u0430\u0431\u0456\u043d\u0435\u0442"
BTN_SOURCE_LIST = "📋 Список джерел"
BTN_TG_BLOCKS = "\U0001f4e6 TG-\u043f\u0430\u043a\u0435\u0442\u0438"
BTN_SOURCES_FILE = "\U0001f4ce \u0424\u0430\u0439\u043b \u0434\u0436\u0435\u0440\u0435\u043b"
BTN_SOURCE_ADD = "➕ Додати RSS"
BTN_TG_ADD = "➕ Додати TG"
BTN_SOURCE_DISABLE = "⛔ Вимкнути джерело"
BTN_SOURCE_ENABLE = "✅ Увімкнути джерело"
BTN_SOURCE_REMOVE = "🗑️ Видалити моє джерело"
BTN_FULL_TEXT_ON = "✅ Повний текст"
BTN_FULL_TEXT_OFF = "⚡ RSS-анонс"
BTN_STOP_ADD = "🚫 Додати стоп-слово"
BTN_STOP_REMOVE = "✅ Видалити стоп-слово"
BTN_PLUS_ADD = "➕ Додати плюс-слово"
BTN_PLUS_REMOVE = "➖ Видалити плюс-слово"
BTN_BACK = "⬅️ Головне меню"
BTN_LANGUAGE = "🌐 Мова"
BTN_COUNTRY = "🌍 Регіон"
BTN_SETTINGS = "⚙️ Налаштування"
BTN_MONITORING_MODE = "🔁 Режим моніторингу"
BTN_AUTO_MONITORING_ON = "✅ Автоматично"
BTN_AUTO_MONITORING_OFF = "✋ Ручний режим"

BUTTON_KEY_BY_DEFAULT_TEXT = {
    BTN_ADD: "add",
    BTN_REMOVE: "remove",
    BTN_INFO: "info",
    BTN_CHECK: "check",
    BTN_SOURCES: "sources",
    BTN_REPORT: "report",
    BTN_FILTERS: "filters",
    BTN_TEXT_MODE: "text_mode",
    BTN_PLANS: "plans",
    BTN_HELP: "help",
    BTN_APP: "app",
    BTN_SOURCE_LIST: "source_list",
    BTN_TG_BLOCKS: "tg_blocks",
    BTN_SOURCES_FILE: "sources_file",
    BTN_SOURCE_ADD: "source_add",
    BTN_TG_ADD: "tg_add",
    BTN_SOURCE_DISABLE: "source_disable",
    BTN_SOURCE_ENABLE: "source_enable",
    BTN_SOURCE_REMOVE: "source_remove",
    BTN_FULL_TEXT_ON: "full_text_on",
    BTN_FULL_TEXT_OFF: "full_text_off",
    BTN_STOP_ADD: "stop_add",
    BTN_STOP_REMOVE: "stop_remove",
    BTN_PLUS_ADD: "plus_add",
    BTN_PLUS_REMOVE: "plus_remove",
    BTN_BACK: "back",
    BTN_LANGUAGE: "language",
    BTN_COUNTRY: "country",
    BTN_SETTINGS: "settings",
    BTN_MONITORING_MODE: "monitoring_mode",
    BTN_AUTO_MONITORING_ON: "auto_monitoring_on",
    BTN_AUTO_MONITORING_OFF: "auto_monitoring_off",
}

BUTTON_KEYS = tuple(BUTTON_KEY_BY_DEFAULT_TEXT.values())
MAIN_MENU_ROWS = (
    ("info", "check"),
    ("sources", "report"),
    ("filters",),
    ("plans", "help"),
)
FILTER_MENU_ROWS = (
    ("add", "remove"),
    ("stop_add", "stop_remove"),
    ("plus_add", "plus_remove"),
    ("info", "back"),
)
TEXT_MODE_MENU_ROWS = (
    ("full_text_on", "full_text_off"),
    ("info", "back"),
)
SOURCE_MENU_ROWS = (
    ("source_list", "tg_blocks"),
    ("sources_file",),
    ("source_add", "tg_add"),
    ("source_disable", "source_enable"),
    ("source_remove", "back"),
)
SETTINGS_MENU_ROWS = (
    ("language", "country"),
    ("text_mode", "monitoring_mode"),
    ("info", "back"),
)
MONITORING_MODE_MENU_ROWS = (
    ("auto_monitoring_on", "auto_monitoring_off"),
    ("info", "back"),
)

MINI_APP_URL = ""
REQUIRE_ONBOARDING = False
TRIAL_PLAN_ID = ""
TRIAL_DAYS = 7


def main_menu_for_chat(chat_id: int, db: Database) -> dict:
    language_code = db.get_user_settings(chat_id).language_code
    keyboard = menu_keyboard(language_code, MAIN_MENU_ROWS)
    if MINI_APP_URL:
        keyboard.insert(0, [{"text": button_label(language_code, "app"), "web_app": {"url": MINI_APP_URL}}])
    if REQUIRE_ONBOARDING:
        keyboard.insert(-1, [{"text": button_label(language_code, "settings")}])
    return menu_markup(keyboard)


def filter_menu_for_chat(chat_id: int, db: Database) -> dict:
    return menu_markup(menu_keyboard(db.get_user_settings(chat_id).language_code, FILTER_MENU_ROWS))


def text_mode_menu_for_chat(chat_id: int, db: Database) -> dict:
    return menu_markup(menu_keyboard(db.get_user_settings(chat_id).language_code, TEXT_MODE_MENU_ROWS))


def source_menu_for_chat(chat_id: int, db: Database) -> dict:
    return menu_markup(menu_keyboard(db.get_user_settings(chat_id).language_code, SOURCE_MENU_ROWS))


def settings_menu_for_chat(chat_id: int, db: Database) -> dict:
    return menu_markup(menu_keyboard(db.get_user_settings(chat_id).language_code, SETTINGS_MENU_ROWS))


def monitoring_mode_menu_for_chat(chat_id: int, db: Database) -> dict:
    return menu_markup(menu_keyboard(db.get_user_settings(chat_id).language_code, MONITORING_MODE_MENU_ROWS))


def menu_keyboard(language_code: str, rows: tuple[tuple[str, ...], ...]) -> list[list[dict]]:
    return [[{"text": button_label(language_code, key)} for key in row] for row in rows]


def menu_markup(keyboard: list[list[dict]]) -> dict:
    return {
        "keyboard": keyboard,
        "resize_keyboard": True,
        "is_persistent": True,
    }


def button_label(language_code: str, key: str) -> str:
    return locale_text(language_code, f"button_{key}")


def button_action(value: str) -> str | None:
    needle = (value or "").strip().lower()
    if not needle:
        return None
    default_action = BUTTON_KEY_BY_DEFAULT_TEXT.get(value.strip())
    if default_action:
        return default_action
    for language_code in LANGUAGES:
        for key in BUTTON_KEYS:
            if needle == button_label(language_code, key).lower():
                return key
    return None

PENDING_ACTIONS: dict[int, str] = {}
MONITOR_LOCK = threading.Lock()
ADMIN_CHAT_IDS: set[int] = set()
PLAN_MONITOR_INTERVAL_SECONDS = {
    "free": 3600,
    "basic": 1800,
    "pro": 1800,
    "business": 300,
}
MONITOR_IDLE_SECONDS = 10
MANUAL_CHECK_WAIT_SECONDS = 60
TG_BLOCK_SIZE = 50


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Telegram-бот для медіамоніторингу")
    parser.add_argument("--config", default="config.json", help="Шлях до config.json")
    parser.add_argument("--once", action="store_true", help="Виконати одну перевірку і завершити роботу")
    parser.add_argument("--no-bot", action="store_true", help="Не приймати Telegram-команди")
    args = parser.parse_args(argv)

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
        handlers=[logging.StreamHandler(sys.stdout)],
    )

    config_path = Path(args.config)
    if not config_path.exists():
        example = config_path.with_name("config.example.json")
        if example.exists():
            shutil.copyfile(example, config_path)
        print(f"Створено {config_path}. Додайте Telegram-токен і запустіть ще раз.")
        return 2

    config = load_config(config_path)
    global REQUIRE_ONBOARDING, TRIAL_PLAN_ID, TRIAL_DAYS
    REQUIRE_ONBOARDING = config.require_onboarding
    TRIAL_PLAN_ID = config.trial_plan_id
    TRIAL_DAYS = config.trial_days
    ADMIN_CHAT_IDS.clear()
    ADMIN_CHAT_IDS.update(config.admin_chat_ids)
    db = Database(config.database_path)
    db.migrate()
    telegram = TelegramApi(config.telegram_bot_token)
    sources = load_sources(config.sources_path)
    configure_mini_app(config, telegram, db, sources)
    configure_bot_commands(telegram)
    monitor = Monitor(config, db, telegram, sources)

    if args.once:
        sent = monitor.run_once()
        print(f"Перевірку завершено. Надіслано сповіщень: {sent}")
        return 0

    if args.no_bot:
        run_monitor_loop(monitor)

    run_bot_loop(db, telegram, monitor, sources, config.poll_interval_seconds)
    return 0


def run_bot_loop(
    db: Database,
    telegram: TelegramApi,
    monitor: Monitor,
    sources,
    poll_interval_seconds: int,
) -> None:
    offset: int | None = None
    logging.info(
        "Бот запущений. Автоматичний моніторинг: Free 3600 с, Basic/Pro 1800 с, Business 300 с"
    )
    threading.Thread(
        target=run_monitor_loop,
        args=(monitor,),
        daemon=True,
        name="media-monitor-loop",
    ).start()

    while True:
        try:
            updates = telegram.get_updates(offset=offset, timeout=20)
        except Exception:
            logging.exception("Не вдалося отримати оновлення Telegram")
            time.sleep(5)
            continue

        for update in updates:
            offset = int(update["update_id"]) + 1
            if "pre_checkout_query" in update:
                handle_pre_checkout_query(update["pre_checkout_query"], telegram)
                continue
            message = update.get("message") or {}
            text = (message.get("text") or "").strip()
            chat = message.get("chat") or {}
            chat_id = chat.get("id")
            if chat_id is None:
                continue
            if message.get("successful_payment"):
                handle_successful_payment(int(chat_id), message["successful_payment"], db, telegram)
                continue
            if message.get("web_app_data"):
                try:
                    handle_web_app_data(int(chat_id), message["web_app_data"], db, telegram, monitor, sources)
                except Exception:
                    logging.exception("Не вдалося обробити Mini App дію від %s", chat_id)
                    language_code = db.get_user_settings(int(chat_id)).language_code
                    telegram.send_message(
                        int(chat_id),
                        locale_text(language_code, "mini_app_action_failed"),
                        reply_markup=main_menu_for_chat(chat_id, db),
                    )
                continue
            if not text:
                continue
            try:
                handle_message(int(chat_id), text, db, telegram, monitor, sources)
            except Exception:
                logging.exception("Не вдалося обробити повідомлення від %s", chat_id)
                language_code = db.get_user_settings(int(chat_id)).language_code
                telegram.send_message(
                    int(chat_id),
                    locale_text(language_code, "message_failed"),
                    reply_markup=main_menu_for_chat(chat_id, db),
                )


def run_monitor_loop(monitor: Monitor) -> None:
    last_checked_at: dict[int, float] = {}
    while True:
        due_chat_ids, has_business = due_monitoring_chat_ids(monitor, last_checked_at)
        if not due_chat_ids:
            time.sleep(MONITOR_IDLE_SECONDS)
            continue
        sent = run_monitor_safely(monitor, due_chat_ids)
        if sent is None:
            time.sleep(MONITOR_IDLE_SECONDS)
            continue
        if sent is not None:
            checked_at = time.time()
            for chat_id in due_chat_ids:
                last_checked_at[chat_id] = checked_at
            logging.info(
                "Автоматичну перевірку завершено. Користувачів: %s. Надіслано сповіщень: %s",
                len(due_chat_ids),
                sent,
            )
        time.sleep(MONITOR_IDLE_SECONDS)


def due_monitoring_chat_ids(monitor: Monitor, last_checked_at: dict[int, float]) -> tuple[set[int], bool]:
    now = time.time()
    due_chat_ids: set[int] = set()
    has_business = False
    for user in monitor.db.iter_monitoring_users():
        if not user.auto_monitoring_enabled:
            continue
        plan = monitor.db.get_active_plan(user.chat_id)
        interval = PLAN_MONITOR_INTERVAL_SECONDS.get(plan.id, 3600)
        if plan.id == "business":
            has_business = True
        last_checked = last_checked_at.get(user.chat_id)
        if last_checked is None or interval <= 0 or now - last_checked >= interval:
            due_chat_ids.add(user.chat_id)
    return due_chat_ids, has_business


def run_monitor_safely(
    monitor: Monitor,
    chat_ids: set[int] | None = None,
    wait_seconds: int = 0,
) -> int | None:
    if not MONITOR_LOCK.acquire(timeout=wait_seconds):
        return None
    try:
        return monitor.run_once(chat_ids)
    finally:
        MONITOR_LOCK.release()


def configure_mini_app(config, telegram: TelegramApi, db: Database, sources) -> None:
    global MINI_APP_URL
    MINI_APP_URL = config.mini_app_url
    if not config.mini_app_url:
        return
    try:
        telegram.set_chat_menu_button("Monitorio", config.mini_app_url)
    except Exception:
        logging.exception("Не вдалося скинути глобальну Telegram menu button для Mini App")
    try:
        start_static_server(
            config.mini_app_host,
            config.mini_app_port,
            config.mini_app_static_path,
            bot_token=config.telegram_bot_token,
            db=db,
            sources=sources,
            require_business=False,
        )
    except Exception:
        logging.exception("Не вдалося запустити Mini App server")


def configure_bot_commands(telegram: TelegramApi) -> None:
    commands = [
        {"command": "start", "description": "Start the bot and show the menu"},
        {"command": "add", "description": "Add a keyword"},
        {"command": "remove", "description": "Remove a keyword"},
        {"command": "plans", "description": "Show plans"},
        {"command": "buy", "description": "Buy a plan"},
        {"command": "fulltext", "description": "Manage full-text search"},
        {"command": "monitoring", "description": "Manual or automatic monitoring"},
        {"command": "rss", "description": "Manage sources"},
        {"command": "tg", "description": "Add a Telegram channel"},
        {"command": "tgblocks", "description": "Manage TG packages"},
        {"command": "info", "description": "Show my monitoring"},
        {"command": "sources", "description": "Show sources"},
        {"command": "sourcesfile", "description": "Receive the source file"},
        {"command": "check", "description": "Check now"},
        {"command": "report", "description": "Receive CSV report"},
        {"command": "help", "description": "Help"},
    ]
    if REQUIRE_ONBOARDING:
        commands[9:9] = [
            {"command": "settings", "description": "Language, region, and text mode"},
            {"command": "language", "description": "Change interface language"},
            {"command": "country", "description": "Change monitoring region"},
        ]
    telegram.set_my_commands(commands)


def handle_web_app_data(
    chat_id: int,
    web_app_data: dict,
    db: Database,
    telegram: TelegramApi,
    monitor: Monitor,
    sources,
) -> None:
    db.touch_user(chat_id)
    language_code = db.get_user_settings(chat_id).language_code
    try:
        payload = json.loads(web_app_data.get("data") or "{}")
    except json.JSONDecodeError:
        telegram.send_message(chat_id, locale_text(language_code, "mini_app_bad_data"), reply_markup=main_menu_for_chat(chat_id, db))
        return
    action = str(payload.get("action") or "").strip()
    value = str(payload.get("value") or "").strip()

    if action == "set_country":
        country_code = str(payload.get("country") or value).strip()
        handle_country_choice(chat_id, country_code, db, telegram)
        return

    if action == "set_language":
        language = str(payload.get("language") or value).strip()
        handle_language_choice(chat_id, language, db, telegram)
        return

    if action == "add_keyword":
        if not value:
            telegram.send_message(chat_id, locale_text(language_code, "prompt_add_keyword"), reply_markup=main_menu_for_chat(chat_id, db))
            return
        if not can_add_keyword(chat_id, db, telegram):
            return
        added = db.add_keyword(chat_id, value)
        telegram.send_message(
            chat_id,
            format_add_result(language_code, locale_text(language_code, "keyword_label"), value, added),
            reply_markup=main_menu_for_chat(chat_id, db),
        )
        return

    if action == "remove_keyword":
        if not value:
            telegram.send_message(chat_id, locale_text(language_code, "prompt_remove_keyword"), reply_markup=main_menu_for_chat(chat_id, db))
            return
        removed = db.remove_keyword(chat_id, value)
        telegram.send_message(
            chat_id,
            format_remove_result(language_code, locale_text(language_code, "keyword_label"), value, removed),
            reply_markup=main_menu_for_chat(chat_id, db),
        )
        return

    if action == "add_stop_word":
        added = db.add_stop_word(chat_id, value)
        telegram.send_message(
            chat_id,
            format_add_result(language_code, locale_text(language_code, "stop_word_label"), value, added),
            reply_markup=filter_menu_for_chat(chat_id, db),
        )
        return

    if action == "remove_stop_word":
        removed = db.remove_stop_word(chat_id, value)
        telegram.send_message(
            chat_id,
            format_remove_result(language_code, locale_text(language_code, "stop_word_label"), value, removed),
            reply_markup=filter_menu_for_chat(chat_id, db),
        )
        return

    if action == "add_plus_word":
        added = db.add_plus_word(chat_id, value)
        telegram.send_message(
            chat_id,
            format_add_result(language_code, locale_text(language_code, "plus_word_label"), value, added),
            reply_markup=filter_menu_for_chat(chat_id, db),
        )
        return

    if action == "remove_plus_word":
        removed = db.remove_plus_word(chat_id, value)
        telegram.send_message(
            chat_id,
            format_remove_result(language_code, locale_text(language_code, "plus_word_label"), value, removed),
            reply_markup=filter_menu_for_chat(chat_id, db),
        )
        return

    if action == "fulltext":
        enabled = bool(payload.get("enabled"))
        plan = db.get_active_plan(chat_id)
        if enabled and not plan.full_text:
            telegram.send_message(chat_id, locale_text(language_code, "fulltext_unavailable"), reply_markup=main_menu_for_chat(chat_id, db))
            return
        db.set_full_text_enabled(chat_id, enabled)
        status = locale_text(language_code, "status_enabled" if enabled else "status_disabled")
        telegram.send_message(chat_id, locale_text(language_code, "fulltext_status", status=status), reply_markup=main_menu_for_chat(chat_id, db))
        return

    if action == "auto_monitoring":
        enabled = bool(payload.get("enabled"))
        db.set_auto_monitoring_enabled(chat_id, enabled)
        telegram.send_message(
            chat_id,
            locale_text(language_code, "auto_monitoring_enabled" if enabled else "manual_monitoring_enabled"),
            reply_markup=main_menu_for_chat(chat_id, db),
        )
        return

    if action == "tg_block":
        block_number = parse_block_number(str(payload.get("block") or ""))
        enabled = bool(payload.get("enabled"))
        set_tg_block(chat_id, block_number, enabled, db, telegram, sources)
        return

    if action == "add_rss":
        add_custom_rss(chat_id, value, db, telegram)
        return

    if action == "add_tg":
        add_custom_telegram(chat_id, value, db, telegram)
        return

    if action == "sources_file":
        send_sources_file(chat_id, db, telegram, sources)
        return

    if action == "check":
        run_manual_check(chat_id, db, telegram, monitor)
        return

    if action == "plans":
        send_plans(chat_id, db, telegram)
        return

    if action == "report":
        send_report(chat_id, db, telegram)
        return

    telegram.send_message(chat_id, locale_text(language_code, "mini_app_unknown_action"), reply_markup=main_menu_for_chat(chat_id, db))


def handle_message(chat_id: int, text: str, db: Database, telegram: TelegramApi, monitor: Monitor, sources) -> None:
    db.touch_user(chat_id, onboarding_completed_default=not REQUIRE_ONBOARDING)

    pending = PENDING_ACTIONS.get(chat_id)
    if pending in {"set_language", "set_country"} and text and not text.startswith("/"):
        PENDING_ACTIONS.pop(chat_id, None)
        if pending == "set_language":
            handle_language_choice(chat_id, text, db, telegram)
        else:
            handle_country_choice(chat_id, text, db, telegram)
        return

    settings = db.get_user_settings(chat_id)
    if REQUIRE_ONBOARDING and not settings.onboarding_completed and not text.startswith(("/start", "/language", "/country")):
        send_language_choice(chat_id, db, telegram)
        return

    action = button_action(text)

    if action == "plans":
        send_plans(chat_id, db, telegram)
        return

    if text.startswith("/"):
        handle_command(chat_id, text, db, telegram, monitor, sources)
        return

    if text:
        message_payment = None

    if action == "add":
        PENDING_ACTIONS[chat_id] = "add_keyword"
        telegram.send_message(chat_id, locale_text(settings.language_code, "prompt_add_keyword"), reply_markup=filter_menu_for_chat(chat_id, db))
        return

    if action == "remove":
        PENDING_ACTIONS[chat_id] = "remove_keyword"
        telegram.send_message(chat_id, locale_text(settings.language_code, "prompt_remove_keyword"), reply_markup=filter_menu_for_chat(chat_id, db))
        return

    if action == "info":
        send_info(chat_id, db, telegram, sources)
        return

    if action == "check":
        run_manual_check(chat_id, db, telegram, monitor)
        return

    if action == "sources":
        send_sources(chat_id, db, telegram, sources)
        return

    if action == "source_list":
        send_sources(chat_id, db, telegram, sources)
        return

    if action == "sources_file":
        send_sources_file(chat_id, db, telegram, sources)
        return

    if action == "tg_blocks":
        send_tg_blocks(chat_id, db, telegram, sources)
        return

    block_action = parse_tg_block_button(text)
    if block_action:
        action, block_number = block_action
        set_tg_block(chat_id, block_number, action == "on", db, telegram, sources)
        return

    if action == "source_add":
        PENDING_ACTIONS[chat_id] = "add_rss"
        telegram.send_message(
            chat_id,
            locale_text(settings.language_code, "prompt_add_rss"),
            reply_markup=source_menu_for_chat(chat_id, db),
        )
        return

    if action == "tg_add":
        PENDING_ACTIONS[chat_id] = "add_tg"
        telegram.send_message(
            chat_id,
            locale_text(settings.language_code, "prompt_add_tg"),
            reply_markup=source_menu_for_chat(chat_id, db),
        )
        return

    if action == "source_disable":
        PENDING_ACTIONS[chat_id] = "disable_rss"
        telegram.send_message(
            chat_id,
            locale_text(settings.language_code, "prompt_disable_source") + "\n\n"
            + format_sources(chat_id, db, sources),
            reply_markup=source_menu_for_chat(chat_id, db),
        )
        return

    if action == "source_enable":
        PENDING_ACTIONS[chat_id] = "enable_rss"
        telegram.send_message(
            chat_id,
            locale_text(settings.language_code, "prompt_enable_source") + "\n\n"
            + format_sources(chat_id, db, sources),
            reply_markup=source_menu_for_chat(chat_id, db),
        )
        return

    if action == "source_remove":
        PENDING_ACTIONS[chat_id] = "remove_rss"
        telegram.send_message(
            chat_id,
            locale_text(settings.language_code, "prompt_remove_source") + "\n\n"
            + format_sources(chat_id, db, sources),
            reply_markup=source_menu_for_chat(chat_id, db),
        )
        return

    if action == "report":
        send_report(chat_id, db, telegram)
        return

    if action == "filters":
        telegram.send_message(chat_id, locale_text(settings.language_code, "filters_title"), reply_markup=filter_menu_for_chat(chat_id, db))
        return

    if action == "text_mode":
        send_text_mode(chat_id, db, telegram)
        return

    if action == "monitoring_mode":
        send_monitoring_mode(chat_id, db, telegram)
        return

    if action == "settings":
        send_settings(chat_id, db, telegram)
        return

    if action == "full_text_on":
        plan = db.get_active_plan(chat_id)
        if not plan.full_text:
            telegram.send_message(
                chat_id,
                locale_text(settings.language_code, "fulltext_unavailable"),
                reply_markup=main_menu_for_chat(chat_id, db),
            )
            return
        db.set_full_text_enabled(chat_id, True)
        telegram.send_message(
            chat_id,
            locale_text(settings.language_code, "fulltext_enabled"),
            reply_markup=text_mode_menu_for_chat(chat_id, db),
        )
        return

    if action == "full_text_off":
        db.set_full_text_enabled(chat_id, False)
        telegram.send_message(
            chat_id,
            locale_text(settings.language_code, "fast_mode_enabled"),
            reply_markup=text_mode_menu_for_chat(chat_id, db),
        )
        return

    if action == "auto_monitoring_on":
        db.set_auto_monitoring_enabled(chat_id, True)
        telegram.send_message(
            chat_id,
            locale_text(settings.language_code, "auto_monitoring_enabled"),
            reply_markup=monitoring_mode_menu_for_chat(chat_id, db),
        )
        return

    if action == "auto_monitoring_off":
        db.set_auto_monitoring_enabled(chat_id, False)
        telegram.send_message(
            chat_id,
            locale_text(settings.language_code, "manual_monitoring_enabled"),
            reply_markup=monitoring_mode_menu_for_chat(chat_id, db),
        )
        return

    if action == "help":
        send_help(chat_id, db, telegram)
        return

    if action == "language":
        send_language_choice(chat_id, db, telegram)
        return

    if action == "country":
        send_country_choice(chat_id, db, telegram)
        return

    if action == "back":
        telegram.send_message(chat_id, locale_text(settings.language_code, "main_menu_title"), reply_markup=main_menu_for_chat(chat_id, db))
        return

    if action == "stop_add":
        PENDING_ACTIONS[chat_id] = "add_stop_word"
        telegram.send_message(chat_id, locale_text(settings.language_code, "prompt_add_stop_word"), reply_markup=filter_menu_for_chat(chat_id, db))
        return

    if action == "stop_remove":
        PENDING_ACTIONS[chat_id] = "remove_stop_word"
        telegram.send_message(chat_id, locale_text(settings.language_code, "prompt_remove_stop_word"), reply_markup=filter_menu_for_chat(chat_id, db))
        return

    if action == "plus_add":
        PENDING_ACTIONS[chat_id] = "add_plus_word"
        telegram.send_message(chat_id, locale_text(settings.language_code, "prompt_add_plus_word"), reply_markup=filter_menu_for_chat(chat_id, db))
        return

    if action == "plus_remove":
        PENDING_ACTIONS[chat_id] = "remove_plus_word"
        telegram.send_message(chat_id, locale_text(settings.language_code, "prompt_remove_plus_word"), reply_markup=filter_menu_for_chat(chat_id, db))
        return

    pending = PENDING_ACTIONS.pop(chat_id, None)
    if pending:
        handle_pending_value(chat_id, pending, text, db, telegram, sources)
        return

    telegram.send_message(
        chat_id,
        locale_text(settings.language_code, "choose_menu_action"),
        reply_markup=main_menu_for_chat(chat_id, db),
    )


def handle_command(chat_id: int, text: str, db: Database, telegram: TelegramApi, monitor: Monitor, sources) -> None:
    command, argument = split_command(text)
    language_code = db.get_user_settings(chat_id).language_code

    if command in {"/start", "/help", "/menu"}:
        if command == "/start" and REQUIRE_ONBOARDING and not db.get_user_settings(chat_id).onboarding_completed:
            send_language_choice(chat_id, db, telegram)
            return
        send_help(chat_id, db, telegram)
        return

    if command == "/language":
        if argument:
            handle_language_choice(chat_id, argument, db, telegram)
        else:
            send_language_choice(chat_id, db, telegram)
        return

    if command == "/country":
        if argument:
            handle_country_choice(chat_id, argument, db, telegram)
        else:
            send_country_choice(chat_id, db, telegram)
        return

    if command == "/settings":
        send_settings(chat_id, db, telegram)
        return

    if command == "/plans":
        send_plans(chat_id, db, telegram)
        return

    if command == "/buy":
        send_plan_invoice(chat_id, argument, db, telegram)
        return

    if command == "/grant":
        handle_grant_command(chat_id, argument, db, telegram)
        return

    if command == "/users":
        send_users(chat_id, db, telegram)
        return

    if command == "/add":
        if not argument:
            PENDING_ACTIONS[chat_id] = "add_keyword"
            telegram.send_message(chat_id, locale_text(language_code, "prompt_add_keyword"), reply_markup=main_menu_for_chat(chat_id, db))
            return
        if not can_add_keyword(chat_id, db, telegram):
            return
        added = db.add_keyword(chat_id, argument)
        telegram.send_message(
            chat_id,
            format_add_result(language_code, locale_text(language_code, "keyword_label"), argument, added),
            reply_markup=main_menu_for_chat(chat_id, db),
        )
        return

    if command == "/remove":
        if not argument:
            PENDING_ACTIONS[chat_id] = "remove_keyword"
            telegram.send_message(chat_id, locale_text(language_code, "prompt_remove_keyword"), reply_markup=main_menu_for_chat(chat_id, db))
            return
        removed = db.remove_keyword(chat_id, argument)
        telegram.send_message(
            chat_id,
            format_remove_result(language_code, locale_text(language_code, "keyword_label"), argument, removed),
            reply_markup=main_menu_for_chat(chat_id, db),
        )
        return

    if command == "/fulltext":
        handle_full_text_command(chat_id, argument, db, telegram)
        return

    if command == "/monitoring":
        handle_monitoring_mode_command(chat_id, argument, db, telegram)
        return

    if command == "/rss":
        handle_rss_command(chat_id, argument, db, telegram, sources)
        return

    if command == "/tg":
        handle_tg_command(chat_id, argument, db, telegram, sources)
        return

    if command == "/tgblocks":
        handle_tg_blocks_command(chat_id, argument, db, telegram, sources)
        return

    if command == "/addstopword":
        if not argument:
            PENDING_ACTIONS[chat_id] = "add_stop_word"
            telegram.send_message(chat_id, locale_text(language_code, "prompt_add_stop_word"), reply_markup=filter_menu_for_chat(chat_id, db))
            return
        added = db.add_stop_word(chat_id, argument)
        telegram.send_message(
            chat_id,
            format_add_result(language_code, locale_text(language_code, "stop_word_label"), argument, added),
            reply_markup=filter_menu_for_chat(chat_id, db),
        )
        return

    if command == "/removestopword":
        if not argument:
            PENDING_ACTIONS[chat_id] = "remove_stop_word"
            telegram.send_message(chat_id, locale_text(language_code, "prompt_remove_stop_word"), reply_markup=filter_menu_for_chat(chat_id, db))
            return
        removed = db.remove_stop_word(chat_id, argument)
        telegram.send_message(
            chat_id,
            format_remove_result(language_code, locale_text(language_code, "stop_word_label"), argument, removed),
            reply_markup=filter_menu_for_chat(chat_id, db),
        )
        return

    if command == "/addplusword":
        if not argument:
            PENDING_ACTIONS[chat_id] = "add_plus_word"
            telegram.send_message(chat_id, locale_text(language_code, "prompt_add_plus_word"), reply_markup=filter_menu_for_chat(chat_id, db))
            return
        added = db.add_plus_word(chat_id, argument)
        telegram.send_message(
            chat_id,
            format_add_result(language_code, locale_text(language_code, "plus_word_label"), argument, added),
            reply_markup=filter_menu_for_chat(chat_id, db),
        )
        return

    if command == "/removeplusword":
        if not argument:
            PENDING_ACTIONS[chat_id] = "remove_plus_word"
            telegram.send_message(chat_id, locale_text(language_code, "prompt_remove_plus_word"), reply_markup=filter_menu_for_chat(chat_id, db))
            return
        removed = db.remove_plus_word(chat_id, argument)
        telegram.send_message(
            chat_id,
            format_remove_result(language_code, locale_text(language_code, "plus_word_label"), argument, removed),
            reply_markup=filter_menu_for_chat(chat_id, db),
        )
        return

    if command in {"/info", "/list"}:
        send_info(chat_id, db, telegram, sources)
        return

    if command == "/sources":
        send_sources(chat_id, db, telegram, sources)
        return

    if command == "/sourcesfile":
        send_sources_file(chat_id, db, telegram, sources)
        return

    if command == "/check":
        run_manual_check(chat_id, db, telegram, monitor)
        return

    if command == "/report":
        send_report(chat_id, db, telegram)
        return

    telegram.send_message(chat_id, locale_text(language_code, "choose_menu_action"), reply_markup=main_menu_for_chat(chat_id, db))


def handle_pending_value(
    chat_id: int,
    action: str,
    value: str,
    db: Database,
    telegram: TelegramApi,
    sources,
) -> None:
    language_code = db.get_user_settings(chat_id).language_code
    if action == "add_keyword":
        if not can_add_keyword(chat_id, db, telegram):
            return
        added = db.add_keyword(chat_id, value)
        telegram.send_message(
            chat_id,
            format_add_result(language_code, locale_text(language_code, "keyword_label"), value, added),
            reply_markup=filter_menu_for_chat(chat_id, db),
        )
        return

    if action == "remove_keyword":
        removed = db.remove_keyword(chat_id, value)
        telegram.send_message(
            chat_id,
            format_remove_result(language_code, locale_text(language_code, "keyword_label"), value, removed),
            reply_markup=filter_menu_for_chat(chat_id, db),
        )
        return

    if action == "add_stop_word":
        added = db.add_stop_word(chat_id, value)
        telegram.send_message(
            chat_id,
            format_add_result(language_code, locale_text(language_code, "stop_word_label"), value, added),
            reply_markup=filter_menu_for_chat(chat_id, db),
        )
        return

    if action == "remove_stop_word":
        removed = db.remove_stop_word(chat_id, value)
        telegram.send_message(
            chat_id,
            format_remove_result(language_code, locale_text(language_code, "stop_word_label"), value, removed),
            reply_markup=filter_menu_for_chat(chat_id, db),
        )
        return

    if action == "add_plus_word":
        added = db.add_plus_word(chat_id, value)
        telegram.send_message(
            chat_id,
            format_add_result(language_code, locale_text(language_code, "plus_word_label"), value, added),
            reply_markup=filter_menu_for_chat(chat_id, db),
        )
        return

    if action == "remove_plus_word":
        removed = db.remove_plus_word(chat_id, value)
        telegram.send_message(
            chat_id,
            format_remove_result(language_code, locale_text(language_code, "plus_word_label"), value, removed),
            reply_markup=filter_menu_for_chat(chat_id, db),
        )
        return

    if action == "add_rss":
        add_custom_rss(chat_id, value, db, telegram)
        return

    if action == "add_tg":
        add_custom_telegram(chat_id, value, db, telegram)
        return

    if action == "disable_rss":
        disable_rss_by_number(chat_id, value, db, telegram, sources)
        return

    if action == "enable_rss":
        enable_rss_by_number(chat_id, value, db, telegram, sources)
        return

    if action == "remove_rss":
        remove_custom_rss_by_number(chat_id, value, db, telegram, sources)


def language_menu() -> dict:
    return {
        "keyboard": [[{"text": language_button_text(language.code)}] for language in LANGUAGES.values()],
        "resize_keyboard": True,
        "is_persistent": True,
    }


def country_menu(language_code: str) -> dict:
    return {
        "keyboard": [
            [{"text": country_button_text(country.code, language_code)}]
            for country in COUNTRIES.values()
        ],
        "resize_keyboard": True,
        "is_persistent": True,
    }


def send_language_choice(chat_id: int, db: Database, telegram: TelegramApi) -> None:
    settings = db.get_user_settings(chat_id)
    PENDING_ACTIONS[chat_id] = "set_language"
    message = locale_text(settings.language_code, "choose_language")
    if REQUIRE_ONBOARDING and not settings.onboarding_completed:
        message = locale_text(settings.language_code, "welcome")
    telegram.send_message(
        chat_id,
        message,
        reply_markup=language_menu(),
    )


def send_country_choice(chat_id: int, db: Database, telegram: TelegramApi) -> None:
    settings = db.get_user_settings(chat_id)
    PENDING_ACTIONS[chat_id] = "set_country"
    telegram.send_message(
        chat_id,
        locale_text(settings.language_code, "choose_country"),
        reply_markup=country_menu(settings.language_code),
    )


def send_settings(chat_id: int, db: Database, telegram: TelegramApi) -> None:
    settings = db.get_user_settings(chat_id)
    monitoring = db.get_user_monitoring(chat_id)
    text_mode = locale_text(
        settings.language_code,
        "text_mode_full" if monitoring.full_text_enabled else "text_mode_fast",
    )
    monitoring_mode = auto_monitoring_text(settings.language_code, monitoring.auto_monitoring_enabled)
    telegram.send_message(
        chat_id,
        (
            f"{locale_text(settings.language_code, 'settings')}:\n\n"
            f"{locale_text(settings.language_code, 'language')}: {escape(language_name(settings.language_code))}\n"
            f"{locale_text(settings.language_code, 'country')}: "
            f"{escape(country_name(settings.country_code, settings.language_code))}\n"
            f"{locale_text(settings.language_code, 'text_mode_label')}: {escape(text_mode)}\n"
            f"{locale_text(settings.language_code, 'monitoring_mode_label')}: {escape(monitoring_mode)}\n\n"
            f"{locale_text(settings.language_code, 'change_language')}: {button_label(settings.language_code, 'language')}\n"
            f"{locale_text(settings.language_code, 'change_country')}: {button_label(settings.language_code, 'country')}\n"
            f"{locale_text(settings.language_code, 'change_text_mode')}: {button_label(settings.language_code, 'text_mode')}\n"
            f"{locale_text(settings.language_code, 'change_monitoring_mode')}: {button_label(settings.language_code, 'monitoring_mode')}"
        ),
        reply_markup=settings_menu_for_chat(chat_id, db),
    )


def handle_language_choice(chat_id: int, value: str, db: Database, telegram: TelegramApi) -> None:
    language_code = language_from_button(value)
    settings = db.get_user_settings(chat_id)
    if language_code is None:
        telegram.send_message(chat_id, locale_text(settings.language_code, "unknown_language"), reply_markup=language_menu())
        PENDING_ACTIONS[chat_id] = "set_language"
        return
    db.set_language(chat_id, language_code)
    telegram.send_message(
        chat_id,
        locale_text(language_code, "language_saved", language=language_name(language_code)),
        reply_markup=settings_menu_for_chat(chat_id, db) if db.get_user_settings(chat_id).onboarding_completed else main_menu_for_chat(chat_id, db),
    )
    if REQUIRE_ONBOARDING and not db.get_user_settings(chat_id).onboarding_completed:
        send_country_choice(chat_id, db, telegram)


def handle_country_choice(chat_id: int, value: str, db: Database, telegram: TelegramApi) -> None:
    country_code = country_from_button(value) or value.strip().lower()
    settings = db.get_user_settings(chat_id)
    if country_code not in COUNTRIES:
        telegram.send_message(chat_id, locale_text(settings.language_code, "unknown_country"), reply_markup=country_menu(settings.language_code))
        PENDING_ACTIONS[chat_id] = "set_country"
        return
    was_completed = settings.onboarding_completed
    db.set_country(chat_id, country_code)
    db.set_onboarding_completed(chat_id, True)
    updated = db.get_user_settings(chat_id)
    lines = [
        locale_text(
            updated.language_code,
            "country_saved",
            country=country_name(updated.country_code, updated.language_code),
        ),
    ]
    if not was_completed:
        lines.append(locale_text(updated.language_code, "onboarding_done"))
        trial_message = activate_trial_if_needed(chat_id, db)
        if trial_message:
            lines.append(trial_message)
    telegram.send_message(
        chat_id,
        "\n\n".join(lines),
        reply_markup=settings_menu_for_chat(chat_id, db) if was_completed else main_menu_for_chat(chat_id, db),
    )


def activate_trial_if_needed(chat_id: int, db: Database) -> str:
    if not TRIAL_PLAN_ID or TRIAL_DAYS <= 0 or db.get_subscription(chat_id):
        return ""
    plan = plan_by_id(TRIAL_PLAN_ID)
    if plan.id == "free":
        return ""
    expires = db.activate_plan(chat_id, plan.id, TRIAL_DAYS)
    settings = db.get_user_settings(chat_id)
    return locale_text(settings.language_code, "trial_started", days=TRIAL_DAYS, plan=f"{plan.name} ({expires})")


def handle_full_text_command(chat_id: int, argument: str, db: Database, telegram: TelegramApi) -> None:
    value = argument.strip().lower()
    language_code = db.get_user_settings(chat_id).language_code
    if value in {"on", "увімкнути", "вкл"}:
        plan = db.get_active_plan(chat_id)
        if not plan.full_text:
            telegram.send_message(
                chat_id,
                locale_text(language_code, "fulltext_unavailable"),
                reply_markup=main_menu_for_chat(chat_id, db),
            )
            return
        db.set_full_text_enabled(chat_id, True)
        telegram.send_message(
            chat_id,
            locale_text(language_code, "fulltext_enabled"),
            reply_markup=text_mode_menu_for_chat(chat_id, db),
        )
        return
    if value in {"off", "вимкнути", "викл"}:
        db.set_full_text_enabled(chat_id, False)
        telegram.send_message(
            chat_id,
            locale_text(language_code, "fast_mode_enabled"),
            reply_markup=text_mode_menu_for_chat(chat_id, db),
        )
        return
    send_text_mode(chat_id, db, telegram)


def handle_monitoring_mode_command(chat_id: int, argument: str, db: Database, telegram: TelegramApi) -> None:
    value = argument.strip().lower()
    language_code = db.get_user_settings(chat_id).language_code
    if value in {"auto", "automatic", "on"}:
        db.set_auto_monitoring_enabled(chat_id, True)
        telegram.send_message(
            chat_id,
            locale_text(language_code, "auto_monitoring_enabled"),
            reply_markup=monitoring_mode_menu_for_chat(chat_id, db),
        )
        return
    if value in {"manual", "off"}:
        db.set_auto_monitoring_enabled(chat_id, False)
        telegram.send_message(
            chat_id,
            locale_text(language_code, "manual_monitoring_enabled"),
            reply_markup=monitoring_mode_menu_for_chat(chat_id, db),
        )
        return
    send_monitoring_mode(chat_id, db, telegram)


def send_plans(chat_id: int, db: Database, telegram: TelegramApi) -> None:
    language_code = db.get_user_settings(chat_id).language_code
    plan = db.get_active_plan(chat_id)
    subscription = db.get_subscription(chat_id)
    expires = subscription["expires_at"] if subscription and plan.id != "free" else locale_text(language_code, "no_expiry")
    lines = [
        locale_text(language_code, "plans_title"),
        "",
        f"{locale_text(language_code, 'current_plan')}: {plan.name}",
        f"{locale_text(language_code, 'expires_at')}: {expires}",
        "",
        plan_text_localized(language_code, PLANS["free"]),
    ]
    for paid in paid_plans():
        lines.append(plan_text_localized(language_code, paid))
        lines.append(f"{locale_text(language_code, 'payment_command')}: /buy {paid.id}")
    lines.append("")
    lines.append(locale_text(language_code, "plan_activation_note"))
    telegram.send_message(
        chat_id,
        "\n".join(escape(line) for line in lines),
        disable_web_page_preview=True,
        reply_markup=main_menu_for_chat(chat_id, db),
    )


def plan_description(language_code: str, plan: Plan) -> str:
    return locale_text(language_code, f"plan_{plan.id}_description")


def plan_text_localized(language_code: str, plan: Plan) -> str:
    description = plan_description(language_code, plan)
    if plan.id == "free":
        return locale_text(language_code, "plan_free_template", name=plan.name, description=description)
    return locale_text(
        language_code,
        "plan_paid_template",
        name=plan.name,
        stars=plan.stars,
        days=plan.days,
        description=description,
    )


def send_plan_invoice(chat_id: int, plan_id: str, db: Database, telegram: TelegramApi) -> None:
    language_code = db.get_user_settings(chat_id).language_code
    plan = plan_by_id(plan_id.strip())
    if plan.id == "free":
        telegram.send_message(chat_id, locale_text(language_code, "choose_paid_plan"), reply_markup=main_menu_for_chat(chat_id, db))
        return
    payload = f"plan:{plan.id}:{chat_id}:{int(time.time())}"
    telegram.send_invoice(
        chat_id=chat_id,
        title=locale_text(language_code, "invoice_title", plan=plan.name, days=plan.days),
        description=plan_description(language_code, plan),
        payload=payload,
        prices=[{"label": locale_text(language_code, "invoice_price_label", plan=plan.name, days=plan.days), "amount": plan.stars}],
    )


def handle_pre_checkout_query(query: dict, telegram: TelegramApi) -> None:
    payload = str(query.get("invoice_payload") or "")
    plan_id = parse_plan_payload(payload)
    plan = plan_by_id(plan_id or "")
    if plan.id == "free":
        telegram.answer_pre_checkout_query(
            str(query["id"]),
            False,
            locale_text("en", "unknown_plan_checkout"),
        )
        return
    telegram.answer_pre_checkout_query(str(query["id"]), True)


def handle_successful_payment(chat_id: int, payment: dict, db: Database, telegram: TelegramApi) -> None:
    language_code = db.get_user_settings(chat_id).language_code
    payload = str(payment.get("invoice_payload") or "")
    plan_id = parse_plan_payload(payload)
    plan = plan_by_id(plan_id or "")
    if plan.id == "free":
        telegram.send_message(chat_id, locale_text(language_code, "payment_unknown_plan"), reply_markup=main_menu_for_chat(chat_id, db))
        return
    recorded = db.record_payment(
        chat_id=chat_id,
        plan_id=plan.id,
        currency=str(payment.get("currency") or ""),
        total_amount=int(payment.get("total_amount") or 0),
        invoice_payload=payload,
        telegram_payment_charge_id=payment.get("telegram_payment_charge_id"),
        provider_payment_charge_id=payment.get("provider_payment_charge_id"),
    )
    expires = db.activate_plan(chat_id, plan.id)
    status = locale_text(language_code, "payment_status_activated" if recorded else "payment_status_already")
    telegram.send_message(
        chat_id,
        locale_text(language_code, "payment_success", plan=escape(plan.name), status=escape(status), expires=escape(expires)),
        reply_markup=main_menu_for_chat(chat_id, db),
    )


def parse_plan_payload(payload: str) -> str | None:
    parts = payload.split(":")
    if len(parts) >= 2 and parts[0] == "plan":
        return parts[1]
    return None


def handle_grant_command(chat_id: int, argument: str, db: Database, telegram: TelegramApi) -> None:
    language_code = db.get_user_settings(chat_id).language_code
    if chat_id not in ADMIN_CHAT_IDS:
        telegram.send_message(chat_id, locale_text(language_code, "admin_only"), reply_markup=main_menu_for_chat(chat_id, db))
        return
    target_raw, _, rest = argument.strip().partition(" ")
    plan_raw, _, days_raw = rest.strip().partition(" ")
    try:
        target_chat_id = int(target_raw)
    except ValueError:
        telegram.send_message(chat_id, locale_text(language_code, "grant_format"), reply_markup=main_menu_for_chat(chat_id, db))
        return
    plan = plan_by_id(plan_raw)
    if plan.id == "free":
        telegram.send_message(chat_id, locale_text(language_code, "grant_plan_format"), reply_markup=main_menu_for_chat(chat_id, db))
        return
    try:
        days = int(days_raw) if days_raw else plan.days
    except ValueError:
        days = plan.days
    expires = db.activate_plan(target_chat_id, plan.id, days)
    telegram.send_message(
        chat_id,
        locale_text(language_code, "grant_success", plan=plan.name, chat_id=target_chat_id, expires=expires),
        reply_markup=main_menu_for_chat(chat_id, db),
    )


def send_users(chat_id: int, db: Database, telegram: TelegramApi) -> None:
    language_code = db.get_user_settings(chat_id).language_code
    if chat_id not in ADMIN_CHAT_IDS:
        telegram.send_message(chat_id, locale_text(language_code, "admin_only"), reply_markup=main_menu_for_chat(chat_id, db))
        return
    total = db.user_count()
    users = db.list_users(limit=30)
    lines = [locale_text(language_code, "users_count", total=total)]
    if len(users) < total:
        lines.append(locale_text(language_code, "users_shown", shown=len(users)))
    lines.append("")
    if not users:
        lines.append(locale_text(language_code, "users_empty"))
    for index, row in enumerate(users, start=1):
        user_chat_id = int(row["chat_id"])
        plan = db.get_active_plan(user_chat_id)
        expires = row["expires_at"] if plan.id != "free" and row["expires_at"] else "-"
        lines.extend(
            [
                f"{index}. ID: <code>{user_chat_id}</code>",
                locale_text(
                    language_code,
                    "users_plan_line",
                    plan=escape(plan.name),
                    keywords=row["keyword_count"],
                    sources=row["custom_source_count"],
                ),
                locale_text(language_code, "users_last_seen", last_seen=escape(row["last_seen_at"])),
                locale_text(language_code, "users_expires", expires=escape(expires)),
            ]
        )
    telegram.send_message(chat_id, "\n".join(lines), reply_markup=main_menu_for_chat(chat_id, db))


def can_add_keyword(chat_id: int, db: Database, telegram: TelegramApi) -> bool:
    plan = db.get_active_plan(chat_id)
    current = len(db.get_user_monitoring(chat_id).keywords)
    if current >= plan.max_keywords:
        language_code = db.get_user_settings(chat_id).language_code
        telegram.send_message(
            chat_id,
            locale_text(language_code, "keyword_limit", plan=escape(plan.name), limit=plan.max_keywords),
            reply_markup=main_menu_for_chat(chat_id, db),
        )
        return False
    return True


def handle_rss_command(chat_id: int, argument: str, db: Database, telegram: TelegramApi, sources) -> None:
    action, _, rest = argument.strip().partition(" ")
    action = action.lower()
    language_code = db.get_user_settings(chat_id).language_code

    if action in {"", "list", "список"}:
        send_sources(chat_id, db, telegram, sources)
        return

    if action == "add":
        if not rest.strip():
            telegram.send_message(
                chat_id,
                locale_text(language_code, "rss_add_format"),
                reply_markup=source_menu_for_chat(chat_id, db),
            )
            return
        add_custom_rss(chat_id, rest.strip(), db, telegram)
        return

    if action in {"off", "disable", "вимкнути"}:
        disable_rss_by_number(chat_id, rest, db, telegram, sources)
        return

    if action in {"on", "enable", "увімкнути"}:
        enable_rss_by_number(chat_id, rest, db, telegram, sources)
        return

    if action in {"remove", "delete", "видалити"}:
        remove_custom_rss_by_number(chat_id, rest, db, telegram, sources)
        return

    telegram.send_message(
        chat_id,
        locale_text(language_code, "rss_unknown_action"),
        reply_markup=source_menu_for_chat(chat_id, db),
    )


def handle_tg_command(chat_id: int, argument: str, db: Database, telegram: TelegramApi, sources) -> None:
    action, _, rest = argument.strip().partition(" ")
    action = action.lower()
    language_code = db.get_user_settings(chat_id).language_code
    if action in {"", "blocks", "list"}:
        send_tg_blocks(chat_id, db, telegram, sources)
        return
    if action in {"off", "disable"}:
        set_tg_block(chat_id, parse_block_number(rest), False, db, telegram, sources)
        return
    if action in {"on", "enable"}:
        set_tg_block(chat_id, parse_block_number(rest), True, db, telegram, sources)
        return
    if action == "add":
        if not rest.strip():
            telegram.send_message(
                chat_id,
                locale_text(language_code, "tg_add_format"),
                reply_markup=source_menu_for_chat(chat_id, db),
            )
            return
        add_custom_telegram(chat_id, rest.strip(), db, telegram)
        return
    telegram.send_message(
        chat_id,
        locale_text(language_code, "tg_available"),
        reply_markup=source_menu_for_chat(chat_id, db),
    )


def handle_tg_blocks_command(chat_id: int, argument: str, db: Database, telegram: TelegramApi, sources) -> None:
    action, _, rest = argument.strip().partition(" ")
    action = action.lower()
    language_code = db.get_user_settings(chat_id).language_code
    if action in {"", "list", "status"}:
        send_tg_blocks(chat_id, db, telegram, sources)
        return
    if action in {"off", "disable"}:
        set_tg_block(chat_id, parse_block_number(rest), False, db, telegram, sources)
        return
    if action in {"on", "enable"}:
        set_tg_block(chat_id, parse_block_number(rest), True, db, telegram, sources)
        return
    telegram.send_message(
        chat_id,
        locale_text(language_code, "tgblocks_available"),
        reply_markup=tg_blocks_menu(chat_id, db, country_sources(db.get_user_settings(chat_id).country_code, sources)),
    )


def send_tg_blocks(chat_id: int, db: Database, telegram: TelegramApi, sources) -> None:
    plan = db.get_active_plan(chat_id)
    language_code = db.get_user_settings(chat_id).language_code
    if plan.id == "free":
        telegram.send_message(
            chat_id,
            locale_text(language_code, "paid_tg_only"),
            reply_markup=source_menu_for_chat(chat_id, db),
        )
        return
    telegram.send_message(
        chat_id,
        format_tg_blocks(chat_id, db, sources),
        disable_web_page_preview=True,
        reply_markup=tg_blocks_menu(chat_id, db, country_sources(db.get_user_settings(chat_id).country_code, sources)),
    )


def set_tg_block(
    chat_id: int,
    block_number: int,
    enabled: bool,
    db: Database,
    telegram: TelegramApi,
    sources,
) -> None:
    plan = db.get_active_plan(chat_id)
    language_code = db.get_user_settings(chat_id).language_code
    if plan.id == "free":
        telegram.send_message(
            chat_id,
            locale_text(language_code, "paid_tg_only"),
            reply_markup=source_menu_for_chat(chat_id, db),
        )
        return
    current_sources = country_sources(db.get_user_settings(chat_id).country_code, sources)
    blocks = tg_source_blocks(current_sources)
    if block_number < 1 or block_number > len(blocks):
        telegram.send_message(
            chat_id,
            locale_text(language_code, "tg_block_number_prompt"),
            reply_markup=tg_blocks_menu(chat_id, db, current_sources),
        )
        return
    block = blocks[block_number - 1]
    urls = [source.url for source in block]
    changed = db.enable_sources(chat_id, urls) if enabled else db.disable_sources(chat_id, urls)
    action = locale_text(language_code, "status_enabled" if enabled else "status_disabled")
    telegram.send_message(
        chat_id,
        locale_text(language_code, "tg_block_updated", block=tg_block_title(language_code, block_number, block), status=action, changed=changed) + "\n\n"
        + format_tg_blocks(chat_id, db, sources),
        disable_web_page_preview=True,
        reply_markup=tg_blocks_menu(chat_id, db, current_sources),
    )


def format_tg_blocks(chat_id: int, db: Database, sources) -> str:
    language_code = db.get_user_settings(chat_id).language_code
    monitoring = db.get_user_monitoring(chat_id)
    disabled = set(monitoring.disabled_source_urls)
    blocks = tg_source_blocks(country_sources(db.get_user_settings(chat_id).country_code, sources))
    if not blocks:
        return locale_text(language_code, "paid_tg_empty")
    lines = [locale_text(language_code, "paid_tg_title"), ""]
    total_active = 0
    total_sources = 0
    for index, block in enumerate(blocks, start=1):
        active = sum(1 for source in block if normalize_url(source.url) not in disabled)
        total_active += active
        total_sources += len(block)
        if active == len(block):
            status = "✅"
        elif active == 0:
            status = "⛔"
        else:
            status = "◐"
        lines.append(
            f"{index}. {status} {tg_block_title(language_code, index, block)}: "
            f"{active}/{len(block)} {locale_text(language_code, 'active_word')}"
        )
    lines.extend(
        [
            "",
            locale_text(language_code, "tg_blocks_total", active=total_active, total=total_sources),
            locale_text(language_code, "tg_blocks_hint"),
            locale_text(language_code, "tg_blocks_commands"),
        ]
    )
    return "\n".join(lines)


def tg_blocks_menu(chat_id: int, db: Database, sources) -> dict:
    language_code = db.get_user_settings(chat_id).language_code
    rows = []
    for index, block in enumerate(tg_source_blocks(sources), start=1):
        label = tg_block_range(index, block)
        rows.append([{"text": f"⛔ TG {label}"}, {"text": f"✅ TG {label}"}])
    rows.append([{"text": button_label(language_code, "source_list")}, {"text": button_label(language_code, "back")}])
    return {"keyboard": rows, "resize_keyboard": True, "is_persistent": True}


def tg_source_blocks(sources) -> list[list[Source]]:
    paid_sources = [source for source in sources if source.type == "telegram_paid"]
    return [
        paid_sources[index : index + TG_BLOCK_SIZE]
        for index in range(0, len(paid_sources), TG_BLOCK_SIZE)
    ]


def country_sources(country_code: str, sources) -> list[Source]:
    return [source for source in sources if source.country == country_code]


def tg_block_title(language_code: str, block_number: int, block: list[Source]) -> str:
    start = (block_number - 1) * TG_BLOCK_SIZE + 1
    end = start + len(block) - 1
    if block_number == 1:
        return locale_text(language_code, "top_block_first", start=start, end=end)
    return locale_text(language_code, "top_block", start=start, end=end)


def tg_block_range(block_number: int, block: list[Source]) -> str:
    start = (block_number - 1) * TG_BLOCK_SIZE + 1
    end = start + len(block) - 1
    return f"{start}-{end}"


def parse_tg_block_button(text: str) -> tuple[str, int] | None:
    value = text.strip()
    if value.startswith("⛔ TG "):
        return "off", parse_block_number(value.removeprefix("⛔ TG "))
    if value.startswith("✅ TG "):
        return "on", parse_block_number(value.removeprefix("✅ TG "))
    return None


def parse_block_number(value: str) -> int:
    match = re.search(r"\d+", value or "")
    if not match:
        return 0
    number = int(match.group(0))
    if number > 10:
        return (number + TG_BLOCK_SIZE - 1) // TG_BLOCK_SIZE
    return number


def add_custom_rss(chat_id: int, value: str, db: Database, telegram: TelegramApi) -> None:
    language_code = db.get_user_settings(chat_id).language_code
    plan = db.get_active_plan(chat_id)
    custom_count = len(db.get_user_monitoring(chat_id).custom_sources)
    if custom_count >= plan.max_custom_sources:
        telegram.send_message(
            chat_id,
            locale_text(language_code, "custom_rss_limit", plan=escape(plan.name), limit=plan.max_custom_sources),
            reply_markup=source_menu_for_chat(chat_id, db),
        )
        return

    url, name = parse_rss_add_value(value)
    if not valid_http_url(url):
        telegram.send_message(
            chat_id,
            locale_text(language_code, "invalid_rss_url"),
            reply_markup=source_menu_for_chat(chat_id, db),
        )
        return

    source = Source(name or source_name_from_url(url), url, "rss", country=db.get_user_settings(chat_id).country_code)
    try:
        articles = fetch_rss(source, 20)
    except Exception:
        telegram.send_message(
            chat_id,
            locale_text(language_code, "rss_read_failed"),
            reply_markup=source_menu_for_chat(chat_id, db),
        )
        return

    if not articles:
        telegram.send_message(
            chat_id,
            locale_text(language_code, "rss_empty"),
            reply_markup=source_menu_for_chat(chat_id, db),
        )
        return

    added = db.add_user_source(chat_id, source)
    telegram.send_message(
        chat_id,
        f"{locale_text(language_code, 'custom_rss_added' if added else 'custom_rss_exists')}: {escape(source.name)}\n{escape(source.url)}",
        disable_web_page_preview=True,
        reply_markup=source_menu_for_chat(chat_id, db),
    )


def add_custom_telegram(chat_id: int, value: str, db: Database, telegram: TelegramApi) -> None:
    language_code = db.get_user_settings(chat_id).language_code
    plan = db.get_active_plan(chat_id)
    custom_count = len(db.get_user_monitoring(chat_id).custom_sources)
    if custom_count >= plan.max_custom_sources:
        telegram.send_message(
            chat_id,
            locale_text(language_code, "custom_source_limit", plan=escape(plan.name), limit=plan.max_custom_sources),
            reply_markup=source_menu_for_chat(chat_id, db),
        )
        return

    url, name = parse_telegram_add_value(value)
    if not url:
        telegram.send_message(
            chat_id,
            locale_text(language_code, "invalid_tg_url"),
            reply_markup=source_menu_for_chat(chat_id, db),
        )
        return

    source = Source(name or source_name_from_url(url), url, "telegram", country=db.get_user_settings(chat_id).country_code)
    try:
        articles = fetch_telegram_channel(source, 20)
    except Exception:
        telegram.send_message(
            chat_id,
            locale_text(language_code, "tg_read_failed"),
            reply_markup=source_menu_for_chat(chat_id, db),
        )
        return

    if not articles:
        telegram.send_message(
            chat_id,
            locale_text(language_code, "tg_empty"),
            reply_markup=source_menu_for_chat(chat_id, db),
        )
        return

    added = db.add_user_source(chat_id, source)
    telegram.send_message(
        chat_id,
        f"{locale_text(language_code, 'custom_tg_added' if added else 'custom_tg_exists')}: {escape(source.name)}\n{escape(source.url)}",
        disable_web_page_preview=True,
        reply_markup=source_menu_for_chat(chat_id, db),
    )


def disable_rss_by_number(chat_id: int, value: str, db: Database, telegram: TelegramApi, sources) -> None:
    language_code = db.get_user_settings(chat_id).language_code
    row = find_source_row(chat_id, value, db, sources)
    if row is None:
        telegram.send_message(
            chat_id,
            locale_text(language_code, "source_lookup_prompt") + "\n\n" + format_sources(chat_id, db, sources),
            reply_markup=source_menu_for_chat(chat_id, db),
        )
        return
    if row["custom"]:
        telegram.send_message(chat_id, locale_text(language_code, "custom_sources_not_disabled"), reply_markup=source_menu_for_chat(chat_id, db))
        return
    if not row["enabled"]:
        telegram.send_message(chat_id, locale_text(language_code, "source_already_disabled"), reply_markup=source_menu_for_chat(chat_id, db))
        return
    db.disable_source(chat_id, row["source"].url)
    telegram.send_message(
        chat_id,
        locale_text(language_code, "source_disabled", source=escape(row["source"].name)),
        reply_markup=source_menu_for_chat(chat_id, db),
    )


def enable_rss_by_number(chat_id: int, value: str, db: Database, telegram: TelegramApi, sources) -> None:
    language_code = db.get_user_settings(chat_id).language_code
    row = find_source_row(chat_id, value, db, sources)
    if row is None:
        telegram.send_message(
            chat_id,
            locale_text(language_code, "source_lookup_prompt") + "\n\n" + format_sources(chat_id, db, sources),
            reply_markup=source_menu_for_chat(chat_id, db),
        )
        return
    if row["custom"]:
        telegram.send_message(chat_id, locale_text(language_code, "custom_sources_already_active"), reply_markup=source_menu_for_chat(chat_id, db))
        return
    if row["enabled"]:
        telegram.send_message(chat_id, locale_text(language_code, "source_already_enabled"), reply_markup=source_menu_for_chat(chat_id, db))
        return
    db.enable_source(chat_id, row["source"].url)
    telegram.send_message(
        chat_id,
        locale_text(language_code, "source_enabled", source=escape(row["source"].name)),
        reply_markup=source_menu_for_chat(chat_id, db),
    )


def remove_custom_rss_by_number(chat_id: int, value: str, db: Database, telegram: TelegramApi, sources) -> None:
    language_code = db.get_user_settings(chat_id).language_code
    row = find_source_row(chat_id, value, db, sources)
    if row is None:
        telegram.send_message(
            chat_id,
            locale_text(language_code, "custom_source_lookup_prompt") + "\n\n" + format_sources(chat_id, db, sources),
            reply_markup=source_menu_for_chat(chat_id, db),
        )
        return
    if not row["custom"]:
        telegram.send_message(chat_id, locale_text(language_code, "standard_sources_not_removed"), reply_markup=source_menu_for_chat(chat_id, db))
        return
    removed = db.remove_user_source(chat_id, row["source"].url)
    telegram.send_message(
        chat_id,
        f"{locale_text(language_code, 'custom_source_removed' if removed else 'source_not_found')}: {escape(row['source'].name)}",
        reply_markup=source_menu_for_chat(chat_id, db),
    )


def send_help(chat_id: int, db: Database, telegram: TelegramApi) -> None:
    language_code = db.get_user_settings(chat_id).language_code
    telegram.send_message(
        chat_id,
        locale_text(language_code, "help_text"),
        disable_web_page_preview=True,
        reply_markup=main_menu_for_chat(chat_id, db),
    )


def send_info(chat_id: int, db: Database, telegram: TelegramApi, sources) -> None:
    monitoring = db.get_user_monitoring(chat_id)
    settings = db.get_user_settings(chat_id)
    plan = db.get_active_plan(chat_id)
    language_code = settings.language_code
    text_mode = locale_text(
        language_code,
        "text_mode_full" if monitoring.full_text_enabled else "text_mode_fast",
    )
    monitoring_mode = auto_monitoring_text(language_code, monitoring.auto_monitoring_enabled)
    keyword_countries = {keyword.country_code for keyword in monitoring.keywords}
    active_sources = len(db.get_enabled_sources(chat_id, sources, keyword_countries or None))
    telegram.send_message(
        chat_id,
        f"{locale_text(language_code, 'info_title')}:\n\n"
        f"{locale_text(language_code, 'language')}: {escape(language_name(language_code))}\n"
        f"{locale_text(language_code, 'country')}: {escape(country_name(settings.country_code, language_code))}\n\n"
        f"{locale_text(language_code, 'keywords')}: {format_keywords(language_code, monitoring.keywords)}\n"
        f"{locale_text(language_code, 'stop_words')}: {format_terms(language_code, monitoring.stop_words)}\n"
        f"{locale_text(language_code, 'plus_words')}: {format_terms(language_code, monitoring.plus_words)}\n\n"
        f"{locale_text(language_code, 'search_mode')}: {escape(text_mode)}\n"
        f"{locale_text(language_code, 'monitoring_mode_label')}: {escape(monitoring_mode)}\n"
        f"{locale_text(language_code, 'active_sources')}: {active_sources}\n"
        f"{locale_text(language_code, 'auto_check')}: "
        f"{monitor_interval_text(language_code, plan.id) if monitoring.auto_monitoring_enabled else locale_text(language_code, 'auto_check_off')}.",
        disable_web_page_preview=True,
        reply_markup=main_menu_for_chat(chat_id, db),
    )


def monitor_interval_text(language_code: str, plan_id: str) -> str:
    if plan_id == "business":
        return locale_text(language_code, "interval_business")
    if plan_id in {"basic", "pro"}:
        return locale_text(language_code, "interval_paid")
    return locale_text(language_code, "interval_free")


def auto_monitoring_text(language_code: str, enabled: bool) -> str:
    return locale_text(
        language_code,
        "monitoring_mode_auto" if enabled else "monitoring_mode_manual",
    )


def send_monitoring_mode(chat_id: int, db: Database, telegram: TelegramApi) -> None:
    monitoring = db.get_user_monitoring(chat_id)
    language_code = db.get_user_settings(chat_id).language_code
    current = auto_monitoring_text(language_code, monitoring.auto_monitoring_enabled)
    telegram.send_message(
        chat_id,
        f"{locale_text(language_code, 'monitoring_mode_intro')}\n\n"
        f"{locale_text(language_code, 'current_mode')}: {escape(current)}\n\n"
        f"{locale_text(language_code, 'monitoring_mode_note')}",
        reply_markup=monitoring_mode_menu_for_chat(chat_id, db),
    )


def send_text_mode(chat_id: int, db: Database, telegram: TelegramApi) -> None:
    monitoring = db.get_user_monitoring(chat_id)
    language_code = db.get_user_settings(chat_id).language_code
    current = locale_text(
        language_code,
        "text_mode_full" if monitoring.full_text_enabled else "text_mode_fast",
    )
    telegram.send_message(
        chat_id,
        f"{locale_text(language_code, 'text_mode_intro')}\n\n"
        f"{locale_text(language_code, 'current_mode')}: {escape(current)}\n\n"
        f"{locale_text(language_code, 'text_mode_note')}",
        reply_markup=text_mode_menu_for_chat(chat_id, db),
    )


def send_sources(chat_id: int, db: Database, telegram: TelegramApi, sources) -> None:
    telegram.send_message(
        chat_id,
        format_sources(chat_id, db, sources),
        disable_web_page_preview=True,
        reply_markup=source_menu_for_chat(chat_id, db),
    )


def send_sources_file(chat_id: int, db: Database, telegram: TelegramApi, sources) -> None:
    path = write_sources_table(chat_id, db, sources, Path("reports"))
    language_code = db.get_user_settings(chat_id).language_code
    telegram.send_document(chat_id, path, locale_text(language_code, "sources_file_caption"))


def write_sources_table(chat_id: int, db: Database, sources, output_dir: Path) -> Path:
    language_code = db.get_user_settings(chat_id).language_code
    output_dir.mkdir(parents=True, exist_ok=True)
    path = output_dir / f"media-monitor-sources-{chat_id}.csv"
    rows = source_rows(chat_id, db, sources)
    visible_number_by_url = visible_source_numbers(rows)
    disabled_rows = [row for row in rows if not row["enabled"]]
    with path.open("w", encoding="utf-8-sig", newline="") as fh:
        writer = csv.writer(fh)
        writer.writerow(
            [
                "list_number",
                "tg_rank",
                "tg_package",
                "status",
                "access",
                "country",
                "language",
                "type",
                "name",
                "username",
                "subscribers",
                "url",
                "disable_command",
                "enable_command",
            ]
        )
        for row in rows:
            source = row["source"]
            username = telegram_username(source.url)
            visible_number = visible_number_by_url.get(normalize_url(source.url), "")
            tg_rank = source.rank or ""
            tg_block = tg_block_label_for_rank(source.rank) if source.type == "telegram_paid" else ""
            lookup = f"@{username}" if username else str(visible_number)
            writer.writerow(
                [
                    visible_number,
                    tg_rank,
                    tg_block,
                    locale_text(language_code, "status_enabled" if row["enabled"] else "status_disabled"),
                    locale_text(language_code, "source_kind_custom" if row["custom"] else "source_kind_standard"),
                    source.country,
                    source.language,
                    source.type,
                    display_source_name(source),
                    f"@{username}" if username else "",
                    source.subscribers or "",
                    display_source_url(source),
                    f"/rss off {lookup}".strip(),
                    f"/rss on {lookup}".strip(),
                ]
            )
        if disabled_rows:
            writer.writerow([])
            writer.writerow(["Disabled sources"])
            for row in disabled_rows:
                writer.writerow([display_source_name(row["source"]), display_source_url(row["source"])])
    return path


def visible_source_numbers(rows: list[dict]) -> dict[str, int]:
    result: dict[str, int] = {}
    visible_rows = [row for row in rows if row["source"].type != "telegram_paid"]
    for display_number, row in enumerate(visible_rows, start=1):
        result[normalize_url(row["source"].url)] = display_number
    return result


def tg_block_label_for_rank(rank: int | None) -> str:
    if not rank:
        return ""
    block_number = (rank + TG_BLOCK_SIZE - 1) // TG_BLOCK_SIZE
    start = (block_number - 1) * TG_BLOCK_SIZE + 1
    end = min(block_number * TG_BLOCK_SIZE, 230)
    return f"{start}-{end}"


def format_sources(chat_id: int, db: Database, sources) -> str:
    language_code = db.get_user_settings(chat_id).language_code
    rows = source_rows(chat_id, db, sources)
    active_count = sum(1 for row in rows if row["enabled"])
    paid_tg_rows = [row for row in rows if row["source"].type == "telegram_paid"]
    visible_rows = [row for row in rows if row["source"].type != "telegram_paid"]
    lines = [
        locale_text(language_code, "sources_title", active=active_count, total=len(rows)),
        "",
    ]
    for display_number, row in enumerate(visible_rows, start=1):
        status = "✅" if row["enabled"] else "⛔"
        kind = locale_text(language_code, "source_kind_custom" if row["custom"] else "source_kind_standard")
        source = row["source"]
        lines.append(f"{display_number}. {status} {escape(display_source_name(source))} ({kind}, {escape(source.type)})")
        source_url = display_source_url(source)
        if source_url:
            lines.append(f"   {escape(source_url)}")
    if paid_tg_rows:
        paid_active = sum(1 for row in paid_tg_rows if row["enabled"])
        lines.extend(
            [
                "",
                locale_text(language_code, "paid_tg_summary", active=paid_active, total=len(paid_tg_rows)),
                locale_text(language_code, "paid_tg_manage_hint"),
            ]
        )
    lines.append("")
    lines.append(locale_text(language_code, "rss_commands_hint"))
    return "\n".join(lines)


def display_source_name(source: Source) -> str:
    return re.sub(r"\s+via\s+Google\s+News\s*$", "", source.name, flags=re.IGNORECASE).strip() or source.name


def display_source_url(source: Source) -> str:
    if is_google_news_source(source.url):
        site = google_news_site_query(source.url)
        return site or ""
    return source.url


def is_google_news_source(url: str) -> bool:
    host = urlparse(url).netloc.lower()
    return host.endswith("news.google.com")


def google_news_site_query(url: str) -> str:
    parsed = urlparse(url)
    query = parse_qs(parsed.query).get("q", [""])[0].strip()
    match = re.search(r"site:([^\s]+)", query, flags=re.IGNORECASE)
    if not match:
        return ""
    return match.group(1).strip()


def source_rows(chat_id: int, db: Database, sources) -> list[dict]:
    monitoring = db.get_user_monitoring(chat_id)
    plan = db.get_active_plan(chat_id)
    disabled = set(monitoring.disabled_source_urls)
    settings = db.get_user_settings(chat_id)
    rows: list[dict] = []
    number = 1
    for source in sources:
        if source.country != settings.country_code:
            continue
        if not source_allowed_for_plan(source, plan.id):
            continue
        rows.append(
            {
                "number": number,
                "source": source,
                "custom": False,
                "enabled": normalize_url(source.url) not in disabled,
            }
        )
        number += 1
    for source in monitoring.custom_sources:
        rows.append(
            {
                "number": number,
                "source": source,
                "custom": True,
                "enabled": True,
            }
        )
        number += 1
    return rows


def find_source_row(chat_id: int, value: str, db: Database, sources) -> dict | None:
    raw = value.strip()
    if not raw:
        return None
    try:
        number = int(raw)
    except ValueError:
        number = None
    visible_rows = [
        row
        for row in source_rows(chat_id, db, sources)
        if row["source"].type != "telegram_paid"
    ]
    if number is not None:
        for display_number, row in enumerate(visible_rows, start=1):
            if display_number == number:
                return row
        return None
    return find_source_row_by_text(raw, source_rows(chat_id, db, sources))


def find_source_row_by_text(value: str, rows: list[dict]) -> dict | None:
    raw = value.strip()
    needle = raw.lower().lstrip("@")
    if not needle:
        return None
    normalized_input = normalize_source_lookup_url(raw)
    matches = []
    for row in rows:
        source = row["source"]
        username = telegram_username(source.url).lower()
        source_url = normalize_url(source.url).lower()
        source_name = source.name.lower()
        if normalized_input and normalized_input == source_url:
            return row
        if username and needle == username:
            return row
        if needle == source_url or needle in source_name:
            matches.append(row)
    if len(matches) == 1:
        return matches[0]
    return None


def normalize_source_lookup_url(value: str) -> str:
    raw = value.strip()
    if not raw:
        return ""
    if raw.startswith("@") or raw.startswith("t.me/") or raw.startswith("telegram.me/"):
        return normalize_url(telegram_preview_url(raw)).lower()
    if raw.startswith("http://") or raw.startswith("https://"):
        parsed = urlparse(raw)
        if parsed.netloc.lower() in {"t.me", "telegram.me"}:
            return normalize_url(telegram_preview_url(raw)).lower()
        return normalize_url(raw).lower()
    return ""


def telegram_username(url: str) -> str:
    parsed = urlparse(url)
    if parsed.netloc.lower() not in {"t.me", "telegram.me"}:
        return ""
    parts = [part for part in parsed.path.split("/") if part]
    if parts and parts[0].lower() == "s" and len(parts) > 1:
        return parts[1]
    if parts:
        return parts[0]
    return ""


def parse_rss_add_value(value: str) -> tuple[str, str]:
    url, _, name = value.strip().partition(" ")
    return url.strip(), name.strip()


def parse_telegram_add_value(value: str) -> tuple[str, str]:
    raw, _, name = value.strip().partition(" ")
    if not raw:
        return "", ""
    url = telegram_preview_url(raw)
    return url, name.strip()


def valid_http_url(url: str) -> bool:
    parsed = urlparse(url)
    return parsed.scheme in {"http", "https"} and bool(parsed.netloc)


def source_name_from_url(url: str) -> str:
    parsed = urlparse(url)
    if parsed.netloc == "t.me":
        parts = [part for part in parsed.path.split("/") if part]
        if parts and parts[0] == "s" and len(parts) > 1:
            return f"Telegram @{parts[1]}"
        if parts:
            return f"Telegram @{parts[0]}"
    return parsed.netloc or "My source"


def run_manual_check(chat_id: int, db: Database, telegram: TelegramApi, monitor: Monitor) -> None:
    language_code = db.get_user_settings(chat_id).language_code
    telegram.send_message(chat_id, locale_text(language_code, "manual_check_start"), reply_markup=main_menu_for_chat(chat_id, db))
    sent = run_monitor_safely(monitor, {chat_id}, wait_seconds=MANUAL_CHECK_WAIT_SECONDS)
    if sent is None:
        telegram.send_message(
            chat_id,
            locale_text(language_code, "manual_check_busy"),
            reply_markup=main_menu_for_chat(chat_id, db),
        )
        return
    telegram.send_message(
        chat_id,
        locale_text(language_code, "manual_check_done", sent=sent),
        reply_markup=main_menu_for_chat(chat_id, db),
    )


def send_report(chat_id: int, db: Database, telegram: TelegramApi) -> None:
    path = write_csv_report(db, chat_id, Path("reports"))
    language_code = db.get_user_settings(chat_id).language_code
    telegram.send_document(chat_id, path, locale_text(language_code, "report_caption"))


def split_command(text: str) -> tuple[str, str]:
    first, _, rest = text.strip().partition(" ")
    command = first.split("@", 1)[0].lower()
    return command, rest.strip()


def format_terms(language_code: str, values: tuple[str, ...]) -> str:
    if not values:
        return locale_text(language_code, "empty_terms")
    return ", ".join(escape(value) for value in values)


def format_keywords(language_code: str, values) -> str:
    if not values:
        return locale_text(language_code, "empty_terms")
    return ", ".join(
        f"{escape(value.phrase)} ({escape(country_name(value.country_code, language_code))})"
        for value in values
    )


def format_add_result(language_code: str, label: str, value: str, added: bool) -> str:
    status = locale_text(language_code, "added" if added else "already_exists")
    return f"{label} {status}: {escape(value)}"


def format_remove_result(language_code: str, label: str, value: str, removed: bool) -> str:
    status = locale_text(language_code, "removed" if removed else "not_found")
    return f"{label} {status}: {escape(value)}"


if __name__ == "__main__":
    raise SystemExit(main())

