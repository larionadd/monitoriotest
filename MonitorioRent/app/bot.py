from __future__ import annotations

import asyncio
import os
from pathlib import Path

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update, WebAppInfo
from telegram.ext import Application, CommandHandler, ContextTypes

from .db import Database
from .sources import ListingSourceSync


BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "").strip()
MINI_APP_URL = os.getenv("MONITORIO_RENT_MINI_APP_URL", "").strip()
ROOT = Path(__file__).resolve().parents[1]
DATABASE_PATH = Path(os.getenv("MONITORIO_RENT_DATABASE", ROOT / "data" / "monitorio_rent.sqlite3"))
MONITOR_INTERVAL_SECONDS = max(1800, int(os.getenv("MONITORIO_RENT_MONITOR_INTERVAL", "1800")))
MAX_INITIAL_NOTIFICATIONS = 10
database = Database(DATABASE_PATH)
source_sync = ListingSourceSync(database)


def cabinet_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        [[InlineKeyboardButton("Відкрити кабінет", web_app=WebAppInfo(url=MINI_APP_URL))]]
    )


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not update.effective_message:
        return
    await update.effective_message.reply_text(
        "Вітаємо в MonitorioRent. Тут можна шукати або здавати квартири в Україні. "
        "Перше питання в кабінеті — орендуєте ви квартиру чи здаєте її.",
        reply_markup=cabinet_keyboard(),
    )


async def cabinet(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not update.effective_message:
        return
    await update.effective_message.reply_text(
        "Відкрийте кабінет MonitorioRent:",
        reply_markup=cabinet_keyboard(),
    )


def listing_caption(listing: dict) -> str:
    details = []
    if listing.get("rooms"):
        details.append(f"{listing['rooms']}-кімнатна")
    if listing.get("area_sqm"):
        details.append(f"{listing['area_sqm']:g} м²")
    title = " · ".join(details) or "Квартира в оренду"
    price = (
        f"{listing['price_uah']:,} грн/місяць".replace(",", " ")
        if listing.get("price_uah")
        else listing.get("price_original", "Ціна в оголошенні")
    )
    location = ", ".join(filter(None, (listing.get("city"), listing.get("district"), listing.get("address"))))
    source = listing.get("source_title") or "MonitorioRent"
    return f"🏠 {title}\n📍 {location}\n💰 {price}\nДжерело: {source}"[:1024]


async def send_listing(application: Application, chat_id: int, listing: dict) -> bool:
    source_url = listing.get("source_url") or MINI_APP_URL
    markup = InlineKeyboardMarkup(
        [[InlineKeyboardButton("Відкрити оголошення", url=source_url)]]
    )
    caption = listing_caption(listing)
    photo = next(iter(listing.get("photos") or []), None)
    try:
        if photo:
            await application.bot.send_photo(
                chat_id=chat_id, photo=photo, caption=caption, reply_markup=markup
            )
        else:
            await application.bot.send_message(chat_id=chat_id, text=caption, reply_markup=markup)
        return True
    except Exception:
        try:
            await application.bot.send_message(chat_id=chat_id, text=caption, reply_markup=markup)
            return True
        except Exception:
            return False


async def process_searches(context: ContextTypes.DEFAULT_TYPE, *, initial_only: bool) -> None:
    for search in database.list_active_searches():
        try:
            chat_id = int(search["user_id"])
        except (TypeError, ValueError):
            continue
        state = database.search_monitor_state(search["id"])
        initial = not bool(state.get("initial_report_sent"))
        if initial_only and not initial:
            continue
        matches = database.matches_for_search(search, only_unsent=not initial, limit=100)

        if initial:
            if matches:
                await context.application.bot.send_message(
                    chat_id=chat_id,
                    text=(
                        f"🔎 За вашим пошуком знайдено {len(matches)} свіжих оголошень "
                        f"за останні {search.get('lookback_days', 3)} дн. "
                        f"Показую до {MAX_INITIAL_NOTIFICATIONS}; далі перевірятиму нові кожні 30 хвилин."
                    ),
                    reply_markup=cabinet_keyboard(),
                )
                for listing in matches[:MAX_INITIAL_NOTIFICATIONS]:
                    await send_listing(context.application, chat_id, listing)
                for listing in matches:
                    database.mark_notification_sent(search["id"], listing["id"])
            else:
                alternatives = (
                    database.similar_matches_for_search(search, limit=5)
                    if search.get("district")
                    else []
                )
                if alternatives:
                    await context.application.bot.send_message(
                        chat_id=chat_id,
                        text=(
                            f"У районі «{search['district']}» точних збігів поки немає. "
                            f"Показую {len(alternatives)} схожих варіантів у місті {search['city']} "
                            "за вашим бюджетом і кількістю кімнат. Точний район продовжую моніторити."
                        ),
                        reply_markup=cabinet_keyboard(),
                    )
                    for listing in alternatives:
                        await send_listing(context.application, chat_id, listing)
                else:
                    await context.application.bot.send_message(
                        chat_id=chat_id,
                        text=(
                            "За вашими критеріями свіжих оголошень поки немає. "
                            "Моніторинг активний — повідомлю, щойно з’явиться відповідний варіант."
                        ),
                        reply_markup=cabinet_keyboard(),
                    )
            database.mark_search_checked(search["id"])
            continue

        for listing in matches:
            if await send_listing(context.application, chat_id, listing):
                database.mark_notification_sent(search["id"], listing["id"])
        database.mark_search_checked(search["id"])


async def report_new_searches(context: ContextTypes.DEFAULT_TYPE) -> None:
    await process_searches(context, initial_only=True)


async def monitor_searches(context: ContextTypes.DEFAULT_TYPE) -> None:
    await asyncio.to_thread(source_sync.sync_all)
    await process_searches(context, initial_only=False)


async def searches(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not update.effective_message or not update.effective_user:
        return
    items = database.list_searches(str(update.effective_user.id))
    if not items:
        await update.effective_message.reply_text("У вас ще немає активних пошуків.", reply_markup=cabinet_keyboard())
        return
    lines = ["Ваші активні пошуки:"]
    for item in items:
        lines.append(
            f"• {item['city']}{', ' + item['district'] if item['district'] else ''} · "
            f"до {item['price_max']} грн · {item['rooms_min']}–{item['rooms_max']} кімн. · "
            f"за {item.get('lookback_days', 3)} дн."
        )
    await update.effective_message.reply_text("\n".join(lines), reply_markup=cabinet_keyboard())


def main() -> None:
    if not BOT_TOKEN:
        raise RuntimeError("TELEGRAM_BOT_TOKEN is required")
    if not MINI_APP_URL.startswith("https://"):
        raise RuntimeError("MONITORIO_RENT_MINI_APP_URL must be a public HTTPS URL")
    application = Application.builder().token(BOT_TOKEN).build()
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("cabinet", cabinet))
    application.add_handler(CommandHandler("searches", searches))
    if application.job_queue is None:
        raise RuntimeError("Install python-telegram-bot[job-queue] to enable monitoring")
    application.job_queue.run_repeating(
        monitor_searches,
        interval=MONITOR_INTERVAL_SECONDS,
        first=10,
        name="rent-search-monitor",
    )
    application.job_queue.run_repeating(
        report_new_searches,
        interval=15,
        first=3,
        name="new-search-reporter",
    )
    application.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
