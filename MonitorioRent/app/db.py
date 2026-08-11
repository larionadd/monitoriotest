from __future__ import annotations

import sqlite3
from contextlib import contextmanager
from datetime import UTC, datetime
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
                """
            )

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
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 1, ?)
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
                    source, created_at, updated_at
                ) VALUES (?, ?, 'pending', ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'owner', ?, ?)
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
        price_max: int | None = None,
        rooms: int | None = None,
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
        if price_max is not None:
            clauses.append("price_uah <= ?")
            params.append(price_max)
        if rooms is not None:
            clauses.append("rooms = ?")
            params.append(rooms)
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
        item["photos"] = photos
        return item
