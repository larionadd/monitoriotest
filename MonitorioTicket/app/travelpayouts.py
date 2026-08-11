from __future__ import annotations

import json
from datetime import datetime
from typing import Any
from urllib.parse import urlencode, urljoin, urlparse, urlunparse, parse_qsl
from urllib.request import Request, urlopen

from app.config import settings


API_BASE = "https://api.travelpayouts.com"
AVIASALES_BASE = "https://www.aviasales.com"


def _append_marker(url: str) -> str:
    if not settings.travelpayouts_marker:
        return url
    parsed = urlparse(url)
    query = dict(parse_qsl(parsed.query))
    query.setdefault("marker", settings.travelpayouts_marker)
    return urlunparse(parsed._replace(query=urlencode(query)))


def aviasales_link(link: str | None, origin: str, destination: str | None, departure_date: str | None) -> str:
    if link:
        return _append_marker(urljoin(AVIASALES_BASE, link))
    if destination and departure_date:
        try:
            date_part = datetime.fromisoformat(departure_date).strftime("%d%m")
        except ValueError:
            date_part = ""
        return _append_marker(f"{AVIASALES_BASE}/search/{origin.upper()}{date_part}{destination.upper()}1")
    params = {"origin_iata": origin.upper()}
    if destination:
        params["destination_iata"] = destination.upper()
    if departure_date:
        params["depart_date"] = departure_date
    return _append_marker(f"{AVIASALES_BASE}/search?{urlencode(params)}")


def prices_for_dates(
    origin: str,
    destination: str | None,
    departure_date: str | None,
    return_date: str | None,
    currency: str,
    direct_only: bool,
    limit: int = 10,
) -> list[dict[str, Any]]:
    if not settings.travelpayouts_token:
        return []

    params: dict[str, Any] = {
        "origin": origin.upper(),
        "departure_at": departure_date or "",
        "one_way": "false" if return_date else "true",
        "direct": "true" if direct_only else "false",
        "sorting": "price",
        "unique": "false",
        "limit": str(limit),
        "page": "1",
        "currency": currency.lower(),
        "cy": currency.lower(),
        "token": settings.travelpayouts_token,
    }
    if destination:
        params["destination"] = destination.upper()
    if return_date:
        params["return_at"] = return_date

    query = urlencode({key: value for key, value in params.items() if value not in {None, ""}})
    request = Request(
        f"{API_BASE}/aviasales/v3/prices_for_dates?{query}",
        headers={
            "Accept": "application/json",
            "Accept-Encoding": "identity",
            "X-Access-Token": settings.travelpayouts_token,
        },
    )
    try:
        with urlopen(request, timeout=12) as response:
            payload = json.loads(response.read().decode("utf-8"))
    except Exception:
        return []
    if not payload.get("success"):
        return []
    data = payload.get("data") or []
    return data if isinstance(data, list) else []
