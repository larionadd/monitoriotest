from __future__ import annotations

import sqlite3
from contextlib import contextmanager
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any
from uuid import uuid4


def utc_now() -> str:
    return datetime.now(UTC).isoformat(timespec="seconds")


class Database:
    def __init__(self, path: str | Path) -> None:
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.initialize()

    def connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.path, timeout=30)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys = ON")
        return connection

    @contextmanager
    def connection(self):
        connection = self.connect()
        try:
            yield connection
            connection.commit()
        except Exception:
            connection.rollback()
            raise
        finally:
            connection.close()

    def initialize(self) -> None:
        with self.connection() as connection:
            connection.executescript(
                """
                CREATE TABLE IF NOT EXISTS profiles (
                    user_id TEXT PRIMARY KEY,
                    role TEXT NOT NULL CHECK (role IN ('renter', 'landlord')),
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS saved_searches (
                    id TEXT PRIMARY KEY,
                    user_id TEXT NOT NULL,
                    city TEXT NOT NULL,
                    district TEXT NOT NULL DEFAULT '',
                    price_min INTEGER NOT NULL DEFAULT 0,
                    price_max INTEGER NOT NULL,
                    rooms_min INTEGER NOT NULL DEFAULT 1,
                    rooms_max INTEGER NOT NULL DEFAULT 1,
                    pets_allowed INTEGER NOT NULL DEFAULT 0,
                    no_commission INTEGER NOT NULL DEFAULT 0,
                    owner_only INTEGER NOT NULL DEFAULT 0,
                    active INTEGER NOT NULL DEFAULT 1,
                    created_at TEXT NOT NULL
                );

                CREATE INDEX IF NOT EXISTS idx_saved_searches_user
                    ON saved_searches (user_id, created_at DESC);

                CREATE TABLE IF NOT EXISTS listings (
                    id TEXT PRIMARY KEY,
                    user_id TEXT NOT NULL,
                    status TEXT NOT NULL DEFAULT 'pending'
                        CHECK (status IN ('draft', 'pending', 'active', 'rejected', 'archived')),
                    city TEXT NOT NULL,
                    district TEXT NOT NULL DEFAULT '',
                    address TEXT NOT NULL,
                    price_uah INTEGER NOT NULL,
                    rooms INTEGER NOT NULL,
                    area_sqm REAL NOT NULL,
                    floor INTEGER,
                    total_floors INTEGER,
                    pets_allowed INTEGER NOT NULL DEFAULT 0,
                    commission_pct INTEGER NOT NULL DEFAULT 0,
                    description TEXT NOT NULL,
                    contact_name TEXT NOT NULL,
                    contact_phone TEXT NOT NULL,
                    source TEXT NOT NULL DEFAULT 'owner',
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                );

                CREATE INDEX IF NOT EXISTS idx_listings_feed
                    ON listings (status, city, price_uah, created_at DESC);
                CREATE INDEX IF NOT EXISTS idx_listings_user
                    ON listings (user_id, created_at DESC);

                CREATE TABLE IF NOT EXISTS listing_photos (
                    id TEXT PRIMARY KEY,
                    listing_id TEXT NOT NULL REFERENCES listings(id) ON DELETE CASCADE,
                    url TEXT NOT NULL,
                    position INTEGER NOT NULL DEFAULT 0
                );

                CREATE TABLE IF NOT EXISTS listing_notifications (
                    search_id TEXT NOT NULL REFERENCES saved_searches(id) ON DELETE CASCADE,
                    listing_id TEXT NOT NULL REFERENCES listings(id) ON DELETE CASCADE,
                    sent_at TEXT NOT NULL,
                    PRIMARY KEY (search_id, listing_id)
                );

                CREATE TABLE IF NOT EXISTS search_monitor_state (
                    search_id TEXT PRIMARY KEY REFERENCES saved_searches(id) ON DELETE CASCADE,
                    initial_report_sent INTEGER NOT NULL DEFAULT 0,
                    last_checked_at TEXT,
                    updated_at TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS source_sync_state (
                    source TEXT PRIMARY KEY,
                    last_started_at TEXT,
                    month_key TEXT NOT NULL,
                    request_count INTEGER NOT NULL DEFAULT 0,
                    updated_at TEXT NOT NULL
                );
                """
            )
            self._ensure_listing_columns(connection)
            connection.execute(
                """
                CREATE UNIQUE INDEX IF NOT EXISTS idx_listings_external
                    ON listings (source, external_id)
                    WHERE external_id IS NOT NULL AND external_id != ''
                """
            )
            connection.execute("UPDATE listings SET owner_only = 1 WHERE source = 'owner'")

    @staticmethod
    def _ensure_listing_columns(connection: sqlite3.Connection) -> None:
        existing = {
            row["name"]
            for row in connection.execute("PRAGMA table_info(listings)").fetchall()
        }
        additions = {
            "external_id": "TEXT",
            "source_url": "TEXT NOT NULL DEFAULT ''",
            "source_title": "TEXT NOT NULL DEFAULT ''",
            "price_original": "TEXT NOT NULL DEFAULT ''",
            "currency": "TEXT NOT NULL DEFAULT 'UAH'",
            "published_at": "TEXT",
            "owner_only": "INTEGER NOT NULL DEFAULT 0",
        }
        for name, definition in additions.items():
            if name not in existing:
                connection.execute(f"ALTER TABLE listings ADD COLUMN {name} {definition}")
        search_columns = {
            row["name"]
            for row in connection.execute("PRAGMA table_info(saved_searches)").fetchall()
        }
        if "lookback_days" not in search_columns:
            connection.execute("ALTER TABLE saved_searches ADD COLUMN lookback_days INTEGER NOT NULL DEFAULT 3")

    def set_role(self, user_id: str, role: str) -> dict[str, Any]:
        now = utc_now()
        with self.connection() as connection:
            connection.execute(
                """
                INSERT INTO profiles (user_id, role, created_at, updated_at)
                VALUES (?, ?, ?, ?)
                ON CONFLICT(user_id) DO UPDATE SET
                    role = excluded.role,
                    updated_at = excluded.updated_at
                """,
                (user_id, role, now, now),
            )
        return self.get_profile(user_id) or {}

    def claim_source_sync(self, source: str, min_interval_seconds: int) -> bool:
        now = datetime.now(UTC)
        month_key = now.strftime("%Y-%m")
        with self.connection() as connection:
            connection.execute("BEGIN IMMEDIATE")
            row = connection.execute(
                "SELECT last_started_at, month_key, request_count FROM source_sync_state WHERE source = ?",
                (source,),
            ).fetchone()
            if row and row["last_started_at"] and min_interval_seconds > 0:
                last_started = datetime.fromisoformat(row["last_started_at"])
                if now - last_started < timedelta(seconds=min_interval_seconds):
                    return False
            request_count = row["request_count"] if row and row["month_key"] == month_key else 0
            connection.execute(
                """
                INSERT INTO source_sync_state (source, last_started_at, month_key, request_count, updated_at)
                VALUES (?, ?, ?, ?, ?)
                ON CONFLICT(source) DO UPDATE SET
                    last_started_at = excluded.last_started_at,
                    month_key = excluded.month_key,
                    request_count = excluded.request_count,
                    updated_at = excluded.updated_at
                """,
                (source, now.isoformat(timespec="seconds"), month_key, request_count, now.isoformat(timespec="seconds")),
            )
        return True

    def reserve_source_requests(self, source: str, monthly_limit: int, count: int = 1) -> bool:
        now = datetime.now(UTC)
        month_key = now.strftime("%Y-%m")
        with self.connection() as connection:
            connection.execute("BEGIN IMMEDIATE")
            row = connection.execute(
                "SELECT month_key, request_count, last_started_at FROM source_sync_state WHERE source = ?",
                (source,),
            ).fetchone()
            used = row["request_count"] if row and row["month_key"] == month_key else 0
            if used + count > monthly_limit:
                return False
            connection.execute(
                """
                INSERT INTO source_sync_state (source, last_started_at, month_key, request_count, updated_at)
                VALUES (?, ?, ?, ?, ?)
                ON CONFLICT(source) DO UPDATE SET
                    month_key = excluded.month_key,
                    request_count = excluded.request_count,
                    updated_at = excluded.updated_at
                """,
                (
                    source,
                    row["last_started_at"] if row else None,
                    month_key,
                    used + count,
                    now.isoformat(timespec="seconds"),
                ),
            )
        return True

    def source_budget_status(self, source: str, monthly_limit: int) -> dict[str, Any]:
        month_key = datetime.now(UTC).strftime("%Y-%m")
        with self.connection() as connection:
            row = connection.execute(
                "SELECT last_started_at, month_key, request_count FROM source_sync_state WHERE source = ?",
                (source,),
            ).fetchone()
        used = row["request_count"] if row and row["month_key"] == month_key else 0
        return {
            "month": month_key,
            "requests_used": used,
            "requests_limit": monthly_limit,
            "requests_remaining": max(0, monthly_limit - used),
            "last_started_at": row["last_started_at"] if row else None,
        }

    def get_profile(self, user_id: str) -> dict[str, Any] | None:
        with self.connection() as connection:
            row = connection.execute(
                "SELECT user_id, role, created_at, updated_at FROM profiles WHERE user_id = ?",
                (user_id,),
            ).fetchone()
        return dict(row) if row else None

    def create_search(self, user_id: str, payload: dict[str, Any]) -> dict[str, Any]:
        search_id = str(uuid4())
        created_at = utc_now()
        with self.connection() as connection:
            connection.execute(
                """
                INSERT INTO saved_searches (
                    id, user_id, city, district, price_min, price_max,
                    rooms_min, rooms_max, pets_allowed, no_commission,
                    owner_only, active, created_at
                    , lookback_days
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 1, ?, ?)
                """,
                (
                    search_id,
                    user_id,
                    payload["city"],
                    payload.get("district", ""),
                    payload.get("price_min", 0),
                    payload["price_max"],
                    payload.get("rooms_min", 1),
                    payload.get("rooms_max", 1),
                    int(payload.get("pets_allowed", False)),
                    int(payload.get("no_commission", False)),
                    int(payload.get("owner_only", False)),
                    created_at,
                    payload.get("lookback_days", 3),
                ),
            )
        return self.get_search(search_id, user_id) or {}

    def get_search(self, search_id: str, user_id: str) -> dict[str, Any] | None:
        with self.connection() as connection:
            row = connection.execute(
                "SELECT * FROM saved_searches WHERE id = ? AND user_id = ?",
                (search_id, user_id),
            ).fetchone()
        return self._search_row(row) if row else None

    def list_searches(self, user_id: str) -> list[dict[str, Any]]:
        with self.connection() as connection:
            rows = connection.execute(
                "SELECT * FROM saved_searches WHERE user_id = ? ORDER BY created_at DESC",
                (user_id,),
            ).fetchall()
        return [self._search_row(row) for row in rows]

    def delete_search(self, search_id: str, user_id: str) -> bool:
        with self.connection() as connection:
            cursor = connection.execute(
                "DELETE FROM saved_searches WHERE id = ? AND user_id = ?",
                (search_id, user_id),
            )
        return cursor.rowcount > 0

    def list_active_searches(self) -> list[dict[str, Any]]:
        with self.connection() as connection:
            rows = connection.execute(
                "SELECT * FROM saved_searches WHERE active = 1 ORDER BY created_at"
            ).fetchall()
        return [self._search_row(row) for row in rows]

    def search_monitor_state(self, search_id: str) -> dict[str, Any]:
        with self.connection() as connection:
            row = connection.execute(
                "SELECT * FROM search_monitor_state WHERE search_id = ?", (search_id,)
            ).fetchone()
        return dict(row) if row else {"search_id": search_id, "initial_report_sent": 0, "last_checked_at": None}

    def mark_search_checked(self, search_id: str, *, initial_report_sent: bool = True) -> None:
        now = utc_now()
        with self.connection() as connection:
            connection.execute(
                """
                INSERT INTO search_monitor_state (search_id, initial_report_sent, last_checked_at, updated_at)
                VALUES (?, ?, ?, ?)
                ON CONFLICT(search_id) DO UPDATE SET
                    initial_report_sent = MAX(search_monitor_state.initial_report_sent, excluded.initial_report_sent),
                    last_checked_at = excluded.last_checked_at,
                    updated_at = excluded.updated_at
                """,
                (search_id, int(initial_report_sent), now, now),
            )

    def notification_sent(self, search_id: str, listing_id: str) -> bool:
        with self.connection() as connection:
            row = connection.execute(
                "SELECT 1 FROM listing_notifications WHERE search_id = ? AND listing_id = ?",
                (search_id, listing_id),
            ).fetchone()
        return bool(row)

    def mark_notification_sent(self, search_id: str, listing_id: str) -> None:
        with self.connection() as connection:
            connection.execute(
                "INSERT OR IGNORE INTO listing_notifications (search_id, listing_id, sent_at) VALUES (?, ?, ?)",
                (search_id, listing_id, utc_now()),
            )

    def matches_for_search(self, search: dict[str, Any], *, only_unsent: bool = False, limit: int = 100) -> list[dict[str, Any]]:
        listings = self.list_feed(
            city=search["city"], district=search.get("district", ""),
            price_min=search.get("price_min"), price_max=search.get("price_max"),
            rooms_min=search.get("rooms_min"), rooms_max=search.get("rooms_max"),
            pets_allowed=bool(search.get("pets_allowed")),
            no_commission=bool(search.get("no_commission")),
            owner_only=bool(search.get("owner_only")),
            lookback_days=int(search.get("lookback_days", 3)), limit=limit,
        )
        if only_unsent:
            return [item for item in listings if not self.notification_sent(search["id"], item["id"])]
        return listings

    def similar_matches_for_search(self, search: dict[str, Any], *, limit: int = 5) -> list[dict[str, Any]]:
        """Return city-wide alternatives and reserve a slot for DIM.RIA when available."""
        candidates = self.list_feed(
            city=search["city"], district="",
            price_min=search.get("price_min"), price_max=search.get("price_max"),
            rooms_min=search.get("rooms_min"), rooms_max=search.get("rooms_max"),
            pets_allowed=bool(search.get("pets_allowed")),
            no_commission=bool(search.get("no_commission")),
            owner_only=bool(search.get("owner_only")),
            lookback_days=int(search.get("lookback_days", 3)), limit=100,
        )
        if not candidates:
            return []
        dim_ria = next((item for item in candidates if item.get("source") == "dimria"), None)
        if not dim_ria:
            return candidates[:limit]
        return [dim_ria, *(item for item in candidates if item["id"] != dim_ria["id"])][:limit]

    def create_listing(
        self,
        user_id: str,
        payload: dict[str, Any],
        photo_urls: list[str],
    ) -> dict[str, Any]:
        listing_id = str(uuid4())
        now = utc_now()
        with self.connection() as connection:
            connection.execute(
                """
                INSERT INTO listings (
                    id, user_id, status, city, district, address, price_uah,
                    rooms, area_sqm, floor, total_floors, pets_allowed,
                    commission_pct, description, contact_name, contact_phone,
                    source, owner_only, created_at, updated_at
                ) VALUES (?, ?, 'pending', ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'owner', 1, ?, ?)
                """,
                (
                    listing_id,
                    user_id,
                    payload["city"],
                    payload.get("district", ""),
                    payload["address"],
                    payload["price_uah"],
                    payload["rooms"],
                    payload["area_sqm"],
                    payload.get("floor"),
                    payload.get("total_floors"),
                    int(payload.get("pets_allowed", False)),
                    payload.get("commission_pct", 0),
                    payload["description"],
                    payload["contact_name"],
                    payload["contact_phone"],
                    now,
                    now,
                ),
            )
            connection.executemany(
                "INSERT INTO listing_photos (id, listing_id, url, position) VALUES (?, ?, ?, ?)",
                [
                    (str(uuid4()), listing_id, url, position)
                    for position, url in enumerate(photo_urls)
                ],
            )
        return self.get_listing(listing_id) or {}

    def get_listing(self, listing_id: str) -> dict[str, Any] | None:
        with self.connection() as connection:
            row = connection.execute(
                "SELECT * FROM listings WHERE id = ?",
                (listing_id,),
            ).fetchone()
            if not row:
                return None
            photos = connection.execute(
                "SELECT url FROM listing_photos WHERE listing_id = ? ORDER BY position",
                (listing_id,),
            ).fetchall()
        return self._listing_row(row, [photo["url"] for photo in photos])

    def upsert_external_listing(
        self,
        payload: dict[str, Any],
        photo_urls: list[str],
    ) -> tuple[dict[str, Any], bool]:
        now = utc_now()
        listing_id = str(uuid4())
        source = payload["source"]
        external_id = payload["external_id"]
        with self.connection() as connection:
            existing = connection.execute(
                "SELECT id FROM listings WHERE source = ? AND external_id = ?",
                (source, external_id),
            ).fetchone()
            if existing:
                listing_id = existing["id"]
                connection.execute(
                    """
                    UPDATE listings SET
                        status = 'active', city = ?, district = ?, address = ?,
                        price_uah = ?, rooms = ?, area_sqm = ?, floor = ?,
                        total_floors = ?, pets_allowed = ?, commission_pct = ?,
                        description = ?, contact_name = ?, contact_phone = ?,
                        source_url = ?, source_title = ?, price_original = ?,
                        currency = ?, published_at = ?, owner_only = ?, updated_at = ?
                    WHERE id = ?
                    """,
                    (
                        payload["city"], payload.get("district", ""),
                        payload.get("address", "Адреса в оголошенні"),
                        payload.get("price_uah", 0), payload.get("rooms", 0),
                        payload.get("area_sqm", 0), payload.get("floor"),
                        payload.get("total_floors"), int(payload.get("pets_allowed", False)),
                        payload.get("commission_pct", 0), payload["description"],
                        payload.get("contact_name", payload.get("source_title", "Telegram")),
                        payload.get("contact_phone", ""), payload.get("source_url", ""),
                        payload.get("source_title", ""), payload.get("price_original", ""),
                        payload.get("currency", "UAH"), payload.get("published_at"),
                        int(payload.get("owner_only", False)), now,
                        listing_id,
                    ),
                )
                created = False
            else:
                connection.execute(
                    """
                    INSERT INTO listings (
                        id, user_id, status, city, district, address, price_uah,
                        rooms, area_sqm, floor, total_floors, pets_allowed,
                        commission_pct, description, contact_name, contact_phone,
                        source, external_id, source_url, source_title,
                        price_original, currency, published_at, owner_only, created_at, updated_at
                    ) VALUES (?, ?, 'active', ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        listing_id, payload.get("user_id", f"source:{source}"), payload["city"],
                        payload.get("district", ""), payload.get("address", "Адреса в оголошенні"),
                        payload.get("price_uah", 0), payload.get("rooms", 0),
                        payload.get("area_sqm", 0), payload.get("floor"),
                        payload.get("total_floors"), int(payload.get("pets_allowed", False)),
                        payload.get("commission_pct", 0), payload["description"],
                        payload.get("contact_name", payload.get("source_title", "Telegram")),
                        payload.get("contact_phone", ""), source, external_id,
                        payload.get("source_url", ""), payload.get("source_title", ""),
                        payload.get("price_original", ""), payload.get("currency", "UAH"),
                        payload.get("published_at"), int(payload.get("owner_only", False)),
                        payload.get("published_at") or now, now,
                    ),
                )
                created = True

            connection.execute("DELETE FROM listing_photos WHERE listing_id = ?", (listing_id,))
            connection.executemany(
                "INSERT INTO listing_photos (id, listing_id, url, position) VALUES (?, ?, ?, ?)",
                [(str(uuid4()), listing_id, url, position) for position, url in enumerate(photo_urls[:8])],
            )
        return self.get_listing(listing_id) or {}, created

    def has_external_listing(self, source: str, external_id: str) -> bool:
        with self.connection() as connection:
            row = connection.execute(
                "SELECT 1 FROM listings WHERE source = ? AND external_id = ? LIMIT 1",
                (source, external_id),
            ).fetchone()
        return row is not None

    def list_user_listings(self, user_id: str) -> list[dict[str, Any]]:
        with self.connection() as connection:
            rows = connection.execute(
                "SELECT id FROM listings WHERE user_id = ? ORDER BY created_at DESC",
                (user_id,),
            ).fetchall()
        return [listing for row in rows if (listing := self.get_listing(row["id"]))]

    def list_listings_by_status(self, status: str, limit: int = 100) -> list[dict[str, Any]]:
        with self.connection() as connection:
            rows = connection.execute(
                "SELECT id FROM listings WHERE status = ? ORDER BY created_at ASC LIMIT ?",
                (status, max(1, min(limit, 200))),
            ).fetchall()
        return [listing for row in rows if (listing := self.get_listing(row["id"]))]

    def set_listing_status(self, listing_id: str, status: str) -> dict[str, Any] | None:
        with self.connection() as connection:
            cursor = connection.execute(
                "UPDATE listings SET status = ?, updated_at = ? WHERE id = ?",
                (status, utc_now(), listing_id),
            )
        if cursor.rowcount == 0:
            return None
        return self.get_listing(listing_id)

    def list_feed(
        self,
        *,
        city: str = "",
        district: str = "",
        price_min: int | None = None,
        price_max: int | None = None,
        rooms: int | None = None,
        rooms_min: int | None = None,
        rooms_max: int | None = None,
        pets_allowed: bool = False,
        no_commission: bool = False,
        owner_only: bool = False,
        lookback_days: int | None = None,
        limit: int = 30,
        include_pending_for_user: str = "",
    ) -> list[dict[str, Any]]:
        clauses = ["(status = 'active'"]
        params: list[Any] = []
        if include_pending_for_user:
            clauses[0] += " OR (status = 'pending' AND user_id = ?)"
            params.append(include_pending_for_user)
        clauses[0] += ")"
        if city:
            clauses.append("LOWER(city) = LOWER(?)")
            params.append(city)
        if district:
            clauses.append("LOWER(district || ' ' || address || ' ' || description) LIKE LOWER(?)")
            params.append(f"%{district}%")
        if price_min is not None:
            clauses.append("price_uah >= ?")
            params.append(price_min)
        if price_max is not None:
            clauses.append("price_uah > 0 AND price_uah <= ?")
            params.append(price_max)
        if rooms is not None:
            clauses.append("rooms = ?")
            params.append(rooms)
        if rooms_min is not None:
            clauses.append("rooms >= ?")
            params.append(rooms_min)
        if rooms_max is not None:
            clauses.append("rooms <= ?")
            params.append(rooms_max)
        if pets_allowed:
            clauses.append("pets_allowed = 1")
        if no_commission:
            clauses.append("commission_pct = 0")
        if owner_only:
            clauses.append("owner_only = 1")
        if lookback_days is not None:
            clauses.append("datetime(COALESCE(published_at, created_at)) >= datetime('now', ?)")
            params.append(f"-{max(1, min(lookback_days, 30))} days")
        params.append(max(1, min(limit, 100)))
        query = f"SELECT id FROM listings WHERE {' AND '.join(clauses)} ORDER BY created_at DESC LIMIT ?"
        with self.connection() as connection:
            rows = connection.execute(query, params).fetchall()
        return [listing for row in rows if (listing := self.get_listing(row["id"]))]

    @staticmethod
    def _search_row(row: sqlite3.Row) -> dict[str, Any]:
        item = dict(row)
        for key in ("pets_allowed", "no_commission", "owner_only", "active"):
            item[key] = bool(item[key])
        return item

    @staticmethod
    def _listing_row(row: sqlite3.Row, photos: list[str]) -> dict[str, Any]:
        item = dict(row)
        item["pets_allowed"] = bool(item["pets_allowed"])
        item["owner_only"] = bool(item.get("owner_only", 0))
        item["photos"] = photos
        return item
