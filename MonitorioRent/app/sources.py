from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from .db import Database
from .dim_ria_source import DimRiaSourceSync
from .telegram_sources import TelegramSourceSync


class ListingSourceSync:
    def __init__(self, database: Database) -> None:
        self.database = database
        self.telegram = TelegramSourceSync(database)
        self.dim_ria = DimRiaSourceSync(database)

    def sync_all(self) -> dict[str, Any]:
        self.telegram.database = self.database
        self.dim_ria.database = self.database
        started_at = datetime.now(UTC).isoformat(timespec="seconds")
        results: dict[str, Any] = {}
        for name, adapter in (("telegram", self.telegram), ("dimria", self.dim_ria)):
            try:
                results[name] = adapter.sync_all()
            except Exception as exc:
                results[name] = {"ok": False, "error": type(exc).__name__}
        return {"started_at": started_at, "adapters": results, "sources": self.source_status()}

    def source_status(self) -> list[dict[str, Any]]:
        return [*self.telegram.source_status(), self.dim_ria.source_status()]
