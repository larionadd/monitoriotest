from __future__ import annotations

import json
import urllib.error
import urllib.parse
import urllib.request
from typing import Any

from app.config import settings


REQUEST_TIMEOUT_SECONDS = 20

SEAT_LABELS = {
    "any": "будь-яке місце",
    "coupe": "купе",
    "platzkart": "плацкарт",
    "lux": "люкс",
    "sitting": "сидячий",
    "intercity": "Інтерсіті",
}

SEAT_MATCHERS = {
    "coupe": ("купе", "compartment", "к", "К"),
    "platzkart": ("плацкарт", "плац", "reserved", "п", "П"),
    "lux": ("люкс", "св", "suite", "л", "Л"),
    "sitting": ("сидяч", "sitting", "seat", "с", "С"),
    "intercity": ("інтерсіті", "intercity", "ic", "інтер"),
}


def official_search_url() -> str:
    return "https://booking.uz.gov.ua/"


def _headers() -> dict[str, str]:
    return {
        "Accept": "application/json",
        "Content-Type": "application/json; charset=UTF-8",
        "User-Agent": "UZ/1.7.3 Android/7.1.2 User/guest",
        "x-client-locale": "uk",
    }


def _get_json(path: str, params: dict[str, Any]) -> Any:
    query = urllib.parse.urlencode({key: value for key, value in params.items() if value not in {None, ""}})
    url = f"{settings.uz_booking_base.rstrip('/')}{path}"
    if query:
        url = f"{url}?{query}"
    request = urllib.request.Request(url, headers=_headers(), method="GET")
    with urllib.request.urlopen(request, timeout=REQUEST_TIMEOUT_SECONDS) as response:
        charset = response.headers.get_content_charset() or "utf-8"
        return json.loads(response.read().decode(charset))


def find_stations(query: str) -> list[dict[str, Any]]:
    if not query.strip():
        return []
    payload = _get_json("/api/stations", {"search": query.strip()})
    items = payload.get("data", payload) if isinstance(payload, dict) else payload
    if not isinstance(items, list):
        return []
    stations: list[dict[str, Any]] = []
    for item in items:
        if not isinstance(item, dict):
            continue
        station_id = item.get("id") or item.get("value") or item.get("station_id")
        title = item.get("title") or item.get("name") or item.get("label")
        if station_id and title:
            stations.append({"id": str(station_id), "title": str(title)})
    return stations


def _resolve_station_id(station_name: str, saved_id: str | None) -> tuple[str | None, str | None]:
    if saved_id:
        return saved_id, None
    try:
        stations = find_stations(station_name)
    except (urllib.error.HTTPError, urllib.error.URLError, TimeoutError, json.JSONDecodeError) as exc:
        return None, _format_network_error(exc)
    if not stations:
        return None, f"Не вдалося знайти станцію УЗ: {station_name}"
    return stations[0]["id"], None


def _format_network_error(exc: BaseException) -> str:
    if isinstance(exc, urllib.error.HTTPError):
        return f"УЗ endpoint повернув HTTP {exc.code}. Для live-перевірки може бути потрібна авторизація або інший доступ."
    return f"Не вдалося підключитися до УЗ endpoint: {exc}"


def _extract_items(payload: Any) -> list[dict[str, Any]]:
    if isinstance(payload, list):
        return [item for item in payload if isinstance(item, dict)]
    if not isinstance(payload, dict):
        return []
    for key in ("data", "trips", "items", "result"):
        value = payload.get(key)
        if isinstance(value, list):
            return [item for item in value if isinstance(item, dict)]
    return []


def _first_int(*values: Any) -> int:
    for value in values:
        try:
            if value is not None and str(value).strip() != "":
                return int(value)
        except (TypeError, ValueError):
            continue
    return 0


def _seat_type_matches(requested: str, item: dict[str, Any]) -> bool:
    if requested == "any":
        return True
    text = " ".join(str(value) for value in item.values() if value is not None).lower()
    return any(marker.lower() in text for marker in SEAT_MATCHERS.get(requested, ()))


def _wagon_classes(trip: dict[str, Any]) -> list[dict[str, Any]]:
    train = trip.get("train") if isinstance(trip.get("train"), dict) else {}
    for container in (trip, train):
        for key in ("wagon_classes", "wagonTypes", "types", "classes"):
            value = container.get(key)
            if isinstance(value, list):
                return [item for item in value if isinstance(item, dict)]
    return []


def _train_number(trip: dict[str, Any]) -> str:
    train = trip.get("train") if isinstance(trip.get("train"), dict) else {}
    return str(train.get("number") or trip.get("train_number") or trip.get("number") or "")


def _matches_train_number(expected: str | None, actual: str) -> bool:
    if not expected:
        return True
    cleaned_expected = "".join(ch for ch in expected if ch.isalnum())
    cleaned_actual = "".join(ch for ch in actual if ch.isalnum())
    return cleaned_expected.lower() in cleaned_actual.lower()


def _available_seats_for_trip(trip: dict[str, Any], seat_type: str) -> int:
    classes = _wagon_classes(trip)
    if classes:
        total = 0
        for wagon_class in classes:
            if not _seat_type_matches(seat_type, wagon_class):
                continue
            total += _first_int(
                wagon_class.get("free_seats"),
                wagon_class.get("freeSeats"),
                wagon_class.get("places"),
                wagon_class.get("free"),
                wagon_class.get("count"),
            )
        return total
    if seat_type != "any":
        return 0
    return _first_int(trip.get("free_seats"), trip.get("freeSeats"), trip.get("places"), trip.get("free"))


def check_availability(watch: dict[str, Any]) -> dict[str, Any]:
    from_id, from_error = _resolve_station_id(watch["origin_station"], watch.get("origin_station_id"))
    to_id, to_error = _resolve_station_id(watch["destination_station"], watch.get("destination_station_id"))
    if from_error or to_error:
        return {
            "connected": False,
            "available": False,
            "status": "Джерело УЗ не підключене для live-перевірки.",
            "error": from_error or to_error,
            "matches": [],
            "origin_station_id": from_id,
            "destination_station_id": to_id,
            "search_url": official_search_url(),
        }
    try:
        payload = _get_json(
            "/api/trips",
            {
                "station_from_id": from_id,
                "station_to_id": to_id,
                "date": watch["travel_date"],
            },
        )
    except (urllib.error.HTTPError, urllib.error.URLError, TimeoutError, json.JSONDecodeError) as exc:
        return {
            "connected": False,
            "available": False,
            "status": "УЗ не дала live-відповідь.",
            "error": _format_network_error(exc),
            "matches": [],
            "origin_station_id": from_id,
            "destination_station_id": to_id,
            "search_url": official_search_url(),
        }

    matches = []
    for trip in _extract_items(payload):
        train_number = _train_number(trip)
        if not _matches_train_number(watch.get("train_number"), train_number):
            continue
        seats = _available_seats_for_trip(trip, watch.get("seat_type") or "any")
        if seats > 0:
            matches.append({"train_number": train_number or "поїзд", "seats": seats})

    available = bool(matches)
    seat_label = SEAT_LABELS.get(watch.get("seat_type") or "any", "будь-яке місце")
    return {
        "connected": True,
        "available": available,
        "status": f"Знайдено {sum(item['seats'] for item in matches)} місць: {seat_label}." if available else "Потрібних місць поки немає.",
        "error": None,
        "matches": matches,
        "origin_station_id": from_id,
        "destination_station_id": to_id,
        "search_url": official_search_url(),
    }
