from __future__ import annotations

import asyncio
import logging

from telegram import Bot

from app import db, uz
from app.config import settings


logger = logging.getLogger(__name__)


def _notification_text(watch: dict, result: dict) -> str:
    route = f"{watch['origin_station']} -> {watch['destination_station']}"
    train_line = f"\nПотяг: {watch['train_number']}" if watch.get("train_number") else ""
    return (
        "З'явився квиток УЗ.\n\n"
        f"{route}\n"
        f"Дата: {watch['travel_date']}{train_line}\n"
        f"{result['status']}\n\n"
        f"Відкрити УЗ: {result['search_url']}"
    )


async def check_once() -> int:
    bot = Bot(settings.telegram_bot_token) if settings.telegram_bot_token else None
    sent = 0
    for watch in db.list_rail_watches(active_only=True):
        previous_available = bool(watch.get("last_available"))
        result = await asyncio.to_thread(uz.check_availability, watch)
        db.update_rail_watch_check(
            watch["id"],
            available=bool(result["available"]),
            status=result["status"],
            error=result["error"],
            origin_station_id=result.get("origin_station_id"),
            destination_station_id=result.get("destination_station_id"),
        )
        if bot and result["available"] and not previous_available:
            await bot.send_message(chat_id=watch["chat_id"], text=_notification_text(watch, result))
            sent += 1
    return sent


async def run_monitor_loop() -> None:
    interval = max(60, settings.rail_monitor_interval_seconds)
    while True:
        try:
            await check_once()
        except Exception:
            logger.exception("Rail monitor check failed")
        await asyncio.sleep(interval)


def main() -> None:
    db.init_db()
    logging.basicConfig(level=logging.INFO)
    asyncio.run(run_monitor_loop())


if __name__ == "__main__":
    main()
