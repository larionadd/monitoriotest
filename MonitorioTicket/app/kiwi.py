from __future__ import annotations

import json
from datetime import datetime
from typing import Any
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from app.config import settings


API_BASE = "https://api.tequila.kiwi.com"


def _kiwi_date(value: str | None) -> str | None:
    if not value:
        return None
    try:
        return datetime.fromisoformat(value[:10]).strftime("%d/%m/%Y")
    except ValueError:
        return value


def search_flights(
    origin: str,
    destination: str | None,
    departure_date: str | None,
    return_date: str | None,
    passengers: int,
    currency: str,
    direct_only: bool,
    limit: int = 10,
) -> list[dict[str, Any]]:
    if not settings.kiwi_tequila_api_key:
        return []

    date_from = _kiwi_date(departure_date)
    params: dict[str, Any] = {
        "fly_from": origin.upper(),
        "fly_to": destination.upper() if destination else "anywhere",
        "date_from": date_from,
        "date_to": date_from,
        "adults": max(1, passengers),
        "curr": currency.upper(),
        "sort": "price",
        "asc": 1,
        "limit": limit,
        "one_for_city": 1 if not destination else 0,
    }
    if return_date:
        return_kiwi_date = _kiwi_date(return_date)
        params["return_from"] = return_kiwi_date
        params["return_to"] = return_kiwi_date
    if direct_only:
        params["max_stopovers"] = 0
        params["direct_flights"] = 1

    query = urlencode({key: value for key, value in params.items() if value not in {None, ""}})
    request = Request(
        f"{API_BASE}/v2/search?{query}",
        headers={
            "Accept": "application/json",
            "Accept-Encoding": "identity",
            "apikey": settings.kiwi_tequila_api_key,
        },
    )
    try:
        with urlopen(request, timeout=18) as response:
            payload = json.loads(response.read().decode("utf-8"))
    except Exception:
        return []

    data = payload.get("data") if isinstance(payload, dict) else []
    return data if isinstance(data, list) else []


def airline_label(offer: dict[str, Any]) -> str:
    airlines = offer.get("airlines")
    if isinstance(airlines, list) and airlines:
        return ", ".join(str(item) for item in airlines[:3])
    return "Kiwi"


def stops_count(offer: dict[str, Any]) -> int:
    route = offer.get("route")
    if isinstance(route, list) and route:
        return max(0, len(route) - 1)
    return 0
