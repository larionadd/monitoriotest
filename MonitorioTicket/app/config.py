import os
from dataclasses import dataclass

from dotenv import load_dotenv


load_dotenv()


@dataclass(frozen=True)
class Settings:
    app_name: str = os.getenv("APP_NAME", "TicketPing")
    app_host: str = os.getenv("APP_HOST", "127.0.0.1")
    app_port: int = int(os.getenv("APP_PORT", "8017"))
    database_path: str = os.getenv("DATABASE_PATH", "ticketping.sqlite3")
    telegram_bot_token: str = os.getenv("TELEGRAM_BOT_TOKEN", "")
    telegram_admin_ids: tuple[int, ...] = tuple(
        int(value.strip())
        for value in os.getenv("TELEGRAM_ADMIN_IDS", "").split(",")
        if value.strip().isdigit()
    )
    mini_app_url: str = os.getenv("MINI_APP_URL", "")
    run_telegram_bot: bool = os.getenv("RUN_TELEGRAM_BOT", "false").lower() == "true"
    travelpayouts_token: str = os.getenv("TRAVELPAYOUTS_TOKEN", "")
    travelpayouts_marker: str = os.getenv("TRAVELPAYOUTS_MARKER", "")
    skyscanner_api_key: str = os.getenv("SKYSCANNER_API_KEY", "")
    kiwi_tequila_api_key: str = os.getenv("KIWI_TEQUILA_API_KEY", "")
    uz_booking_base: str = os.getenv("UZ_BOOKING_BASE", "https://app.uz.gov.ua")
    run_rail_monitor: bool = os.getenv("RUN_RAIL_MONITOR", "false").lower() == "true"
    rail_monitor_interval_seconds: int = int(os.getenv("RAIL_MONITOR_INTERVAL_SECONDS", "600"))


settings = Settings()
