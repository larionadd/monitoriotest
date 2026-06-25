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
from urllib.parse import urlparse

from .billing import PLANS, paid_plans, plan_by_id, plan_text
from .config import Source, load_config
from .db import Database, normalize_url, source_allowed_for_plan
from .locales import (
    COUNTRIES,
    LANGUAGES,
    country_from_button,
    country_name,
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

MAIN_MENU = {
    "keyboard": [
        [{"text": BTN_ADD}, {"text": BTN_REMOVE}],
        [{"text": BTN_INFO}, {"text": BTN_CHECK}],
        [{"text": BTN_SOURCES}, {"text": BTN_REPORT}],
        [{"text": BTN_FILTERS}, {"text": BTN_TEXT_MODE}],
        [{"text": BTN_PLANS}, {"text": BTN_HELP}],
    ],
    "resize_keyboard": True,
    "is_persistent": True,
}

MINI_APP_URL = ""
REQUIRE_ONBOARDING = False
TRIAL_PLAN_ID = ""
TRIAL_DAYS = 7


def main_menu_for_chat(chat_id: int, db: Database) -> dict:
    keyboard = [[dict(button) for button in row] for row in MAIN_MENU["keyboard"]]
    if MINI_APP_URL and (REQUIRE_ONBOARDING or db.get_active_plan(chat_id).id == "business"):
        keyboard.insert(0, [{"text": BTN_APP, "web_app": {"url": MINI_APP_URL}}])
    if REQUIRE_ONBOARDING:
        keyboard.insert(-1, [{"text": BTN_SETTINGS}])
    return {**MAIN_MENU, "keyboard": keyboard}


FILTER_MENU = {
    "keyboard": [
        [{"text": BTN_STOP_ADD}, {"text": BTN_STOP_REMOVE}],
        [{"text": BTN_PLUS_ADD}, {"text": BTN_PLUS_REMOVE}],
        [{"text": BTN_INFO}, {"text": BTN_BACK}],
    ],
    "resize_keyboard": True,
    "is_persistent": True,
}

TEXT_MODE_MENU = {
    "keyboard": [
        [{"text": BTN_FULL_TEXT_ON}, {"text": BTN_FULL_TEXT_OFF}],
        [{"text": BTN_INFO}, {"text": BTN_BACK}],
    ],
    "resize_keyboard": True,
    "is_persistent": True,
}

SOURCE_MENU = {
    "keyboard": [
        [{"text": BTN_SOURCE_LIST}, {"text": BTN_TG_BLOCKS}],
        [{"text": BTN_SOURCES_FILE}],
        [{"text": BTN_SOURCE_ADD}, {"text": BTN_TG_ADD}],
        [{"text": BTN_SOURCE_DISABLE}, {"text": BTN_SOURCE_ENABLE}],
        [{"text": BTN_SOURCE_REMOVE}, {"text": BTN_BACK}],
    ],
    "resize_keyboard": True,
    "is_persistent": True,
}

SETTINGS_MENU = {
    "keyboard": [
        [{"text": BTN_LANGUAGE}, {"text": BTN_COUNTRY}],
        [{"text": BTN_INFO}, {"text": BTN_BACK}],
    ],
    "resize_keyboard": True,
    "is_persistent": True,
}

HELP = """Команди:
/add ключова фраза - додати ключову фразу
/remove ключова фраза - видалити ключову фразу
/plans - показати тарифи
/buy plan - оплатити тариф через Telegram Stars
/fulltext on - увімкнути пошук у повному тексті новин
/fulltext off - повернути швидкий пошук у заголовку та RSS-анонсі
/fulltext status - показати поточний режим пошуку
/rss list - показати RSS і Telegram-джерела
/rss add URL - додати власне RSS-джерело
/rss off номер - вимкнути стандартне RSS-джерело
/rss on номер - увімкнути стандартне RSS-джерело
/rss remove номер - видалити власне RSS-джерело
/tg add @channel - додати власний публічний Telegram-канал
/tgblocks - керувати платними Telegram-джерелами блоками по 50
/addstopword слово - не показувати матеріали з цим словом
/removestopword слово - видалити стоп-слово
/addplusword слово - показувати тільки матеріали, де є це слово
/removeplusword слово - видалити плюс-слово
/info - показати мої налаштування
/sources - показати кількість джерел
/sourcesfile - отримати файл з усіма джерелами
/check - перевірити джерела зараз
/report - отримати CSV-звіт
/help - допомога
"""

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
    configure_mini_app(config, telegram)
    configure_bot_commands(telegram)
    sources = load_sources(config.sources_path)
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
                    telegram.send_message(
                        int(chat_id),
                        "Не вдалося виконати дію з Mini App. Спробуйте ще раз.",
                        reply_markup=main_menu_for_chat(chat_id, db),
                    )
                continue
            if not text:
                continue
            try:
                handle_message(int(chat_id), text, db, telegram, monitor, sources)
            except Exception:
                logging.exception("Не вдалося обробити повідомлення від %s", chat_id)
                telegram.send_message(
                    int(chat_id),
                    "Не вдалося обробити повідомлення. Спробуйте ще раз.",
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


def configure_mini_app(config, telegram: TelegramApi) -> None:
    global MINI_APP_URL
    MINI_APP_URL = config.mini_app_url
    if not config.mini_app_url:
        return
    try:
        telegram.set_default_chat_menu_button()
    except Exception:
        logging.exception("Не вдалося скинути глобальну Telegram menu button для Mini App")
    try:
        start_static_server(config.mini_app_host, config.mini_app_port, config.mini_app_static_path)
    except Exception:
        logging.exception("Не вдалося запустити Mini App server")


def configure_bot_commands(telegram: TelegramApi) -> None:
    commands = [
            {"command": "start", "description": "Запустити бота і показати меню"},
            {"command": "add", "description": "Додати ключову фразу"},
            {"command": "remove", "description": "Видалити ключову фразу"},
            {"command": "plans", "description": "Показати тарифи"},
            {"command": "buy", "description": "Оплатити тариф"},
            {"command": "fulltext", "description": "Керувати пошуком у повному тексті"},
            {"command": "rss", "description": "Керувати джерелами"},
            {"command": "tg", "description": "Додати Telegram-канал"},
            {"command": "tgblocks", "description": "Керувати TG-пакетами"},
            {"command": "info", "description": "Показати мої налаштування"},
            {"command": "sources", "description": "Показати джерела"},
            {"command": "sourcesfile", "description": "Файл з усіма джерелами"},
            {"command": "check", "description": "Перевірити зараз"},
            {"command": "report", "description": "Отримати CSV-звіт"},
            {"command": "help", "description": "Допомога"},
    ]
    if REQUIRE_ONBOARDING:
        commands[9:9] = [
            {"command": "settings", "description": "Налаштування мови та регіону"},
            {"command": "language", "description": "Змінити мову інтерфейсу"},
            {"command": "country", "description": "Змінити регіон моніторингу"},
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
    if not REQUIRE_ONBOARDING and db.get_active_plan(chat_id).id != "business":
        telegram.send_message(
            chat_id,
            "Кабінет доступний тільки у тарифі Business. Оновіть тариф через /plans.",
            reply_markup=main_menu_for_chat(chat_id, db),
        )
        return
    try:
        payload = json.loads(web_app_data.get("data") or "{}")
    except json.JSONDecodeError:
        telegram.send_message(chat_id, "Mini App надіслав некоректні дані.", reply_markup=main_menu_for_chat(chat_id, db))
        return
    action = str(payload.get("action") or "").strip()
    value = str(payload.get("value") or "").strip()

    if action == "set_country":
        country_code = str(payload.get("country") or value).strip()
        handle_country_choice(chat_id, country_code, db, telegram)
        return

    if action == "add_keyword":
        if not value:
            telegram.send_message(chat_id, "Вкажіть ключову фразу.", reply_markup=main_menu_for_chat(chat_id, db))
            return
        if not can_add_keyword(chat_id, db, telegram):
            return
        added = db.add_keyword(chat_id, value)
        telegram.send_message(chat_id, format_add_result("Ключову фразу", value, added), reply_markup=main_menu_for_chat(chat_id, db))
        return

    if action == "remove_keyword":
        if not value:
            telegram.send_message(chat_id, "Вкажіть ключову фразу для видалення.", reply_markup=main_menu_for_chat(chat_id, db))
            return
        removed = db.remove_keyword(chat_id, value)
        telegram.send_message(chat_id, format_remove_result("Ключову фразу", value, removed), reply_markup=main_menu_for_chat(chat_id, db))
        return

    if action == "fulltext":
        enabled = bool(payload.get("enabled"))
        plan = db.get_active_plan(chat_id)
        if enabled and not plan.full_text:
            telegram.send_message(chat_id, "Пошук у повному тексті доступний у тарифах Pro та Business.", reply_markup=main_menu_for_chat(chat_id, db))
            return
        db.set_full_text_enabled(chat_id, enabled)
        status = "увімкнено" if enabled else "вимкнено"
        telegram.send_message(chat_id, f"Пошук у повному тексті {status}.", reply_markup=main_menu_for_chat(chat_id, db))
        return

    if action == "tg_block":
        block_number = parse_block_number(str(payload.get("block") or ""))
        enabled = bool(payload.get("enabled"))
        set_tg_block(chat_id, block_number, enabled, db, telegram, sources)
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

    telegram.send_message(chat_id, "Невідома дія Mini App.", reply_markup=main_menu_for_chat(chat_id, db))


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

    if text == BTN_PLANS:
        send_plans(chat_id, db, telegram)
        return

    if text.startswith("/"):
        handle_command(chat_id, text, db, telegram, monitor, sources)
        return

    if text:
        message_payment = None

    if text == BTN_ADD:
        PENDING_ACTIONS[chat_id] = "add_keyword"
        telegram.send_message(chat_id, "Надішліть ключову фразу одним повідомленням.", reply_markup=main_menu_for_chat(chat_id, db))
        return

    if text == BTN_REMOVE:
        PENDING_ACTIONS[chat_id] = "remove_keyword"
        telegram.send_message(chat_id, "Надішліть ключову фразу, яку потрібно видалити.", reply_markup=main_menu_for_chat(chat_id, db))
        return

    if text == BTN_INFO:
        send_info(chat_id, db, telegram, sources)
        return

    if text == BTN_CHECK:
        run_manual_check(chat_id, db, telegram, monitor)
        return

    if text == BTN_SOURCES:
        send_sources(chat_id, db, telegram, sources)
        return

    if text == BTN_SOURCE_LIST:
        send_sources(chat_id, db, telegram, sources)
        return

    if text == BTN_SOURCES_FILE:
        send_sources_file(chat_id, db, telegram, sources)
        return

    if text == BTN_TG_BLOCKS:
        send_tg_blocks(chat_id, db, telegram, sources)
        return

    block_action = parse_tg_block_button(text)
    if block_action:
        action, block_number = block_action
        set_tg_block(chat_id, block_number, action == "on", db, telegram, sources)
        return

    if text == BTN_SOURCE_ADD:
        PENDING_ACTIONS[chat_id] = "add_rss"
        telegram.send_message(
            chat_id,
            "Надішліть URL RSS-стрічки. Наприклад:\nhttps://example.com/rss.xml",
            reply_markup=SOURCE_MENU,
        )
        return

    if text == BTN_TG_ADD:
        PENDING_ACTIONS[chat_id] = "add_tg"
        telegram.send_message(
            chat_id,
            "Надішліть username або URL публічного Telegram-каналу. Наприклад:\n@channel\nhttps://t.me/channel",
            reply_markup=SOURCE_MENU,
        )
        return

    if text == BTN_SOURCE_DISABLE:
        PENDING_ACTIONS[chat_id] = "disable_rss"
        telegram.send_message(
            chat_id,
            "Надішліть номер стандартного джерела, яке потрібно вимкнути.\n\n"
            + format_sources(chat_id, db, sources),
            reply_markup=SOURCE_MENU,
        )
        return

    if text == BTN_SOURCE_ENABLE:
        PENDING_ACTIONS[chat_id] = "enable_rss"
        telegram.send_message(
            chat_id,
            "Надішліть номер стандартного джерела, яке потрібно увімкнути.\n\n"
            + format_sources(chat_id, db, sources),
            reply_markup=SOURCE_MENU,
        )
        return

    if text == BTN_SOURCE_REMOVE:
        PENDING_ACTIONS[chat_id] = "remove_rss"
        telegram.send_message(
            chat_id,
            "Надішліть номер власного RSS, який потрібно видалити.\n\n"
            + format_sources(chat_id, db, sources),
            reply_markup=SOURCE_MENU,
        )
        return

    if text == BTN_REPORT:
        send_report(chat_id, db, telegram)
        return

    if text == BTN_FILTERS:
        telegram.send_message(chat_id, "Налаштування фільтрів:", reply_markup=FILTER_MENU)
        return

    if text == BTN_TEXT_MODE:
        send_text_mode(chat_id, db, telegram)
        return

    if text == BTN_SETTINGS:
        send_settings(chat_id, db, telegram)
        return

    if text == BTN_FULL_TEXT_ON:
        plan = db.get_active_plan(chat_id)
        if not plan.full_text:
            telegram.send_message(
                chat_id,
                "Пошук у повному тексті доступний у тарифах Pro та Business.",
                reply_markup=main_menu_for_chat(chat_id, db),
            )
            return
        db.set_full_text_enabled(chat_id, True)
        telegram.send_message(
            chat_id,
            "Режим повного тексту увімкнено. Бот шукатиме ключі в заголовку, RSS-анонсі та тексті сторінки.",
            reply_markup=TEXT_MODE_MENU,
        )
        return

    if text == BTN_FULL_TEXT_OFF:
        db.set_full_text_enabled(chat_id, False)
        telegram.send_message(
            chat_id,
            "Швидкий режим увімкнено. Бот шукатиме ключі тільки в заголовку та RSS-анонсі.",
            reply_markup=TEXT_MODE_MENU,
        )
        return

    if text == BTN_HELP:
        send_help(chat_id, db, telegram)
        return

    if text == BTN_LANGUAGE:
        send_language_choice(chat_id, db, telegram)
        return

    if text == BTN_COUNTRY:
        send_country_choice(chat_id, db, telegram)
        return

    if text == BTN_BACK:
        telegram.send_message(chat_id, "Головне меню:", reply_markup=main_menu_for_chat(chat_id, db))
        return

    if text == BTN_STOP_ADD:
        PENDING_ACTIONS[chat_id] = "add_stop_word"
        telegram.send_message(chat_id, "Надішліть стоп-слово одним повідомленням.", reply_markup=FILTER_MENU)
        return

    if text == BTN_STOP_REMOVE:
        PENDING_ACTIONS[chat_id] = "remove_stop_word"
        telegram.send_message(chat_id, "Надішліть стоп-слово, яке потрібно видалити.", reply_markup=FILTER_MENU)
        return

    if text == BTN_PLUS_ADD:
        PENDING_ACTIONS[chat_id] = "add_plus_word"
        telegram.send_message(chat_id, "Надішліть плюс-слово одним повідомленням.", reply_markup=FILTER_MENU)
        return

    if text == BTN_PLUS_REMOVE:
        PENDING_ACTIONS[chat_id] = "remove_plus_word"
        telegram.send_message(chat_id, "Надішліть плюс-слово, яке потрібно видалити.", reply_markup=FILTER_MENU)
        return

    pending = PENDING_ACTIONS.pop(chat_id, None)
    if pending:
        handle_pending_value(chat_id, pending, text, db, telegram, sources)
        return

    telegram.send_message(
        chat_id,
        "Оберіть дію в меню або скористайтеся командою /help.",
        reply_markup=main_menu_for_chat(chat_id, db),
    )


def handle_command(chat_id: int, text: str, db: Database, telegram: TelegramApi, monitor: Monitor, sources) -> None:
    command, argument = split_command(text)

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
            telegram.send_message(chat_id, "Надішліть ключову фразу одним повідомленням.", reply_markup=main_menu_for_chat(chat_id, db))
            return
        if not can_add_keyword(chat_id, db, telegram):
            return
        added = db.add_keyword(chat_id, argument)
        telegram.send_message(chat_id, format_add_result("Ключову фразу", argument, added), reply_markup=main_menu_for_chat(chat_id, db))
        return

    if command == "/remove":
        if not argument:
            PENDING_ACTIONS[chat_id] = "remove_keyword"
            telegram.send_message(chat_id, "Надішліть ключову фразу, яку потрібно видалити.", reply_markup=main_menu_for_chat(chat_id, db))
            return
        removed = db.remove_keyword(chat_id, argument)
        telegram.send_message(chat_id, format_remove_result("Ключову фразу", argument, removed), reply_markup=main_menu_for_chat(chat_id, db))
        return

    if command == "/fulltext":
        handle_full_text_command(chat_id, argument, db, telegram)
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
            telegram.send_message(chat_id, "Надішліть стоп-слово одним повідомленням.", reply_markup=FILTER_MENU)
            return
        added = db.add_stop_word(chat_id, argument)
        telegram.send_message(chat_id, format_add_result("Стоп-слово", argument, added), reply_markup=FILTER_MENU)
        return

    if command == "/removestopword":
        if not argument:
            PENDING_ACTIONS[chat_id] = "remove_stop_word"
            telegram.send_message(chat_id, "Надішліть стоп-слово, яке потрібно видалити.", reply_markup=FILTER_MENU)
            return
        removed = db.remove_stop_word(chat_id, argument)
        telegram.send_message(chat_id, format_remove_result("Стоп-слово", argument, removed), reply_markup=FILTER_MENU)
        return

    if command == "/addplusword":
        if not argument:
            PENDING_ACTIONS[chat_id] = "add_plus_word"
            telegram.send_message(chat_id, "Надішліть плюс-слово одним повідомленням.", reply_markup=FILTER_MENU)
            return
        added = db.add_plus_word(chat_id, argument)
        telegram.send_message(chat_id, format_add_result("Плюс-слово", argument, added), reply_markup=FILTER_MENU)
        return

    if command == "/removeplusword":
        if not argument:
            PENDING_ACTIONS[chat_id] = "remove_plus_word"
            telegram.send_message(chat_id, "Надішліть плюс-слово, яке потрібно видалити.", reply_markup=FILTER_MENU)
            return
        removed = db.remove_plus_word(chat_id, argument)
        telegram.send_message(chat_id, format_remove_result("Плюс-слово", argument, removed), reply_markup=FILTER_MENU)
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

    telegram.send_message(chat_id, "Невідома команда.\n\n" + HELP, reply_markup=main_menu_for_chat(chat_id, db))


def handle_pending_value(
    chat_id: int,
    action: str,
    value: str,
    db: Database,
    telegram: TelegramApi,
    sources,
) -> None:
    if action == "add_keyword":
        if not can_add_keyword(chat_id, db, telegram):
            return
        added = db.add_keyword(chat_id, value)
        telegram.send_message(chat_id, format_add_result("Ключову фразу", value, added), reply_markup=main_menu_for_chat(chat_id, db))
        return

    if action == "remove_keyword":
        removed = db.remove_keyword(chat_id, value)
        telegram.send_message(chat_id, format_remove_result("Ключову фразу", value, removed), reply_markup=main_menu_for_chat(chat_id, db))
        return

    if action == "add_stop_word":
        added = db.add_stop_word(chat_id, value)
        telegram.send_message(chat_id, format_add_result("Стоп-слово", value, added), reply_markup=FILTER_MENU)
        return

    if action == "remove_stop_word":
        removed = db.remove_stop_word(chat_id, value)
        telegram.send_message(chat_id, format_remove_result("Стоп-слово", value, removed), reply_markup=FILTER_MENU)
        return

    if action == "add_plus_word":
        added = db.add_plus_word(chat_id, value)
        telegram.send_message(chat_id, format_add_result("Плюс-слово", value, added), reply_markup=FILTER_MENU)
        return

    if action == "remove_plus_word":
        removed = db.remove_plus_word(chat_id, value)
        telegram.send_message(chat_id, format_remove_result("Плюс-слово", value, removed), reply_markup=FILTER_MENU)
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
        "keyboard": [[{"text": language.button}] for language in LANGUAGES.values()],
        "resize_keyboard": True,
        "is_persistent": True,
    }


def country_menu() -> dict:
    return {
        "keyboard": [[{"text": country.button}] for country in COUNTRIES.values()],
        "resize_keyboard": True,
        "is_persistent": True,
    }


def send_language_choice(chat_id: int, db: Database, telegram: TelegramApi) -> None:
    settings = db.get_user_settings(chat_id)
    PENDING_ACTIONS[chat_id] = "set_language"
    telegram.send_message(
        chat_id,
        locale_text(settings.language_code, "choose_language"),
        reply_markup=language_menu(),
    )


def send_country_choice(chat_id: int, db: Database, telegram: TelegramApi) -> None:
    settings = db.get_user_settings(chat_id)
    PENDING_ACTIONS[chat_id] = "set_country"
    telegram.send_message(
        chat_id,
        locale_text(settings.language_code, "choose_country"),
        reply_markup=country_menu(),
    )


def send_settings(chat_id: int, db: Database, telegram: TelegramApi) -> None:
    settings = db.get_user_settings(chat_id)
    telegram.send_message(
        chat_id,
        (
            f"{locale_text(settings.language_code, 'settings')}:\n\n"
            f"{locale_text(settings.language_code, 'language')}: {escape(language_name(settings.language_code))}\n"
            f"{locale_text(settings.language_code, 'country')}: "
            f"{escape(country_name(settings.country_code, settings.language_code))}\n\n"
            f"{locale_text(settings.language_code, 'change_language')}: {BTN_LANGUAGE}\n"
            f"{locale_text(settings.language_code, 'change_country')}: {BTN_COUNTRY}"
        ),
        reply_markup=SETTINGS_MENU,
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
        reply_markup=SETTINGS_MENU if db.get_user_settings(chat_id).onboarding_completed else main_menu_for_chat(chat_id, db),
    )
    if REQUIRE_ONBOARDING and not db.get_user_settings(chat_id).onboarding_completed:
        send_country_choice(chat_id, db, telegram)


def handle_country_choice(chat_id: int, value: str, db: Database, telegram: TelegramApi) -> None:
    country_code = country_from_button(value) or value.strip().lower()
    settings = db.get_user_settings(chat_id)
    if country_code not in COUNTRIES:
        telegram.send_message(chat_id, locale_text(settings.language_code, "unknown_country"), reply_markup=country_menu())
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
        reply_markup=SETTINGS_MENU if was_completed else main_menu_for_chat(chat_id, db),
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
    if value in {"on", "увімкнути", "вкл"}:
        plan = db.get_active_plan(chat_id)
        if not plan.full_text:
            telegram.send_message(
                chat_id,
                "Пошук у повному тексті доступний у тарифах Pro та Business.",
                reply_markup=main_menu_for_chat(chat_id, db),
            )
            return
        db.set_full_text_enabled(chat_id, True)
        telegram.send_message(
            chat_id,
            "Режим повного тексту увімкнено.",
            reply_markup=TEXT_MODE_MENU,
        )
        return
    if value in {"off", "вимкнути", "викл"}:
        db.set_full_text_enabled(chat_id, False)
        telegram.send_message(
            chat_id,
            "Швидкий режим RSS-анонсу увімкнено.",
            reply_markup=TEXT_MODE_MENU,
        )
        return
    send_text_mode(chat_id, db, telegram)


def send_plans(chat_id: int, db: Database, telegram: TelegramApi) -> None:
    plan = db.get_active_plan(chat_id)
    subscription = db.get_subscription(chat_id)
    expires = subscription["expires_at"] if subscription and plan.id != "free" else "немає"
    lines = [
        "Тарифи Telegram Stars:",
        "",
        f"Поточний тариф: {plan.name}",
        f"Діє до: {expires}",
        "",
        plan_text(PLANS["free"]),
    ]
    for paid in paid_plans():
        lines.append(plan_text(paid))
        lines.append(f"Оплата: /buy {paid.id}")
    lines.append("")
    lines.append("Після оплати тариф активується автоматично на 30 днів.")
    telegram.send_message(
        chat_id,
        "\n".join(escape(line) for line in lines),
        disable_web_page_preview=True,
        reply_markup=main_menu_for_chat(chat_id, db),
    )


def send_plan_invoice(chat_id: int, plan_id: str, db: Database, telegram: TelegramApi) -> None:
    plan = plan_by_id(plan_id.strip())
    if plan.id == "free":
        telegram.send_message(chat_id, "Оберіть платний тариф: /buy basic, /buy pro або /buy business.", reply_markup=main_menu_for_chat(chat_id, db))
        return
    payload = f"plan:{plan.id}:{chat_id}:{int(time.time())}"
    telegram.send_invoice(
        chat_id=chat_id,
        title=f"Тариф {plan.name} на {plan.days} днів",
        description=plan.description,
        payload=payload,
        prices=[{"label": f"{plan.name} / {plan.days} днів", "amount": plan.stars}],
    )


def handle_pre_checkout_query(query: dict, telegram: TelegramApi) -> None:
    payload = str(query.get("invoice_payload") or "")
    plan_id = parse_plan_payload(payload)
    plan = plan_by_id(plan_id or "")
    if plan.id == "free":
        telegram.answer_pre_checkout_query(
            str(query["id"]),
            False,
            "Невідомий тариф. Спробуйте оформити оплату ще раз.",
        )
        return
    telegram.answer_pre_checkout_query(str(query["id"]), True)


def handle_successful_payment(chat_id: int, payment: dict, db: Database, telegram: TelegramApi) -> None:
    payload = str(payment.get("invoice_payload") or "")
    plan_id = parse_plan_payload(payload)
    plan = plan_by_id(plan_id or "")
    if plan.id == "free":
        telegram.send_message(chat_id, "Оплату отримано, але тариф не розпізнано. Напишіть адміністратору.", reply_markup=main_menu_for_chat(chat_id, db))
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
    status = "активовано" if recorded else "вже було активовано"
    telegram.send_message(
        chat_id,
        f"Оплату отримано. Тариф {escape(plan.name)} {status} до {escape(expires)}.",
        reply_markup=main_menu_for_chat(chat_id, db),
    )


def parse_plan_payload(payload: str) -> str | None:
    parts = payload.split(":")
    if len(parts) >= 2 and parts[0] == "plan":
        return parts[1]
    return None


def handle_grant_command(chat_id: int, argument: str, db: Database, telegram: TelegramApi) -> None:
    if chat_id not in ADMIN_CHAT_IDS:
        telegram.send_message(chat_id, "Ця команда доступна тільки адміністратору.", reply_markup=main_menu_for_chat(chat_id, db))
        return
    target_raw, _, rest = argument.strip().partition(" ")
    plan_raw, _, days_raw = rest.strip().partition(" ")
    try:
        target_chat_id = int(target_raw)
    except ValueError:
        telegram.send_message(chat_id, "Формат: /grant chat_id pro 30", reply_markup=main_menu_for_chat(chat_id, db))
        return
    plan = plan_by_id(plan_raw)
    if plan.id == "free":
        telegram.send_message(chat_id, "Формат: /grant chat_id basic|pro|business 30", reply_markup=main_menu_for_chat(chat_id, db))
        return
    try:
        days = int(days_raw) if days_raw else plan.days
    except ValueError:
        days = plan.days
    expires = db.activate_plan(target_chat_id, plan.id, days)
    telegram.send_message(chat_id, f"Видано {plan.name} для {target_chat_id} до {expires}.", reply_markup=main_menu_for_chat(chat_id, db))


def send_users(chat_id: int, db: Database, telegram: TelegramApi) -> None:
    if chat_id not in ADMIN_CHAT_IDS:
        telegram.send_message(chat_id, "Ця команда доступна тільки адміністратору.", reply_markup=main_menu_for_chat(chat_id, db))
        return
    total = db.user_count()
    users = db.list_users(limit=30)
    lines = [f"Користувачів у базі: {total}"]
    if len(users) < total:
        lines.append(f"Показано останніх активних: {len(users)}")
    lines.append("")
    if not users:
        lines.append("Користувачів ще немає.")
    for index, row in enumerate(users, start=1):
        user_chat_id = int(row["chat_id"])
        plan = db.get_active_plan(user_chat_id)
        expires = row["expires_at"] if plan.id != "free" and row["expires_at"] else "-"
        lines.extend(
            [
                f"{index}. ID: <code>{user_chat_id}</code>",
                f"   тариф: {escape(plan.name)}; ключів: {row['keyword_count']}; власних джерел: {row['custom_source_count']}",
                f"   остання активність: {escape(row['last_seen_at'])}",
                f"   діє до: {escape(expires)}",
            ]
        )
    telegram.send_message(chat_id, "\n".join(lines), reply_markup=main_menu_for_chat(chat_id, db))


def can_add_keyword(chat_id: int, db: Database, telegram: TelegramApi) -> bool:
    plan = db.get_active_plan(chat_id)
    current = len(db.get_user_monitoring(chat_id).keywords)
    if current >= plan.max_keywords:
        telegram.send_message(
            chat_id,
            f"Ліміт ключів для тарифу {escape(plan.name)}: {plan.max_keywords}. Оновіть тариф через /plans.",
            reply_markup=main_menu_for_chat(chat_id, db),
        )
        return False
    return True


def handle_rss_command(chat_id: int, argument: str, db: Database, telegram: TelegramApi, sources) -> None:
    action, _, rest = argument.strip().partition(" ")
    action = action.lower()

    if action in {"", "list", "список"}:
        send_sources(chat_id, db, telegram, sources)
        return

    if action == "add":
        if not rest.strip():
            telegram.send_message(
                chat_id,
                "Формат: /rss add https://example.com/rss.xml",
                reply_markup=SOURCE_MENU,
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
        "Невідома дія RSS.\n\n"
        "Доступно: /rss list, /rss add URL, /rss off номер, /rss on номер, /rss remove номер.",
        reply_markup=SOURCE_MENU,
    )


def handle_tg_command(chat_id: int, argument: str, db: Database, telegram: TelegramApi, sources) -> None:
    action, _, rest = argument.strip().partition(" ")
    action = action.lower()
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
                "Формат: /tg add @channel або /tg add https://t.me/channel",
                reply_markup=SOURCE_MENU,
            )
            return
        add_custom_telegram(chat_id, rest.strip(), db, telegram)
        return
    telegram.send_message(
        chat_id,
        "Доступно: /tg add @channel, /tg blocks, /tg off 1, /tg on 1",
        reply_markup=SOURCE_MENU,
    )


def handle_tg_blocks_command(chat_id: int, argument: str, db: Database, telegram: TelegramApi, sources) -> None:
    action, _, rest = argument.strip().partition(" ")
    action = action.lower()
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
        "Доступно: /tgblocks, /tgblocks off 1, /tgblocks on 1",
        reply_markup=tg_blocks_menu(country_sources(db.get_user_settings(chat_id).country_code, sources)),
    )


def send_tg_blocks(chat_id: int, db: Database, telegram: TelegramApi, sources) -> None:
    plan = db.get_active_plan(chat_id)
    if plan.id == "free":
        telegram.send_message(
            chat_id,
            "Пакети Telegram-каналів доступні тільки у платних тарифах. Оновіть тариф через /plans.",
            reply_markup=SOURCE_MENU,
        )
        return
    telegram.send_message(
        chat_id,
        format_tg_blocks(chat_id, db, sources),
        disable_web_page_preview=True,
        reply_markup=tg_blocks_menu(country_sources(db.get_user_settings(chat_id).country_code, sources)),
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
    if plan.id == "free":
        telegram.send_message(
            chat_id,
            "Пакети Telegram-каналів доступні тільки у платних тарифах. Оновіть тариф через /plans.",
            reply_markup=SOURCE_MENU,
        )
        return
    current_sources = country_sources(db.get_user_settings(chat_id).country_code, sources)
    blocks = tg_source_blocks(current_sources)
    if block_number < 1 or block_number > len(blocks):
        telegram.send_message(
            chat_id,
            "Надішліть номер пакета: 1, 2, 3... або відкрийте /tgblocks.",
            reply_markup=tg_blocks_menu(current_sources),
        )
        return
    block = blocks[block_number - 1]
    urls = [source.url for source in block]
    changed = db.enable_sources(chat_id, urls) if enabled else db.disable_sources(chat_id, urls)
    action = "увімкнено" if enabled else "вимкнено"
    telegram.send_message(
        chat_id,
        f"TG-пакет {tg_block_title(block_number, block)} {action}. Змінено джерел: {changed}.\n\n"
        + format_tg_blocks(chat_id, db, sources),
        disable_web_page_preview=True,
        reply_markup=tg_blocks_menu(current_sources),
    )


def format_tg_blocks(chat_id: int, db: Database, sources) -> str:
    monitoring = db.get_user_monitoring(chat_id)
    disabled = set(monitoring.disabled_source_urls)
    blocks = tg_source_blocks(country_sources(db.get_user_settings(chat_id).country_code, sources))
    if not blocks:
        return "Платні Telegram-джерела ще не додані."
    lines = ["Платні Telegram-пакети:", ""]
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
        lines.append(f"{index}. {status} {tg_block_title(index, block)}: {active}/{len(block)} активні")
    lines.extend(
        [
            "",
            f"Разом: {total_active}/{total_sources} активні.",
            "Кнопки нижче вимикають або вмикають весь пакет.",
            "Команди: /tgblocks off 1, /tgblocks on 1.",
        ]
    )
    return "\n".join(lines)


def tg_blocks_menu(sources) -> dict:
    rows = []
    for index, block in enumerate(tg_source_blocks(sources), start=1):
        label = tg_block_range(index, block)
        rows.append([{"text": f"⛔ TG {label}"}, {"text": f"✅ TG {label}"}])
    rows.append([{"text": BTN_SOURCE_LIST}, {"text": BTN_BACK}])
    return {"keyboard": rows, "resize_keyboard": True, "is_persistent": True}


def tg_source_blocks(sources) -> list[list[Source]]:
    paid_sources = [source for source in sources if source.type == "telegram_paid"]
    return [
        paid_sources[index : index + TG_BLOCK_SIZE]
        for index in range(0, len(paid_sources), TG_BLOCK_SIZE)
    ]


def country_sources(country_code: str, sources) -> list[Source]:
    return [source for source in sources if source.country == country_code]


def tg_block_title(block_number: int, block: list[Source]) -> str:
    start = (block_number - 1) * TG_BLOCK_SIZE + 1
    end = start + len(block) - 1
    if block_number == 1:
        return f"Топ 50 ({start}-{end})"
    return f"Топ {end} ({start}-{end})"


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
    plan = db.get_active_plan(chat_id)
    custom_count = len(db.get_user_monitoring(chat_id).custom_sources)
    if custom_count >= plan.max_custom_sources:
        telegram.send_message(
            chat_id,
            f"Ліміт власних RSS для тарифу {escape(plan.name)}: {plan.max_custom_sources}. Оновіть тариф через /plans.",
            reply_markup=SOURCE_MENU,
        )
        return

    url, name = parse_rss_add_value(value)
    if not valid_http_url(url):
        telegram.send_message(
            chat_id,
            "Надішліть коректний URL RSS-стрічки, який починається з http:// або https://.",
            reply_markup=SOURCE_MENU,
        )
        return

    source = Source(name or source_name_from_url(url), url, "rss", country=db.get_user_settings(chat_id).country_code)
    try:
        articles = fetch_rss(source, 20)
    except Exception:
        telegram.send_message(
            chat_id,
            "Не вдалося прочитати цю RSS-стрічку. Перевірте URL і спробуйте ще раз.",
            reply_markup=SOURCE_MENU,
        )
        return

    if not articles:
        telegram.send_message(
            chat_id,
            "RSS-стрічка відкрилася, але бот не знайшов у ній новин. Таке джерело не додано.",
            reply_markup=SOURCE_MENU,
        )
        return

    added = db.add_user_source(chat_id, source)
    telegram.send_message(
        chat_id,
        f"{'Власне RSS-джерело додано' if added else 'Таке RSS-джерело вже є'}: {escape(source.name)}\n{escape(source.url)}",
        disable_web_page_preview=True,
        reply_markup=SOURCE_MENU,
    )


def add_custom_telegram(chat_id: int, value: str, db: Database, telegram: TelegramApi) -> None:
    plan = db.get_active_plan(chat_id)
    custom_count = len(db.get_user_monitoring(chat_id).custom_sources)
    if custom_count >= plan.max_custom_sources:
        telegram.send_message(
            chat_id,
            f"Ліміт власних джерел для тарифу {escape(plan.name)}: {plan.max_custom_sources}. Оновіть тариф через /plans.",
            reply_markup=SOURCE_MENU,
        )
        return

    url, name = parse_telegram_add_value(value)
    if not url:
        telegram.send_message(
            chat_id,
            "Надішліть username або URL публічного Telegram-каналу. Наприклад: @channel",
            reply_markup=SOURCE_MENU,
        )
        return

    source = Source(name or source_name_from_url(url), url, "telegram", country=db.get_user_settings(chat_id).country_code)
    try:
        articles = fetch_telegram_channel(source, 20)
    except Exception:
        telegram.send_message(
            chat_id,
            "Не вдалося прочитати цей Telegram-канал. Перевірте, що канал публічний і доступний через t.me/s/.",
            reply_markup=SOURCE_MENU,
        )
        return

    if not articles:
        telegram.send_message(
            chat_id,
            "Канал відкрився, але бот не знайшов доступних постів. Джерело не додано.",
            reply_markup=SOURCE_MENU,
        )
        return

    added = db.add_user_source(chat_id, source)
    telegram.send_message(
        chat_id,
        f"{'Telegram-канал додано' if added else 'Такий Telegram-канал уже є'}: {escape(source.name)}\n{escape(source.url)}",
        disable_web_page_preview=True,
        reply_markup=SOURCE_MENU,
    )


def disable_rss_by_number(chat_id: int, value: str, db: Database, telegram: TelegramApi, sources) -> None:
    row = find_source_row(chat_id, value, db, sources)
    if row is None:
        telegram.send_message(chat_id, "Надішліть номер зі списку, @username або URL джерела.\n\n" + format_sources(chat_id, db, sources), reply_markup=SOURCE_MENU)
        return
    if row["custom"]:
        telegram.send_message(chat_id, "Власні джерела не вимикаються. Їх можна видалити через «🗑️ Видалити моє джерело».", reply_markup=SOURCE_MENU)
        return
    if not row["enabled"]:
        telegram.send_message(chat_id, "Це джерело вже вимкнене.", reply_markup=SOURCE_MENU)
        return
    db.disable_source(chat_id, row["source"].url)
    telegram.send_message(chat_id, f"Джерело вимкнено: {escape(row['source'].name)}", reply_markup=SOURCE_MENU)


def enable_rss_by_number(chat_id: int, value: str, db: Database, telegram: TelegramApi, sources) -> None:
    row = find_source_row(chat_id, value, db, sources)
    if row is None:
        telegram.send_message(chat_id, "Надішліть номер зі списку, @username або URL джерела.\n\n" + format_sources(chat_id, db, sources), reply_markup=SOURCE_MENU)
        return
    if row["custom"]:
        telegram.send_message(chat_id, "Власні джерела вже активні. Якщо джерело не потрібне, видаліть його.", reply_markup=SOURCE_MENU)
        return
    if row["enabled"]:
        telegram.send_message(chat_id, "Це джерело вже увімкнене.", reply_markup=SOURCE_MENU)
        return
    db.enable_source(chat_id, row["source"].url)
    telegram.send_message(chat_id, f"Джерело увімкнено: {escape(row['source'].name)}", reply_markup=SOURCE_MENU)


def remove_custom_rss_by_number(chat_id: int, value: str, db: Database, telegram: TelegramApi, sources) -> None:
    row = find_source_row(chat_id, value, db, sources)
    if row is None:
        telegram.send_message(chat_id, "Надішліть номер власного джерела зі списку, @username або URL.\n\n" + format_sources(chat_id, db, sources), reply_markup=SOURCE_MENU)
        return
    if not row["custom"]:
        telegram.send_message(chat_id, "Стандартні RSS не видаляються. Їх можна вимкнути.", reply_markup=SOURCE_MENU)
        return
    removed = db.remove_user_source(chat_id, row["source"].url)
    telegram.send_message(chat_id, f"{'Власне джерело видалено' if removed else 'Джерело не знайдено'}: {escape(row['source'].name)}", reply_markup=SOURCE_MENU)


def send_help(chat_id: int, db: Database, telegram: TelegramApi) -> None:
    telegram.send_message(
        chat_id,
        "Це бот моніторингу українських онлайн-медіа за ключовими словами.\n\n"
        "Автоматичний моніторинг працює за тарифом: Free раз на годину, Basic/Pro кожні 30 хвилин, Business кожні 5 хвилин. "
        "Додайте ключові фрази, і бот надсилатиме знайдені згадки.\n\n"
        + HELP,
        disable_web_page_preview=True,
        reply_markup=main_menu_for_chat(chat_id, db),
    )


def send_info(chat_id: int, db: Database, telegram: TelegramApi, sources) -> None:
    monitoring = db.get_user_monitoring(chat_id)
    settings = db.get_user_settings(chat_id)
    plan = db.get_active_plan(chat_id)
    text_mode = "повний текст новини" if monitoring.full_text_enabled else "заголовок + RSS-анонс"
    active_sources = len(db.get_enabled_sources(chat_id, sources))
    telegram.send_message(
        chat_id,
        "Мій моніторинг:\n\n"
        f"{locale_text(settings.language_code, 'language')}: {escape(language_name(settings.language_code))}\n"
        f"{locale_text(settings.language_code, 'country')}: {escape(country_name(settings.country_code, settings.language_code))}\n\n"
        f"Ключові фрази: {format_terms(monitoring.keywords)}\n"
        f"Стоп-слова: {format_terms(monitoring.stop_words)}\n"
        f"Плюс-слова: {format_terms(monitoring.plus_words)}\n\n"
        f"Режим пошуку: {text_mode}\n"
        f"Активні джерела: {active_sources}\n"
        f"Автоматична перевірка: {monitor_interval_text(plan.id)}.",
        disable_web_page_preview=True,
        reply_markup=main_menu_for_chat(chat_id, db),
    )


def monitor_interval_text(plan_id: str) -> str:
    if plan_id == "business":
        return "кожні 5 хвилин"
    if plan_id in {"basic", "pro"}:
        return "кожні 30 хвилин"
    return "раз на годину"


def send_text_mode(chat_id: int, db: Database, telegram: TelegramApi) -> None:
    monitoring = db.get_user_monitoring(chat_id)
    current = "повний текст новини" if monitoring.full_text_enabled else "заголовок + RSS-анонс"
    telegram.send_message(
        chat_id,
        "Режим пошуку визначає, де бот шукає ваші ключові слова.\n\n"
        f"Поточний режим: {current}\n\n"
        "Повний текст точніший, але перевірка триває довше і залежить від доступності сайту.",
        reply_markup=TEXT_MODE_MENU,
    )


def send_sources(chat_id: int, db: Database, telegram: TelegramApi, sources) -> None:
    telegram.send_message(
        chat_id,
        format_sources(chat_id, db, sources),
        disable_web_page_preview=True,
        reply_markup=SOURCE_MENU,
    )


def send_sources_file(chat_id: int, db: Database, telegram: TelegramApi, sources) -> None:
    path = write_sources_table(chat_id, db, sources, Path("reports"))
    telegram.send_document(chat_id, path, "Таблиця джерел: номери, TG-рейтинг, підписники і команди вимкнення")


def write_sources_table(chat_id: int, db: Database, sources, output_dir: Path) -> Path:
    output_dir.mkdir(parents=True, exist_ok=True)
    path = output_dir / f"media-monitor-sources-{chat_id}.csv"
    rows = source_rows(chat_id, db, sources)
    visible_number_by_url = visible_source_numbers(rows)
    disabled_rows = [row for row in rows if not row["enabled"]]
    with path.open("w", encoding="utf-8-sig", newline="") as fh:
        writer = csv.writer(fh)
        writer.writerow(
            [
                "номер_у_списку",
                "tg_топ",
                "tg_пакет",
                "статус",
                "доступ",
                "країна",
                "мова",
                "тип",
                "назва",
                "username",
                "підписники",
                "url",
                "команда_вимкнути",
                "команда_увімкнути",
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
                    "увімкнено" if row["enabled"] else "вимкнено",
                    "власне" if row["custom"] else "стандартне",
                    source.country,
                    source.language,
                    source.type,
                    source.name,
                    f"@{username}" if username else "",
                    source.subscribers or "",
                    source.url,
                    f"/rss off {lookup}".strip(),
                    f"/rss on {lookup}".strip(),
                ]
            )
        if disabled_rows:
            writer.writerow([])
            writer.writerow(["Вимкнені джерела"])
            for row in disabled_rows:
                writer.writerow([row["source"].name, row["source"].url])
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
    rows = source_rows(chat_id, db, sources)
    active_count = sum(1 for row in rows if row["enabled"])
    paid_tg_rows = [row for row in rows if row["source"].type == "telegram_paid"]
    visible_rows = [row for row in rows if row["source"].type != "telegram_paid"]
    lines = [
        f"Джерела: {active_count} активних із {len(rows)}",
        "",
    ]
    for display_number, row in enumerate(visible_rows, start=1):
        status = "✅" if row["enabled"] else "⛔"
        kind = "власне" if row["custom"] else "стандартне"
        source = row["source"]
        lines.append(f"{display_number}. {status} {escape(source.name)} ({kind}, {escape(source.type)})")
        lines.append(f"   {escape(source.url)}")
    if paid_tg_rows:
        paid_active = sum(1 for row in paid_tg_rows if row["enabled"])
        lines.extend(
            [
                "",
                f"Платні Telegram-канали: {paid_active}/{len(paid_tg_rows)} активні.",
                "Керуйте ними блоками по 50 через кнопку «TG-пакети» або команду /tgblocks.",
            ]
        )
    lines.append("")
    lines.append("Команди: /rss off номер, /rss on номер, /rss add URL, /rss remove номер")
    return "\n".join(lines)


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
    return parsed.netloc or "Моє джерело"


def run_manual_check(chat_id: int, db: Database, telegram: TelegramApi, monitor: Monitor) -> None:
    telegram.send_message(chat_id, "Починаю ручну перевірку джерел.", reply_markup=main_menu_for_chat(chat_id, db))
    sent = run_monitor_safely(monitor, {chat_id}, wait_seconds=MANUAL_CHECK_WAIT_SECONDS)
    if sent is None:
        telegram.send_message(
            chat_id,
            "Фонова перевірка ще триває довше хвилини. Спробуйте /check трохи пізніше.",
            reply_markup=main_menu_for_chat(chat_id, db),
        )
        return
    telegram.send_message(
        chat_id,
        f"Перевірку завершено. Нових сповіщень надіслано: {sent}",
        reply_markup=main_menu_for_chat(chat_id, db),
    )


def send_report(chat_id: int, db: Database, telegram: TelegramApi) -> None:
    path = write_csv_report(db, chat_id, Path("reports"))
    telegram.send_document(chat_id, path, "CSV-звіт за знайденими згадками")


def split_command(text: str) -> tuple[str, str]:
    first, _, rest = text.strip().partition(" ")
    command = first.split("@", 1)[0].lower()
    return command, rest.strip()


def format_terms(values: tuple[str, ...]) -> str:
    if not values:
        return "немає"
    return ", ".join(escape(value) for value in values)


def format_add_result(label: str, value: str, added: bool) -> str:
    status = "додано" if added else "вже є"
    return f"{label} {status}: {escape(value)}"


def format_remove_result(label: str, value: str, removed: bool) -> str:
    status = "видалено" if removed else "не знайдено"
    return f"{label} {status}: {escape(value)}"


if __name__ == "__main__":
    raise SystemExit(main())

