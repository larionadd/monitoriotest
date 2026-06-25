from __future__ import annotations

import csv
from pathlib import Path

from .config import Source
from .locales import DEFAULT_COUNTRY, normalize_country, normalize_language


def load_sources(path: Path) -> list[Source]:
    with path.open("r", encoding="utf-8-sig", newline="") as fh:
        rows = csv.DictReader(fh)
        sources = [
            Source(
                name=(row.get("name") or "").strip(),
                url=(row.get("url") or "").strip(),
                type=(row.get("type") or "rss").strip().lower(),
                rank=parse_int(row.get("rank")),
                subscribers=parse_int(row.get("subscribers")),
                country=normalize_country(row.get("country") or DEFAULT_COUNTRY),
                language=normalize_language(row.get("language") or "") if row.get("language") else "",
            )
            for row in rows
        ]
    return [source for source in sources if source.name and source.url]


def parse_int(value: object) -> int | None:
    try:
        text = str(value or "").strip()
        return int(text) if text else None
    except ValueError:
        return None
