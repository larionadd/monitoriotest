from __future__ import annotations

from datetime import datetime, timedelta, timezone
from email.utils import parsedate_to_datetime
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError


try:
    DISPLAY_TIMEZONE = ZoneInfo("Europe/Kyiv")
except ZoneInfoNotFoundError:
    DISPLAY_TIMEZONE = timezone(timedelta(hours=2))


def parse_datetime_value(value: str | None) -> datetime | None:
    raw = (value or "").strip()
    if not raw:
        return None

    iso_value = raw.replace("Z", "+00:00")
    try:
        parsed = datetime.fromisoformat(iso_value)
    except ValueError:
        try:
            parsed = parsedate_to_datetime(raw)
        except (TypeError, ValueError, IndexError, OverflowError):
            return None

    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed


def display_date_time(value: str | None) -> tuple[str, str]:
    parsed = parse_datetime_value(value)
    if parsed is None:
        raw = (value or "").strip()
        return (raw or "-", "-")

    local_dt = parsed.astimezone(DISPLAY_TIMEZONE)
    return local_dt.strftime("%d.%m.%Y"), local_dt.strftime("%H:%M")


def display_datetime_line(value: str | None) -> str:
    date_value, time_value = display_date_time(value)
    if time_value == "-":
        return date_value
    return f"📅 {date_value}  🕒 {time_value}"
