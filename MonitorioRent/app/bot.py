from __future__ import annotations

import os

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update, WebAppInfo
from telegram.ext import Application, CommandHandler, ContextTypes


BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "").strip()
MINI_APP_URL = os.getenv("MONITORIO_RENT_MINI_APP_URL", "").strip()


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


def main() -> None:
    if not BOT_TOKEN:
        raise RuntimeError("TELEGRAM_BOT_TOKEN is required")
    if not MINI_APP_URL.startswith("https://"):
        raise RuntimeError("MONITORIO_RENT_MINI_APP_URL must be a public HTTPS URL")
    application = Application.builder().token(BOT_TOKEN).build()
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("cabinet", cabinet))
    application.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
