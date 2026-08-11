from __future__ import annotations

from telegram import (
    KeyboardButton,
    MenuButtonWebApp,
    ReplyKeyboardMarkup,
    Update,
    WebAppInfo,
)
from telegram.ext import Application, CommandHandler, ContextTypes, MessageHandler, filters

from app import db
from app.config import settings


BTN_CABINET = "Кабінет"


def cabinet_keyboard() -> ReplyKeyboardMarkup:
    if settings.mini_app_url.startswith("https://"):
        button = KeyboardButton(BTN_CABINET, web_app=WebAppInfo(settings.mini_app_url))
    else:
        button = KeyboardButton(BTN_CABINET)
    return ReplyKeyboardMarkup(
        [[button]],
        resize_keyboard=True,
        input_field_placeholder="Відкрити кабінет",
    )


async def ensure_user(update: Update) -> None:
    user = update.effective_user
    if user:
        db.create_or_touch_user(user.id, user.username, user.first_name)


async def show_cabinet_button(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await ensure_user(update)
    if settings.mini_app_url.startswith("https://"):
        text = "Відкрийте кабінет у Mini App."
    else:
        text = (
            "Кнопка кабінету готова, але Mini App URL ще не налаштований.\n"
            "Потрібен публічний HTTPS у MINI_APP_URL."
        )
    await update.message.reply_text(text, reply_markup=cabinet_keyboard())


async def text_router(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await ensure_user(update)
    await show_cabinet_button(update, context)


async def install_bot_ui(application: Application) -> None:
    await application.bot.delete_my_commands()
    if settings.mini_app_url.startswith("https://"):
        await application.bot.set_chat_menu_button(
            menu_button=MenuButtonWebApp(BTN_CABINET, WebAppInfo(settings.mini_app_url))
        )


def add_handlers(application: Application) -> None:
    application.add_handler(CommandHandler("start", show_cabinet_button))
    application.add_handler(CommandHandler("cabinet", show_cabinet_button))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, text_router))


async def run_bot_async() -> None:
    if not settings.telegram_bot_token:
        raise SystemExit("TELEGRAM_BOT_TOKEN is missing in .env")

    db.init_db()
    application = Application.builder().token(settings.telegram_bot_token).build()
    add_handlers(application)
    await application.initialize()
    await install_bot_ui(application)
    await application.start()
    await application.updater.start_polling()


def main() -> None:
    if not settings.telegram_bot_token:
        raise SystemExit("TELEGRAM_BOT_TOKEN is missing in .env")
    db.init_db()
    application = Application.builder().token(settings.telegram_bot_token).build()
    add_handlers(application)
    application.post_init = install_bot_ui
    application.run_polling()


if __name__ == "__main__":
    main()
