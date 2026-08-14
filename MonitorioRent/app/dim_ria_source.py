from __future__ import annotations

import os
import re
from datetime import UTC, datetime
from typing import Any

import httpx

from .db import Database


API_ROOT = "https://developers.ria.com/dom"
CITY_IDS = {
    "Київ": 10,
    "Львів": 5,
    "Одеса": 12,
    "Дніпро": 11,
    "Харків": 7,
    "Івано-Франківськ": 15,
    "Вінниця": 4,
    "Чернівці": 20,
    "Ужгород": 19,
    "Запоріжжя": 9,
}


def _number(value: Any, default: float = 0) -> float:
    try:
        return float(str(value).replace(" ", "").replace(",", "."))
    except (TypeError, ValueError):
        return default


def _photo_urls(value: Any) -> list[str]:
    photos = value.values() if isinstance(value, dict) else value or []
    result: list[str] = []
    for photo in photos:
        candidate = photo.get("file") or photo.get("url") if isinstance(photo, dict) else photo
        if not candidate:
            continue
        candidate = str(candidate)
        if candidate.startswith(("https://", "http://")):
            result.append(candidate)
        else:
            result.append(f"https://cdn.riastatic.com/photos/{candidate.lstrip('/')}")
    return list(dict.fromkeys(result))[:8]


def normalize_advertisement(item: dict[str, Any]) -> tuple[dict[str, Any], list[str]]:
    advert_id = str(item.get("advert_id") or item.get("id") or item.get("web_id") or "").strip()
    if not advert_id:
        raise ValueError("DIM.RIA advertisement has no id")

    city = item.get("city_name_uk") or item.get("city_name") or item.get("city") or ""
    if isinstance(city, dict):
        city = city.get("name") or city.get("value") or ""
    district = item.get("district_name_uk") or item.get("district_name") or item.get("district") or ""
    if isinstance(district, dict):
        district = district.get("name") or district.get("value") or ""
    street = item.get("street_name_uk") or item.get("street_name") or item.get("street") or ""
    building = item.get("building_number_str") or item.get("building_number") or ""
    address = item.get("address") or " ".join(filter(None, (str(street), str(building))))
    address = str(address).strip() or "Адреса в оголошенні"

    currency_raw = str(item.get("currency_type") or item.get("currency") or "UAH").upper()
    currency = "USD" if "$" in currency_raw or "USD" in currency_raw else "UAH"
    price = _number(item.get("price") or item.get("price_value"))
    price_uah = int(price) if currency == "UAH" else int(_number(item.get("price_uah")))
    rooms = int(_number(item.get("rooms_count") or item.get("rooms")))
    area = _number(item.get("total_square_meters") or item.get("total_square") or item.get("area"))
    offer = str(item.get("advert_type_name") or item.get("offer_type") or "").lower()
    owner_only = bool(item.get("is_owner")) or any(word in offer for word in ("власник", "собственник"))
    no_commission = owner_only or any(word in offer for word in ("без коміс", "без комис"))
    description = str(item.get("description_uk") or item.get("description") or "Оголошення DIM.RIA")[:5000]
    pets_allowed = bool(item.get("withAnimal")) or bool(
        re.search(r"можна\s+з\s+(?:твар|кот|соб)|домашн\w*\s+твар", description, re.I)
    )
    beautiful_url = str(item.get("beautiful_url") or "").strip("/")
    if beautiful_url.startswith("http"):
        source_url = beautiful_url
    elif beautiful_url:
        source_url = f"https://dom.ria.com/uk/{beautiful_url}"
    else:
        source_url = f"https://dom.ria.com/uk/realty-{advert_id}.html"
    published_at = item.get("publishing_date") or item.get("created_at") or item.get("date_created")
    floor_match = re.search(r"(\d+)\D+(\d+)", str(item.get("floor_info") or ""))
    floor = int(_number(item.get("floor"))) or (int(floor_match.group(1)) if floor_match else None)
    total_floors = int(_number(item.get("floors_count") or item.get("total_floors"))) or (
        int(floor_match.group(2)) if floor_match else None
    )

    payload = {
        "channel": "dimria",
        "source": "dimria",
        "external_id": advert_id,
        "source_url": source_url,
        "source_title": "DIM.RIA",
        "city": str(city),
        "district": str(district),
        "address": address,
        "price_uah": price_uah,
        "price_original": f"{price:g} {'USD' if currency == 'USD' else 'грн'}" if price else "",
        "currency": currency,
        "rooms": rooms,
        "area_sqm": area,
        "floor": floor,
        "total_floors": total_floors,
        "pets_allowed": pets_allowed,
        "owner_only": owner_only,
        "commission_pct": 0 if no_commission else int(_number(item.get("commission"))),
        "description": description,
        "contact_name": "DIM.RIA",
        "contact_phone": "",
        "published_at": published_at,
    }
    return payload, _photo_urls(item.get("photos") or item.get("photo"))


class DimRiaSourceSync:
    def __init__(
        self,
        database: Database,
        api_key: str | None = None,
        max_details: int | None = None,
        min_interval_seconds: int | None = None,
        monthly_budget: int | None = None,
    ) -> None:
        self.database = database
        self.api_key = (api_key if api_key is not None else os.getenv("DIM_RIA_API_KEY", "")).strip()
        self.max_details = max_details if max_details is not None else int(os.getenv("DIM_RIA_MAX_DETAILS_PER_RUN", "1"))
        self.min_interval_seconds = (
            min_interval_seconds
            if min_interval_seconds is not None
            else int(os.getenv("DIM_RIA_MIN_INTERVAL_SECONDS", "7200"))
        )
        self.monthly_budget = (
            monthly_budget
            if monthly_budget is not None
            else int(os.getenv("DIM_RIA_MONTHLY_BUDGET", "900"))
        )
        self.last_result: dict[str, Any] = {}

    @property
    def enabled(self) -> bool:
        return bool(self.api_key)

    def source_status(self) -> dict[str, Any]:
        return {
            "source": "dimria",
            "title": "DIM.RIA",
            "enabled": self.enabled,
            "preview_url": "https://dom.ria.com/uk/",
            "min_interval_seconds": self.min_interval_seconds,
            **self.database.source_budget_status("dimria", self.monthly_budget),
            **self.last_result,
        }

    def sync_all(self) -> dict[str, Any]:
        started_at = datetime.now(UTC).isoformat(timespec="seconds")
        if not self.enabled:
            return {"started_at": started_at, "enabled": False, "fetched": 0, "created": 0, "updated": 0}
        if not self.database.claim_source_sync("dimria", self.min_interval_seconds):
            return {
                "started_at": started_at,
                "enabled": True,
                "skipped": "min_interval",
                **self.database.source_budget_status("dimria", self.monthly_budget),
            }
        if not self.database.reserve_source_requests("dimria", self.monthly_budget):
            return {
                "started_at": started_at,
                "enabled": True,
                "skipped": "monthly_budget",
                **self.database.source_budget_status("dimria", self.monthly_budget),
            }

        params: list[tuple[str, str | int]] = [
            ("api_key", self.api_key),
            ("category", 1),
            ("realty_type", 2),
            ("operation_type", 3),
            ("with_photo", 1),
            ("sort", "created_at"),
            ("page", 0),
        ]
        for city_id in CITY_IDS.values():
            params.append(("city_id", city_id))

        created = 0
        updated = 0
        detailed = 0
        with httpx.Client(headers={"User-Agent": "MonitorioRent/0.3"}, timeout=20) as client:
            search = client.get(f"{API_ROOT}/search", params=params)
            search.raise_for_status()
            body = search.json()
            raw_items = body.get("items", []) if isinstance(body, dict) else []
            ids = [str(value.get("id") or value.get("advert_id")) if isinstance(value, dict) else str(value) for value in raw_items]
            ids = [value for value in ids if value and value != "None"]
            for advert_id in ids:
                if self.database.has_external_listing("dimria", advert_id):
                    continue
                if detailed >= self.max_details:
                    break
                if not self.database.reserve_source_requests("dimria", self.monthly_budget):
                    break
                response = client.get(f"{API_ROOT}/info/{advert_id}", params={"api_key": self.api_key})
                response.raise_for_status()
                detail = response.json()
                detail.setdefault("advert_id", advert_id)
                payload, photos = normalize_advertisement(detail)
                _, was_created = self.database.upsert_external_listing(payload, photos)
                created += int(was_created)
                updated += int(not was_created)
                detailed += 1

        self.last_result = {
            "ok": True,
            "last_sync_at": datetime.now(UTC).isoformat(timespec="seconds"),
            "fetched": len(ids),
            "details_fetched": detailed,
            "created": created,
            "updated": updated,
        }
        return {
            "started_at": started_at,
            "enabled": True,
            **self.last_result,
            **self.database.source_budget_status("dimria", self.monthly_budget),
        }
