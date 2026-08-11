from __future__ import annotations

import os
import re
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from typing import Any

import httpx
from bs4 import BeautifulSoup

from .db import Database


@dataclass(frozen=True)
class TelegramSource:
    channel: str
    title: str
    city: str
    default_commission_pct: int = 0

    @property
    def preview_url(self) -> str:
        return f"https://t.me/s/{self.channel}"


# Public, active city channels selected by current audience size and listing activity.
TELEGRAM_SOURCES = (
    TelegramSource("orendakvartyr_ua", "Оренда від Віктора", "Львів"),
    TelegramSource("x_arenda_kharkov", "Оренда квартир Харків · X-Estate", "Харків", 50),
    TelegramSource("x_arenda_kyiv", "Оренда квартир Київ · X-Estate", "Київ", 50),
    TelegramSource("arenda_hata", "Оренда квартир Харків · Arenda_hata", "Харків", 50),
    TelegramSource("orenda_kvatir", "Оренда квартир Київ", "Київ"),
    TelegramSource("lviv_no_maklers", "Оренда від власників у Львові", "Львів"),
    TelegramSource("x_orenda_dnipro", "Оренда квартир Дніпро · X-Estate", "Дніпро", 50),
    TelegramSource("orenda_kvartir_kyiv", "Оренда квартир Київ", "Київ", 40),
    TelegramSource("OrendakvartyrKyiv_UK", "Оренда квартир Київ · власники", "Київ"),
    TelegramSource("x_orenda_odesa", "Оренда квартир Одеса · X-Estate", "Одеса", 50),
)


def _number(value: str) -> float:
    normalized = value.replace(" ", "").replace("\u00a0", "").replace(",", ".")
    return float(normalized)


def _first_match(patterns: tuple[str, ...], text: str, flags: int = re.IGNORECASE) -> re.Match[str] | None:
    for pattern in patterns:
        match = re.search(pattern, text, flags)
        if match:
            return match
    return None


def parse_listing_text(text: str, source: TelegramSource) -> dict[str, Any] | None:
    compact = "\n".join(line.strip() for line in text.splitlines() if line.strip())
    lowered = compact.lower()
    if len(compact) < 20:
        return None
    if re.search(r"\bшукаю\b|\bсниму\b|\bищу\b", lowered) and not re.search(
        r"\bзда(ю|ється|м)\b|\bсда(ю|ётся|м)\b", lowered
    ):
        return None

    price_match = _first_match(
        (
            r"(?:💵|💳|ціна|вартість|оренда|цена|стоимость)\s*[:\-]?\s*(\d[\d\s.,]{2,})\s*(грн|грив(?:ень|ні)?|₴|\$|usd|дол(?:арів|ларів)?)?",
            r"(\d[\d\s.,]{2,})\s*(грн|грив(?:ень|ні)?|₴|\$|usd|дол(?:арів|ларів)?)",
        ),
        compact,
    )
    if not price_match:
        return None
    try:
        raw_price = _number(price_match.group(1))
    except ValueError:
        return None
    currency_token = (price_match.group(2) or "грн").lower()
    currency = "USD" if "$" in currency_token or "usd" in currency_token or "дол" in currency_token else "UAH"
    price_uah = int(raw_price) if currency == "UAH" else 0
    usd_rate = float(os.getenv("MONITORIO_RENT_USD_UAH_RATE", "0") or 0)
    if currency == "USD" and usd_rate > 0:
        price_uah = round(raw_price * usd_rate)

    rooms_match = _first_match(
        (
            r"(?:🔑\s*)?(\d{1,2})\s*(?:[-–]?\s*кім(?:нат(?:на|и|ну|ної)?)?|к(?:/с)?\b)",
            r"(одно|двох?|три|чотири)\s*[-–]?\s*кімнат",
        ),
        compact,
    )
    word_rooms = {"одно": 1, "двох": 2, "дво": 2, "три": 3, "чотири": 4}
    rooms = 0
    if rooms_match:
        token = rooms_match.group(1).lower()
        rooms = int(token) if token.isdigit() else word_rooms.get(token, 0)

    area_match = _first_match((r"(?:✏️\s*)?(\d+(?:[.,]\d+)?)\s*(?:м[²2]|кв\.?\s*м)",), compact)
    area_sqm = _number(area_match.group(1)) if area_match else 0
    floor_match = _first_match((r"(?:поверх|этаж)\s*[:\-]?\s*(\d{1,3})(?:\s*[/ізз]\s*(\d{1,3}))?",), compact)
    floor = int(floor_match.group(1)) if floor_match else None
    total_floors = int(floor_match.group(2)) if floor_match and floor_match.group(2) else None

    address = "Адреса в оголошенні"
    district = ""
    location_match = re.search(r"(?:📍|(?:вул(?:иця)?|вулиця|ул\.)\s*)\s*([^\n]{3,160})", compact, re.IGNORECASE)
    if location_match:
        address = location_match.group(1).strip(" |-—")
        district = address.split(",", 1)[0].strip() if "," in address else ""
    else:
        street_match = re.search(r"([^\n]{0,80}\b(?:вул\.|вулиця|ул\.)\s*[^\n]{3,100})", compact, re.IGNORECASE)
        if street_match:
            address = street_match.group(1).strip()

    commission_pct = source.default_commission_pct
    if re.search(r"без\s+(?:коміс|комисс)|#безкоміс", lowered):
        commission_pct = 0
    else:
        commission_match = re.search(r"коміс(?:ія|сии|сия)?\s*[:\-]?\s*(\d{1,3})\s*%", lowered)
        if commission_match:
            commission_pct = min(int(commission_match.group(1)), 100)

    phone_match = re.search(r"(?:\+?38)?[\s(\-]*(0\d{2})[\s)\-]*\d{3}[\s\-]*\d{2}[\s\-]*\d{2}", compact)
    phone = re.sub(r"\D", "", phone_match.group(0)) if phone_match else ""
    if phone and not phone.startswith("38"):
        phone = f"38{phone}"
    pets_allowed = bool(re.search(r"можна\s+з\s+(?:твар|кот|соб)|🐶|🐱|pets?", lowered))
    owner_only = bool(re.search(r"#?власник|від\s+власник|без\s+(?:посередник|рієлтор)", lowered))

    return {
        "city": source.city,
        "district": district,
        "address": address,
        "price_uah": price_uah,
        "price_original": f"{raw_price:g} {'USD' if currency == 'USD' else 'грн'}",
        "currency": currency,
        "rooms": rooms,
        "area_sqm": area_sqm,
        "floor": floor,
        "total_floors": total_floors,
        "pets_allowed": pets_allowed,
        "owner_only": owner_only,
        "commission_pct": commission_pct,
        "description": compact[:5000],
        "contact_name": source.title,
        "contact_phone": f"+{phone}" if phone else "",
    }


def parse_channel_page(html: str, source: TelegramSource) -> list[dict[str, Any]]:
    soup = BeautifulSoup(html, "html.parser")
    listings: list[dict[str, Any]] = []
    for message in soup.select(".tgme_widget_message[data-post]"):
        post_id = message.get("data-post", "")
        text_node = message.select_one(".tgme_widget_message_text")
        if not post_id or not text_node:
            continue
        parsed = parse_listing_text(text_node.get_text("\n", strip=True), source)
        if not parsed:
            continue
        date_link = message.select_one("a.tgme_widget_message_date")
        source_url = date_link.get("href", "") if date_link else f"https://t.me/{post_id}"
        time_node = message.select_one("time[datetime]")
        published_at = time_node.get("datetime") if time_node else None
        photos: list[str] = []
        for photo in message.select("a.tgme_widget_message_photo"):
            style = photo.get("style", "")
            image_match = re.search(r"url\(['\"]?([^'\")]+)", style)
            if image_match:
                photos.append(image_match.group(1))
        parsed.update(
            {
                "channel": source.channel,
                "source": f"telegram:{source.channel}",
                "external_id": post_id,
                "source_url": source_url,
                "source_title": source.title,
                "published_at": published_at,
                "photos": photos,
            }
        )
        listings.append(parsed)
    return listings


class TelegramSourceSync:
    def __init__(self, database: Database, sources: tuple[TelegramSource, ...] = TELEGRAM_SOURCES) -> None:
        self.database = database
        self.sources = sources
        self.last_results: dict[str, dict[str, Any]] = {}

    def source_status(self) -> list[dict[str, Any]]:
        return [
            {**asdict(source), "preview_url": source.preview_url, **self.last_results.get(source.channel, {})}
            for source in self.sources
        ]

    def sync_all(self) -> dict[str, Any]:
        started_at = datetime.now(UTC).isoformat(timespec="seconds")
        totals = {"fetched": 0, "created": 0, "updated": 0, "failed_sources": 0}
        headers = {"User-Agent": "MonitorioRent/0.2 (+public Telegram listing index)"}
        with httpx.Client(headers=headers, follow_redirects=True, timeout=20) as client:
            for source in self.sources:
                try:
                    response = client.get(source.preview_url)
                    response.raise_for_status()
                    items = parse_channel_page(response.text, source)
                    created = 0
                    for item in items:
                        _, was_created = self.database.upsert_external_listing(item, item.pop("photos", []))
                        created += int(was_created)
                    result = {
                        "ok": True,
                        "last_sync_at": datetime.now(UTC).isoformat(timespec="seconds"),
                        "fetched": len(items),
                        "created": created,
                        "updated": len(items) - created,
                    }
                    self.last_results[source.channel] = result
                    totals["fetched"] += len(items)
                    totals["created"] += created
                    totals["updated"] += len(items) - created
                except Exception as exc:
                    self.last_results[source.channel] = {
                        "ok": False,
                        "last_sync_at": datetime.now(UTC).isoformat(timespec="seconds"),
                        "error": type(exc).__name__,
                    }
                    totals["failed_sources"] += 1
        return {"started_at": started_at, **totals, "sources": self.source_status()}
