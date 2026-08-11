from __future__ import annotations

import json
import sqlite3
from collections.abc import Iterable
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path

from .billing import PLANS, Plan, is_subscription_active, plan_by_id
from .config import Source
from .locales import DEFAULT_COUNTRY, DEFAULT_LANGUAGE, normalize_country, normalize_language


def utcnow() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


@dataclass(frozen=True)
class KeywordTerm:
    phrase: str
    country_code: str
    paused: bool = False
    silent: bool = False


@dataclass(frozen=True)
class UserMonitoring:
    chat_id: int
    language_code: str
    country_code: str
    onboarding_completed: bool
    auto_monitoring_enabled: bool
    monitor_interval_minutes: int
    last_auto_check_at: str
    keywords: tuple[KeywordTerm, ...]
    stop_words: tuple[str, ...]
    plus_words: tuple[str, ...]
    full_text_enabled: bool
    importance_rating_enabled: bool
    threads_search_enabled: bool
    threads_search_hours: int
    threads_media_filter: str
    threads_link_filter: str
    threads_result_limit: int
    threads_search_type: str
    disabled_source_urls: tuple[str, ...]
    custom_sources: tuple[Source, ...]


@dataclass(frozen=True)
class UserSettings:
    chat_id: int
    language_code: str
    country_code: str
    onboarding_completed: bool
    auto_monitoring_enabled: bool
    monitor_interval_minutes: int
    last_auto_check_at: str
    importance_rating_enabled: bool


class Database:
    def __init__(self, path: Path):
        self.path = path
        self.path.parent.mkdir(parents=True, exist_ok=True)

    @contextmanager
    def connect(self):
        conn = sqlite3.connect(self.path, timeout=10)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA busy_timeout=10000")
        try:
            yield conn
            conn.commit()
        finally:
            conn.close()

    def migrate(self) -> None:
        with self.connect() as conn:
            conn.executescript(
                """
                PRAGMA journal_mode = WAL;

                CREATE TABLE IF NOT EXISTS users (
                    chat_id INTEGER PRIMARY KEY,
                    created_at TEXT NOT NULL,
                    last_seen_at TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS keywords (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    chat_id INTEGER NOT NULL,
                    phrase TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    UNIQUE(chat_id, phrase),
                    FOREIGN KEY(chat_id) REFERENCES users(chat_id) ON DELETE CASCADE
                );

                CREATE TABLE IF NOT EXISTS stop_words (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    chat_id INTEGER NOT NULL,
                    word TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    UNIQUE(chat_id, word),
                    FOREIGN KEY(chat_id) REFERENCES users(chat_id) ON DELETE CASCADE
                );

                CREATE TABLE IF NOT EXISTS plus_words (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    chat_id INTEGER NOT NULL,
                    word TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    UNIQUE(chat_id, word),
                    FOREIGN KEY(chat_id) REFERENCES users(chat_id) ON DELETE CASCADE
                );

                CREATE TABLE IF NOT EXISTS articles (
                    url TEXT PRIMARY KEY,
                    source TEXT NOT NULL,
                    source_type TEXT NOT NULL DEFAULT '',
                    title TEXT NOT NULL,
                    published_at TEXT,
                    summary TEXT,
                    first_seen_at TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS article_full_texts (
                    url TEXT PRIMARY KEY,
                    text TEXT NOT NULL,
                    fetched_at TEXT NOT NULL,
                    FOREIGN KEY(url) REFERENCES articles(url) ON DELETE CASCADE
                );

                CREATE TABLE IF NOT EXISTS matches (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    chat_id INTEGER NOT NULL,
                    keyword TEXT NOT NULL,
                    url TEXT NOT NULL,
                    sent_at TEXT NOT NULL,
                    UNIQUE(chat_id, keyword, url)
                );

                CREATE INDEX IF NOT EXISTS idx_matches_chat_sent
                    ON matches(chat_id, sent_at);

                CREATE TABLE IF NOT EXISTS user_disabled_sources (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    chat_id INTEGER NOT NULL,
                    url TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    UNIQUE(chat_id, url),
                    FOREIGN KEY(chat_id) REFERENCES users(chat_id) ON DELETE CASCADE
                );

                CREATE TABLE IF NOT EXISTS user_sources (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    chat_id INTEGER NOT NULL,
                    name TEXT NOT NULL,
                    url TEXT NOT NULL,
                    type TEXT NOT NULL DEFAULT 'rss',
                    created_at TEXT NOT NULL,
                    UNIQUE(chat_id, url),
                    FOREIGN KEY(chat_id) REFERENCES users(chat_id) ON DELETE CASCADE
                );

                CREATE TABLE IF NOT EXISTS subscriptions (
                    chat_id INTEGER PRIMARY KEY,
                    plan_id TEXT NOT NULL,
                    starts_at TEXT NOT NULL,
                    expires_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    FOREIGN KEY(chat_id) REFERENCES users(chat_id) ON DELETE CASCADE
                );

                CREATE TABLE IF NOT EXISTS payments (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    chat_id INTEGER NOT NULL,
                    plan_id TEXT NOT NULL,
                    currency TEXT NOT NULL,
                    total_amount INTEGER NOT NULL,
                    invoice_payload TEXT NOT NULL,
                    telegram_payment_charge_id TEXT,
                    provider_payment_charge_id TEXT,
                    paid_at TEXT NOT NULL,
                    UNIQUE(telegram_payment_charge_id)
                );

                CREATE TABLE IF NOT EXISTS crypto_payments (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    order_id TEXT NOT NULL UNIQUE,
                    chat_id INTEGER NOT NULL,
                    plan_id TEXT NOT NULL,
                    provider TEXT NOT NULL,
                    price_amount TEXT NOT NULL,
                    price_currency TEXT NOT NULL,
                    provider_invoice_id TEXT,
                    invoice_url TEXT NOT NULL,
                    status TEXT NOT NULL,
                    provider_payment_id TEXT,
                    raw_payload TEXT,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    paid_at TEXT,
                    FOREIGN KEY(chat_id) REFERENCES users(chat_id) ON DELETE CASCADE
                );

                CREATE TABLE IF NOT EXISTS subscription_notifications (
                    chat_id INTEGER NOT NULL,
                    plan_id TEXT NOT NULL,
                    expires_at TEXT NOT NULL,
                    kind TEXT NOT NULL,
                    sent_at TEXT NOT NULL,
                    PRIMARY KEY(chat_id, plan_id, expires_at, kind),
                    FOREIGN KEY(chat_id) REFERENCES users(chat_id) ON DELETE CASCADE
                );

                CREATE TABLE IF NOT EXISTS promo_redemptions (
                    chat_id INTEGER NOT NULL,
                    code TEXT NOT NULL,
                    redeemed_at TEXT NOT NULL,
                    PRIMARY KEY(chat_id, code),
                    FOREIGN KEY(chat_id) REFERENCES users(chat_id) ON DELETE CASCADE
                );

                CREATE TABLE IF NOT EXISTS ai_digests (
                    chat_id INTEGER PRIMARY KEY,
                    digest_json TEXT NOT NULL,
                    params_json TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    FOREIGN KEY(chat_id) REFERENCES users(chat_id) ON DELETE CASCADE
                );
                """
            )
            columns = {
                row["name"]
                for row in conn.execute("PRAGMA table_info(users)")
            }
            if "full_text_enabled" not in columns:
                conn.execute(
                    "ALTER TABLE users ADD COLUMN full_text_enabled INTEGER NOT NULL DEFAULT 0"
                )
            if "language_code" not in columns:
                conn.execute(
                    "ALTER TABLE users ADD COLUMN language_code TEXT NOT NULL DEFAULT 'en'"
                )
            if "country_code" not in columns:
                conn.execute(
                    "ALTER TABLE users ADD COLUMN country_code TEXT NOT NULL DEFAULT 'ua'"
                )
            if "onboarding_completed" not in columns:
                conn.execute(
                    "ALTER TABLE users ADD COLUMN onboarding_completed INTEGER NOT NULL DEFAULT 1"
                )
            if "auto_monitoring_enabled" not in columns:
                conn.execute(
                    "ALTER TABLE users ADD COLUMN auto_monitoring_enabled INTEGER NOT NULL DEFAULT 1"
                )
            if "monitor_interval_minutes" not in columns:
                conn.execute(
                    "ALTER TABLE users ADD COLUMN monitor_interval_minutes INTEGER NOT NULL DEFAULT 0"
                )
            if "last_auto_check_at" not in columns:
                conn.execute(
                    "ALTER TABLE users ADD COLUMN last_auto_check_at TEXT NOT NULL DEFAULT ''"
                )
            if "threads_search_enabled" not in columns:
                conn.execute(
                    "ALTER TABLE users ADD COLUMN threads_search_enabled INTEGER NOT NULL DEFAULT 0"
                )
            if "importance_rating_enabled" not in columns:
                conn.execute(
                    "ALTER TABLE users ADD COLUMN importance_rating_enabled INTEGER NOT NULL DEFAULT 0"
                )
            if "threads_search_hours" not in columns:
                conn.execute(
                    "ALTER TABLE users ADD COLUMN threads_search_hours INTEGER NOT NULL DEFAULT 24"
                )
            if "threads_media_filter" not in columns:
                conn.execute(
                    "ALTER TABLE users ADD COLUMN threads_media_filter TEXT NOT NULL DEFAULT 'any'"
                )
            if "threads_link_filter" not in columns:
                conn.execute(
                    "ALTER TABLE users ADD COLUMN threads_link_filter TEXT NOT NULL DEFAULT 'any'"
                )
            if "threads_result_limit" not in columns:
                conn.execute(
                    "ALTER TABLE users ADD COLUMN threads_result_limit INTEGER NOT NULL DEFAULT 15"
                )
            if "threads_search_type" not in columns:
                conn.execute(
                    "ALTER TABLE users ADD COLUMN threads_search_type TEXT NOT NULL DEFAULT 'RECENT'"
                )
            article_columns = {
                row["name"]
                for row in conn.execute("PRAGMA table_info(articles)")
            }
            if "source_type" not in article_columns:
                conn.execute(
                    "ALTER TABLE articles ADD COLUMN source_type TEXT NOT NULL DEFAULT ''"
                )
            user_source_columns = {
                row["name"]
                for row in conn.execute("PRAGMA table_info(user_sources)")
            }
            if "country_code" not in user_source_columns:
                conn.execute(
                    "ALTER TABLE user_sources ADD COLUMN country_code TEXT NOT NULL DEFAULT 'ua'"
                )
            keyword_columns = {
                row["name"]
                for row in conn.execute("PRAGMA table_info(keywords)")
            }
            if "country_code" not in keyword_columns or not self._keywords_unique_has_country(conn):
                self._rebuild_keywords_table(conn)
                keyword_columns = {
                    row["name"]
                    for row in conn.execute("PRAGMA table_info(keywords)")
                }
            if "paused" not in keyword_columns:
                conn.execute(
                    "ALTER TABLE keywords ADD COLUMN paused INTEGER NOT NULL DEFAULT 0"
                )
            if "silent" not in keyword_columns:
                conn.execute(
                    "ALTER TABLE keywords ADD COLUMN silent INTEGER NOT NULL DEFAULT 0"
                )

    def _keywords_unique_has_country(self, conn: sqlite3.Connection) -> bool:
        for index in conn.execute("PRAGMA index_list(keywords)"):
            if not index["unique"]:
                continue
            columns = [
                row["name"]
                for row in conn.execute(f"PRAGMA index_info({index['name']})")
            ]
            if columns == ["chat_id", "phrase", "country_code"]:
                return True
        return False

    def _rebuild_keywords_table(self, conn: sqlite3.Connection) -> None:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS keywords_new (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                chat_id INTEGER NOT NULL,
                phrase TEXT NOT NULL,
                country_code TEXT NOT NULL DEFAULT 'ua',
                created_at TEXT NOT NULL,
                paused INTEGER NOT NULL DEFAULT 0,
                silent INTEGER NOT NULL DEFAULT 0,
                UNIQUE(chat_id, phrase, country_code),
                FOREIGN KEY(chat_id) REFERENCES users(chat_id) ON DELETE CASCADE
            )
            """
        )
        keyword_columns = {
            row["name"]
            for row in conn.execute("PRAGMA table_info(keywords)")
        }
        country_expr = (
            "COALESCE(NULLIF(k.country_code, ''), NULLIF(u.country_code, ''), 'ua')"
            if "country_code" in keyword_columns
            else "COALESCE(NULLIF(u.country_code, ''), 'ua')"
        )
        paused_expr = "COALESCE(k.paused, 0)" if "paused" in keyword_columns else "0"
        silent_expr = "COALESCE(k.silent, 0)" if "silent" in keyword_columns else "0"
        conn.execute(
            f"""
            INSERT OR IGNORE INTO keywords_new(chat_id, phrase, country_code, created_at, paused, silent)
            SELECT k.chat_id, k.phrase, {country_expr}, k.created_at, {paused_expr}, {silent_expr}
            FROM keywords k
            LEFT JOIN users u ON u.chat_id = k.chat_id
            """
        )
        conn.execute("DROP TABLE keywords")
        conn.execute("ALTER TABLE keywords_new RENAME TO keywords")

    def touch_user(
        self,
        chat_id: int,
        onboarding_completed_default: bool = True,
        preferred_language_code: str | None = None,
    ) -> None:
        now = utcnow()
        language_code = normalize_language(preferred_language_code or DEFAULT_LANGUAGE)
        with self.connect() as conn:
            conn.execute(
                """
                INSERT INTO users(
                    chat_id,
                    created_at,
                    last_seen_at,
                    language_code,
                    country_code,
                    onboarding_completed,
                    auto_monitoring_enabled,
                    monitor_interval_minutes,
                    last_auto_check_at
                )
                VALUES(?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(chat_id) DO UPDATE SET last_seen_at = excluded.last_seen_at
                """,
                (
                    chat_id,
                    now,
                    now,
                    language_code,
                    DEFAULT_COUNTRY,
                    1 if onboarding_completed_default else 0,
                    1,
                    0,
                    "",
                ),
            )

    def get_user_settings(self, chat_id: int) -> UserSettings:
        self.touch_user(chat_id)
        with self.connect() as conn:
            row = conn.execute(
                """
                SELECT language_code, country_code, onboarding_completed, auto_monitoring_enabled, monitor_interval_minutes, last_auto_check_at, importance_rating_enabled
                FROM users
                WHERE chat_id = ?
                """,
                (chat_id,),
            ).fetchone()
        return UserSettings(
            chat_id=chat_id,
            language_code=normalize_language(row["language_code"] if row else DEFAULT_LANGUAGE),
            country_code=normalize_country(row["country_code"] if row else DEFAULT_COUNTRY),
            onboarding_completed=bool(row["onboarding_completed"]) if row else True,
            auto_monitoring_enabled=bool(row["auto_monitoring_enabled"]) if row else True,
            monitor_interval_minutes=int(row["monitor_interval_minutes"] or 0) if row else 0,
            last_auto_check_at=str(row["last_auto_check_at"] or "") if row else "",
            importance_rating_enabled=bool(row["importance_rating_enabled"]) if row else False,
        )

    def set_language(self, chat_id: int, language_code: str) -> None:
        self.touch_user(chat_id)
        with self.connect() as conn:
            conn.execute(
                "UPDATE users SET language_code = ? WHERE chat_id = ?",
                (normalize_language(language_code), chat_id),
            )

    def set_country(self, chat_id: int, country_code: str) -> None:
        self.touch_user(chat_id)
        with self.connect() as conn:
            conn.execute(
                "UPDATE users SET country_code = ? WHERE chat_id = ?",
                (normalize_country(country_code), chat_id),
            )

    def set_onboarding_completed(self, chat_id: int, completed: bool) -> None:
        self.touch_user(chat_id)
        with self.connect() as conn:
            conn.execute(
                "UPDATE users SET onboarding_completed = ? WHERE chat_id = ?",
                (1 if completed else 0, chat_id),
            )

    def set_auto_monitoring_enabled(self, chat_id: int, enabled: bool) -> None:
        self.touch_user(chat_id)
        with self.connect() as conn:
            conn.execute(
                "UPDATE users SET auto_monitoring_enabled = ? WHERE chat_id = ?",
                (1 if enabled else 0, chat_id),
            )

    def set_monitor_interval_minutes(self, chat_id: int, minutes: int) -> None:
        self.touch_user(chat_id)
        safe_minutes = max(5, min(1440, int(minutes)))
        with self.connect() as conn:
            conn.execute(
                "UPDATE users SET monitor_interval_minutes = ? WHERE chat_id = ?",
                (safe_minutes, chat_id),
            )

    def mark_auto_checked(self, chat_ids: Iterable[int], checked_at: str | None = None) -> None:
        ids = [int(chat_id) for chat_id in chat_ids]
        if not ids:
            return
        timestamp = checked_at or utcnow()
        with self.connect() as conn:
            conn.executemany(
                "UPDATE users SET last_auto_check_at = ? WHERE chat_id = ?",
                [(timestamp, chat_id) for chat_id in ids],
            )

    def add_keyword(self, chat_id: int, phrase: str, country_code: str | None = None) -> bool:
        term = normalize_term(phrase)
        if not term:
            return False
        self.touch_user(chat_id)
        country = normalize_country(country_code or self.get_user_settings(chat_id).country_code)
        with self.connect() as conn:
            cur = conn.execute(
                """
                INSERT OR IGNORE INTO keywords(chat_id, phrase, country_code, created_at)
                VALUES(?, ?, ?, ?)
                """,
                (chat_id, term, country, utcnow()),
            )
            return cur.rowcount > 0

    def active_keyword_count(self, chat_id: int) -> int:
        self.touch_user(chat_id)
        with self.connect() as conn:
            row = conn.execute(
                "SELECT COUNT(*) AS count FROM keywords WHERE chat_id = ? AND paused = 0",
                (chat_id,),
            ).fetchone()
            return int(row["count"] if row else 0)

    def set_keyword_paused(
        self,
        chat_id: int,
        phrase: str,
        country_code: str | None,
        paused: bool,
    ) -> bool:
        return self._set_keyword_flag(chat_id, phrase, country_code, "paused", paused)

    def set_keyword_silent(
        self,
        chat_id: int,
        phrase: str,
        country_code: str | None,
        silent: bool,
    ) -> bool:
        return self._set_keyword_flag(chat_id, phrase, country_code, "silent", silent)

    def keyword_is_silent(
        self,
        chat_id: int,
        phrase: str,
        country_code: str | None = None,
    ) -> bool:
        term = normalize_term(phrase)
        if not term:
            return False
        params: list[object] = [chat_id, term]
        country_clause = ""
        if country_code:
            country_clause = " AND country_code = ?"
            params.append(normalize_country(country_code))
        with self.connect() as conn:
            row = conn.execute(
                f"""
                SELECT 1
                FROM keywords
                WHERE chat_id = ?
                  AND phrase = ?
                  AND silent = 1
                  {country_clause}
                LIMIT 1
                """,
                params,
            ).fetchone()
            return row is not None

    def _set_keyword_flag(
        self,
        chat_id: int,
        phrase: str,
        country_code: str | None,
        column: str,
        enabled: bool,
    ) -> bool:
        if column not in {"paused", "silent"}:
            raise ValueError(f"Unsupported keyword flag: {column}")
        term = normalize_term(phrase)
        if not term:
            return False
        country = normalize_country(country_code or self.get_user_settings(chat_id).country_code)
        with self.connect() as conn:
            cur = conn.execute(
                f"UPDATE keywords SET {column} = ? WHERE chat_id = ? AND phrase = ? AND country_code = ?",
                (1 if enabled else 0, chat_id, term, country),
            )
            return cur.rowcount > 0

    def set_full_text_enabled(self, chat_id: int, enabled: bool) -> None:
        self.touch_user(chat_id)
        with self.connect() as conn:
            conn.execute(
                "UPDATE users SET full_text_enabled = ? WHERE chat_id = ?",
                (1 if enabled else 0, chat_id),
            )

    def set_importance_rating_enabled(self, chat_id: int, enabled: bool) -> None:
        self.touch_user(chat_id)
        with self.connect() as conn:
            conn.execute(
                "UPDATE users SET importance_rating_enabled = ? WHERE chat_id = ?",
                (1 if enabled else 0, chat_id),
            )

    def set_threads_settings(
        self,
        chat_id: int,
        enabled: bool | None = None,
        hours: int | None = None,
        media_filter: str | None = None,
        link_filter: str | None = None,
        result_limit: int | None = None,
        search_type: str | None = None,
    ) -> None:
        self.touch_user(chat_id)
        assignments: list[str] = []
        params: list[object] = []
        if enabled is not None:
            assignments.append("threads_search_enabled = ?")
            params.append(1 if enabled else 0)
        if hours is not None:
            assignments.append("threads_search_hours = ?")
            params.append(clamp_int(hours, 1, 24, 24))
        if media_filter is not None:
            assignments.append("threads_media_filter = ?")
            params.append(normalize_choice(media_filter, {"any", "media", "no_media"}, "any"))
        if link_filter is not None:
            assignments.append("threads_link_filter = ?")
            params.append(normalize_choice(link_filter, {"any", "link", "no_link"}, "any"))
        if result_limit is not None:
            assignments.append("threads_result_limit = ?")
            params.append(clamp_int(result_limit, 1, 100, 15))
        if search_type is not None:
            assignments.append("threads_search_type = ?")
            params.append(normalize_choice(search_type, {"RECENT", "TOP"}, "RECENT"))
        if not assignments:
            return
        params.append(chat_id)
        with self.connect() as conn:
            conn.execute(
                f"UPDATE users SET {', '.join(assignments)} WHERE chat_id = ?",
                params,
            )

    def get_active_plan(self, chat_id: int) -> Plan:
        with self.connect() as conn:
            row = conn.execute(
                "SELECT plan_id, expires_at FROM subscriptions WHERE chat_id = ?",
                (chat_id,),
            ).fetchone()
        if row and is_subscription_active(row["expires_at"]):
            return plan_by_id(row["plan_id"])
        return PLANS["free"]

    def get_subscription(self, chat_id: int) -> sqlite3.Row | None:
        with self.connect() as conn:
            return conn.execute(
                "SELECT plan_id, starts_at, expires_at, updated_at FROM subscriptions WHERE chat_id = ?",
                (chat_id,),
            ).fetchone()

    def activate_plan(self, chat_id: int, plan_id: str, days: int | None = None) -> str:
        plan = plan_by_id(plan_id)
        if plan.id == "free":
            raise ValueError("free plan cannot be activated as a paid subscription")
        self.touch_user(chat_id)
        now_dt = datetime.now(timezone.utc).replace(microsecond=0)
        current = self.get_subscription(chat_id)
        if current and current["plan_id"] == plan.id and is_subscription_active(current["expires_at"]):
            starts_dt = datetime.fromisoformat(current["expires_at"])
            if starts_dt.tzinfo is None:
                starts_dt = starts_dt.replace(tzinfo=timezone.utc)
        else:
            starts_dt = now_dt
        expires_dt = starts_dt + timedelta(days=days or plan.days)
        now = now_dt.isoformat()
        expires = expires_dt.isoformat()
        with self.connect() as conn:
            conn.execute(
                """
                INSERT INTO subscriptions(chat_id, plan_id, starts_at, expires_at, updated_at)
                VALUES(?, ?, ?, ?, ?)
                ON CONFLICT(chat_id) DO UPDATE SET
                    plan_id = excluded.plan_id,
                    starts_at = excluded.starts_at,
                    expires_at = excluded.expires_at,
                    updated_at = excluded.updated_at
                """,
                (chat_id, plan.id, now, expires, now),
            )
        return expires

    def activate_promo_plan(self, chat_id: int, code: str, plan_id: str, days: int) -> str | None:
        plan = plan_by_id(plan_id)
        if plan.id == "free":
            raise ValueError("free plan cannot be activated as a paid subscription")
        normalized_code = code.strip().upper()
        if not normalized_code:
            return None
        self.touch_user(chat_id)
        now_dt = datetime.now(timezone.utc).replace(microsecond=0)
        now = now_dt.isoformat()
        with self.connect() as conn:
            try:
                conn.execute(
                    """
                    INSERT INTO promo_redemptions(chat_id, code, redeemed_at)
                    VALUES(?, ?, ?)
                    """,
                    (chat_id, normalized_code, now),
                )
            except sqlite3.IntegrityError:
                return None
            current = conn.execute(
                "SELECT plan_id, expires_at FROM subscriptions WHERE chat_id = ?",
                (chat_id,),
            ).fetchone()
            if current and current["plan_id"] == plan.id and is_subscription_active(current["expires_at"]):
                starts_dt = datetime.fromisoformat(current["expires_at"])
                if starts_dt.tzinfo is None:
                    starts_dt = starts_dt.replace(tzinfo=timezone.utc)
            else:
                starts_dt = now_dt
            expires_dt = starts_dt + timedelta(days=days)
            expires = expires_dt.isoformat()
            conn.execute(
                """
                INSERT INTO subscriptions(chat_id, plan_id, starts_at, expires_at, updated_at)
                VALUES(?, ?, ?, ?, ?)
                ON CONFLICT(chat_id) DO UPDATE SET
                    plan_id = excluded.plan_id,
                    starts_at = excluded.starts_at,
                    expires_at = excluded.expires_at,
                    updated_at = excluded.updated_at
                """,
                (chat_id, plan.id, now, expires, now),
            )
        return expires

    def subscriptions_expiring_for_reminder(self, now: str, until: str) -> list[sqlite3.Row]:
        with self.connect() as conn:
            return list(
                conn.execute(
                    """
                    SELECT s.chat_id, s.plan_id, s.expires_at
                    FROM subscriptions s
                    WHERE s.plan_id != 'free'
                      AND s.expires_at > ?
                      AND s.expires_at <= ?
                      AND NOT EXISTS (
                          SELECT 1
                          FROM subscription_notifications n
                          WHERE n.chat_id = s.chat_id
                            AND n.plan_id = s.plan_id
                            AND n.expires_at = s.expires_at
                            AND n.kind = 'reminder_1d'
                      )
                    """,
                    (now, until),
                )
            )

    def subscriptions_expired_for_notice(self, since: str, now: str) -> list[sqlite3.Row]:
        with self.connect() as conn:
            return list(
                conn.execute(
                    """
                    SELECT s.chat_id, s.plan_id, s.expires_at
                    FROM subscriptions s
                    WHERE s.plan_id != 'free'
                      AND s.expires_at >= ?
                      AND s.expires_at <= ?
                      AND NOT EXISTS (
                          SELECT 1
                          FROM subscription_notifications n
                          WHERE n.chat_id = s.chat_id
                            AND n.plan_id = s.plan_id
                            AND n.expires_at = s.expires_at
                            AND n.kind = 'expired'
                      )
                    """,
                    (since, now),
                )
            )

    def mark_subscription_notification(self, chat_id: int, plan_id: str, expires_at: str, kind: str) -> None:
        with self.connect() as conn:
            conn.execute(
                """
                INSERT OR IGNORE INTO subscription_notifications(chat_id, plan_id, expires_at, kind, sent_at)
                VALUES(?, ?, ?, ?, ?)
                """,
                (chat_id, plan_id, expires_at, kind, utcnow()),
            )

    def record_payment(
        self,
        chat_id: int,
        plan_id: str,
        currency: str,
        total_amount: int,
        invoice_payload: str,
        telegram_payment_charge_id: str | None,
        provider_payment_charge_id: str | None,
    ) -> bool:
        self.touch_user(chat_id)
        with self.connect() as conn:
            cur = conn.execute(
                """
                INSERT OR IGNORE INTO payments(
                    chat_id,
                    plan_id,
                    currency,
                    total_amount,
                    invoice_payload,
                    telegram_payment_charge_id,
                    provider_payment_charge_id,
                    paid_at
                )
                VALUES(?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    chat_id,
                    plan_id,
                    currency,
                    total_amount,
                    invoice_payload,
                    telegram_payment_charge_id,
                    provider_payment_charge_id,
                    utcnow(),
                ),
            )
            return cur.rowcount > 0

    def record_crypto_invoice(
        self,
        chat_id: int,
        plan_id: str,
        order_id: str,
        price_amount: str,
        price_currency: str,
        provider_invoice_id: str | None,
        invoice_url: str,
        raw_payload: str,
    ) -> None:
        self.touch_user(chat_id)
        now = utcnow()
        with self.connect() as conn:
            conn.execute(
                """
                INSERT INTO crypto_payments(
                    order_id,
                    chat_id,
                    plan_id,
                    provider,
                    price_amount,
                    price_currency,
                    provider_invoice_id,
                    invoice_url,
                    status,
                    raw_payload,
                    created_at,
                    updated_at
                )
                VALUES(?, ?, ?, 'nowpayments', ?, ?, ?, ?, 'created', ?, ?, ?)
                ON CONFLICT(order_id) DO UPDATE SET
                    provider_invoice_id = excluded.provider_invoice_id,
                    invoice_url = excluded.invoice_url,
                    raw_payload = excluded.raw_payload,
                    updated_at = excluded.updated_at
                """,
                (
                    order_id,
                    chat_id,
                    plan_id,
                    price_amount,
                    price_currency,
                    provider_invoice_id,
                    invoice_url,
                    raw_payload,
                    now,
                    now,
                ),
            )

    def get_crypto_payment_by_order_id(self, order_id: str) -> sqlite3.Row | None:
        with self.connect() as conn:
            return conn.execute(
                "SELECT * FROM crypto_payments WHERE order_id = ?",
                (order_id,),
            ).fetchone()

    def latest_crypto_payment(self, chat_id: int) -> sqlite3.Row | None:
        with self.connect() as conn:
            return conn.execute(
                """
                SELECT *
                FROM crypto_payments
                WHERE chat_id = ?
                ORDER BY created_at DESC, id DESC
                LIMIT 1
                """,
                (chat_id,),
            ).fetchone()

    def update_crypto_payment_status(
        self,
        order_id: str,
        status: str,
        provider_payment_id: str | None,
        raw_payload: str,
        paid: bool,
    ) -> tuple[sqlite3.Row | None, bool]:
        now = utcnow()
        with self.connect() as conn:
            row = conn.execute(
                "SELECT * FROM crypto_payments WHERE order_id = ?",
                (order_id,),
            ).fetchone()
            if row is None:
                return None, False
            newly_paid = bool(paid and not row["paid_at"])
            paid_at = now if newly_paid else row["paid_at"]
            conn.execute(
                """
                UPDATE crypto_payments
                SET status = ?,
                    provider_payment_id = COALESCE(?, provider_payment_id),
                    raw_payload = ?,
                    updated_at = ?,
                    paid_at = ?
                WHERE order_id = ?
                """,
                (status, provider_payment_id, raw_payload, now, paid_at, order_id),
            )
            updated = conn.execute(
                "SELECT * FROM crypto_payments WHERE order_id = ?",
                (order_id,),
            ).fetchone()
            return updated, newly_paid

    def disable_source(self, chat_id: int, url: str) -> bool:
        source_url = normalize_url(url)
        if not source_url:
            return False
        self.touch_user(chat_id)
        with self.connect() as conn:
            cur = conn.execute(
                """
                INSERT OR IGNORE INTO user_disabled_sources(chat_id, url, created_at)
                VALUES(?, ?, ?)
                """,
                (chat_id, source_url, utcnow()),
            )
            return cur.rowcount > 0

    def enable_source(self, chat_id: int, url: str) -> bool:
        source_url = normalize_url(url)
        with self.connect() as conn:
            cur = conn.execute(
                "DELETE FROM user_disabled_sources WHERE chat_id = ? AND url = ?",
                (chat_id, source_url),
            )
            return cur.rowcount > 0

    def disable_sources(self, chat_id: int, urls: list[str]) -> int:
        normalized_urls = [normalize_url(url) for url in urls]
        normalized_urls = [url for url in normalized_urls if url]
        if not normalized_urls:
            return 0
        self.touch_user(chat_id)
        with self.connect() as conn:
            before = conn.total_changes
            conn.executemany(
                """
                INSERT OR IGNORE INTO user_disabled_sources(chat_id, url, created_at)
                VALUES(?, ?, ?)
                """,
                [(chat_id, url, utcnow()) for url in normalized_urls],
            )
            return conn.total_changes - before

    def enable_sources(self, chat_id: int, urls: list[str]) -> int:
        normalized_urls = [normalize_url(url) for url in urls]
        normalized_urls = [url for url in normalized_urls if url]
        if not normalized_urls:
            return 0
        placeholders = ",".join("?" for _ in normalized_urls)
        with self.connect() as conn:
            cur = conn.execute(
                f"DELETE FROM user_disabled_sources WHERE chat_id = ? AND url IN ({placeholders})",
                [chat_id, *normalized_urls],
            )
            return cur.rowcount

    def add_user_source(self, chat_id: int, source: Source) -> bool:
        source_url = normalize_url(source.url)
        if not source.name.strip() or not source_url:
            return False
        self.touch_user(chat_id)
        with self.connect() as conn:
            cur = conn.execute(
                """
                    INSERT OR IGNORE INTO user_sources(chat_id, name, url, type, country_code, created_at)
                    VALUES(?, ?, ?, ?, ?, ?)
                """,
                (
                    chat_id,
                    source.name.strip(),
                    source_url,
                    source.type or "rss",
                    normalize_country(source.country),
                    utcnow(),
                ),
            )
            return cur.rowcount > 0

    def remove_user_source(self, chat_id: int, url: str) -> bool:
        source_url = normalize_url(url)
        with self.connect() as conn:
            cur = conn.execute(
                "DELETE FROM user_sources WHERE chat_id = ? AND url = ?",
                (chat_id, source_url),
            )
            return cur.rowcount > 0

    def remove_keyword(self, chat_id: int, phrase: str, country_code: str | None = None) -> bool:
        with self.connect() as conn:
            term = normalize_term(phrase)
            if country_code:
                cur = conn.execute(
                    "DELETE FROM keywords WHERE chat_id = ? AND phrase = ? AND country_code = ?",
                    (chat_id, term, normalize_country(country_code)),
                )
            else:
                cur = conn.execute(
                    "DELETE FROM keywords WHERE chat_id = ? AND phrase = ?",
                    (chat_id, term),
                )
            return cur.rowcount > 0

    def add_stop_word(self, chat_id: int, word: str) -> bool:
        return self._add_term("stop_words", chat_id, word)

    def remove_stop_word(self, chat_id: int, word: str) -> bool:
        return self._remove_term("stop_words", chat_id, word)

    def add_plus_word(self, chat_id: int, word: str) -> bool:
        return self._add_term("plus_words", chat_id, word)

    def remove_plus_word(self, chat_id: int, word: str) -> bool:
        return self._remove_term("plus_words", chat_id, word)

    def _add_term(self, table: str, chat_id: int, value: str) -> bool:
        term = normalize_term(value)
        if not term:
            return False
        self.touch_user(chat_id)
        with self.connect() as conn:
            cur = conn.execute(
                f"INSERT OR IGNORE INTO {table}(chat_id, {self._value_column(table)}, created_at) VALUES(?, ?, ?)",
                (chat_id, term, utcnow()),
            )
            return cur.rowcount > 0

    def _remove_term(self, table: str, chat_id: int, value: str) -> bool:
        term = normalize_term(value)
        with self.connect() as conn:
            cur = conn.execute(
                f"DELETE FROM {table} WHERE chat_id = ? AND {self._value_column(table)} = ?",
                (chat_id, term),
            )
            return cur.rowcount > 0

    @staticmethod
    def _value_column(table: str) -> str:
        return "phrase" if table == "keywords" else "word"

    def get_user_monitoring(self, chat_id: int) -> UserMonitoring:
        with self.connect() as conn:
            row = conn.execute(
                """
                SELECT
                    full_text_enabled,
                    language_code,
                    country_code,
                    onboarding_completed,
                    auto_monitoring_enabled,
                    monitor_interval_minutes,
                    last_auto_check_at,
                    importance_rating_enabled,
                    threads_search_enabled,
                    threads_search_hours,
                    threads_media_filter,
                    threads_link_filter,
                    threads_result_limit,
                    threads_search_type
                FROM users
                WHERE chat_id = ?
                """,
                (chat_id,),
            ).fetchone()
            full_text_enabled = bool(row["full_text_enabled"]) if row else False
            importance_rating_enabled = bool(row["importance_rating_enabled"]) if row else False
            language_code = normalize_language(row["language_code"] if row else DEFAULT_LANGUAGE)
            country_code = normalize_country(row["country_code"] if row else DEFAULT_COUNTRY)
            onboarding_completed = bool(row["onboarding_completed"]) if row else True
            auto_monitoring_enabled = bool(row["auto_monitoring_enabled"]) if row else True
            monitor_interval_minutes = int(row["monitor_interval_minutes"] or 0) if row else 0
            last_auto_check_at = str(row["last_auto_check_at"] or "") if row else ""
            threads_search_enabled = bool(row["threads_search_enabled"]) if row else False
            threads_search_hours = clamp_int(row["threads_search_hours"] if row else 24, 1, 24, 24)
            threads_media_filter = normalize_choice(
                row["threads_media_filter"] if row else "any",
                {"any", "media", "no_media"},
                "any",
            )
            threads_link_filter = normalize_choice(
                row["threads_link_filter"] if row else "any",
                {"any", "link", "no_link"},
                "any",
            )
            threads_result_limit = clamp_int(row["threads_result_limit"] if row else 15, 1, 100, 15)
            threads_search_type = normalize_choice(
                row["threads_search_type"] if row else "RECENT",
                {"RECENT", "TOP"},
                "RECENT",
            )
            keywords = tuple(
                KeywordTerm(
                    row["phrase"],
                    normalize_country(row["country_code"]),
                    bool(row["paused"]),
                    bool(row["silent"]),
                )
                for row in conn.execute(
                    "SELECT phrase, country_code, paused, silent FROM keywords WHERE chat_id = ? ORDER BY paused, country_code, phrase",
                    (chat_id,),
                )
            )
            stop_words = tuple(
                row["word"]
                for row in conn.execute(
                    "SELECT word FROM stop_words WHERE chat_id = ? ORDER BY word", (chat_id,)
                )
            )
            plus_words = tuple(
                row["word"]
                for row in conn.execute(
                    "SELECT word FROM plus_words WHERE chat_id = ? ORDER BY word", (chat_id,)
                )
            )
            disabled_source_urls = tuple(
                row["url"]
                for row in conn.execute(
                    "SELECT url FROM user_disabled_sources WHERE chat_id = ? ORDER BY url",
                    (chat_id,),
                )
            )
            custom_sources = tuple(
                Source(
                    row["name"],
                    row["url"],
                    row["type"],
                    country=normalize_country(row["country_code"]),
                )
                for row in conn.execute(
                    """
                    SELECT name, url, type, country_code
                    FROM user_sources
                    WHERE chat_id = ?
                    ORDER BY name, url
                    """,
                    (chat_id,),
                )
            )
        return UserMonitoring(
            chat_id,
            language_code,
            country_code,
            onboarding_completed,
            auto_monitoring_enabled,
            monitor_interval_minutes,
            last_auto_check_at,
            keywords,
            stop_words,
            plus_words,
            full_text_enabled,
            importance_rating_enabled,
            threads_search_enabled,
            threads_search_hours,
            threads_media_filter,
            threads_link_filter,
            threads_result_limit,
            threads_search_type,
            disabled_source_urls,
            custom_sources,
        )

    def get_enabled_sources(
        self,
        chat_id: int,
        default_sources: list[Source],
        country_codes: Iterable[str] | None = None,
    ) -> list[Source]:
        monitoring = self.get_user_monitoring(chat_id)
        plan = self.get_active_plan(chat_id)
        disabled = set(monitoring.disabled_source_urls)
        countries = (
            {normalize_country(country) for country in country_codes}
            if country_codes
            else {monitoring.country_code}
        )
        in_country = [
            source
            for source in default_sources
            if normalize_country(source.country) in countries
        ]
        free_urls = free_source_urls(in_country) if plan.id == "free" else None
        sources = [
            source
            for source in in_country
            if normalize_url(source.url) not in disabled
            and source_allowed_for_plan(source, plan.id, free_urls)
        ]
        sources.extend(
            source
            for source in monitoring.custom_sources[: plan.max_custom_sources]
            if normalize_country(source.country) in countries
            and normalize_url(source.url) not in disabled
        )
        return dedupe_sources(sources)

    def iter_monitoring_users(self) -> Iterable[UserMonitoring]:
        with self.connect() as conn:
            chat_ids = [row["chat_id"] for row in conn.execute("SELECT chat_id FROM users")]
        for chat_id in chat_ids:
            monitoring = self.get_user_monitoring(chat_id)
            if monitoring.keywords:
                yield monitoring

    def user_count(self) -> int:
        with self.connect() as conn:
            row = conn.execute("SELECT COUNT(*) AS c FROM users").fetchone()
            return int(row["c"])

    def list_users(self, limit: int = 30) -> list[sqlite3.Row]:
        with self.connect() as conn:
            return list(
                conn.execute(
                    """
                    SELECT
                        u.chat_id,
                        u.created_at,
                        u.last_seen_at,
                        s.plan_id,
                        s.expires_at,
                        (
                            SELECT COUNT(*)
                            FROM keywords k
                            WHERE k.chat_id = u.chat_id
                        ) AS keyword_count,
                        (
                            SELECT COUNT(*)
                            FROM user_sources us
                            WHERE us.chat_id = u.chat_id
                        ) AS custom_source_count
                    FROM users u
                    LEFT JOIN subscriptions s ON s.chat_id = u.chat_id
                    ORDER BY u.last_seen_at DESC
                    LIMIT ?
                    """,
                    (limit,),
                )
            )

    def list_user_keywords(self) -> list[sqlite3.Row]:
        with self.connect() as conn:
            return list(
                conn.execute(
                    """
                    SELECT
                        u.chat_id,
                        u.created_at AS user_created_at,
                        u.last_seen_at,
                        u.language_code,
                        u.country_code AS user_country_code,
                        s.plan_id,
                        s.expires_at,
                        k.phrase,
                        k.country_code AS keyword_country_code,
                        k.paused,
                        k.silent,
                        k.created_at AS keyword_created_at
                    FROM keywords k
                    JOIN users u ON u.chat_id = k.chat_id
                    LEFT JOIN subscriptions s ON s.chat_id = u.chat_id
                    ORDER BY u.last_seen_at DESC, k.paused, k.country_code, k.phrase
                    """
                )
            )

    def list_star_payments(self) -> list[sqlite3.Row]:
        with self.connect() as conn:
            return list(
                conn.execute(
                    """
                    SELECT
                        p.id,
                        p.chat_id,
                        p.plan_id,
                        p.currency,
                        p.total_amount,
                        p.invoice_payload,
                        p.telegram_payment_charge_id,
                        p.provider_payment_charge_id,
                        p.paid_at,
                        u.created_at AS user_created_at,
                        u.last_seen_at,
                        s.plan_id AS active_plan_id,
                        s.expires_at AS subscription_expires_at
                    FROM payments p
                    LEFT JOIN users u ON u.chat_id = p.chat_id
                    LEFT JOIN subscriptions s ON s.chat_id = p.chat_id
                    WHERE UPPER(p.currency) = 'XTR'
                    ORDER BY p.paid_at DESC, p.id DESC
                    """
                )
            )

    def list_crypto_payments(self) -> list[sqlite3.Row]:
        with self.connect() as conn:
            return list(
                conn.execute(
                    """
                    SELECT
                        cp.id,
                        cp.order_id,
                        cp.chat_id,
                        cp.plan_id,
                        cp.provider,
                        cp.price_amount,
                        cp.price_currency,
                        cp.provider_invoice_id,
                        cp.invoice_url,
                        cp.status,
                        cp.provider_payment_id,
                        cp.created_at,
                        cp.updated_at,
                        cp.paid_at,
                        u.created_at AS user_created_at,
                        u.last_seen_at,
                        s.plan_id AS active_plan_id,
                        s.expires_at AS subscription_expires_at
                    FROM crypto_payments cp
                    LEFT JOIN users u ON u.chat_id = cp.chat_id
                    LEFT JOIN subscriptions s ON s.chat_id = cp.chat_id
                    ORDER BY COALESCE(cp.paid_at, cp.updated_at, cp.created_at) DESC, cp.id DESC
                    """
                )
            )

    def save_article(
        self,
        url: str,
        source: str,
        title: str,
        published_at: str,
        summary: str,
        source_type: str = "",
    ) -> None:
        with self.connect() as conn:
            conn.execute(
                """
                INSERT INTO articles(url, source, source_type, title, published_at, summary, first_seen_at)
                VALUES(?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(url) DO UPDATE SET
                    source_type = CASE
                        WHEN articles.source_type = '' THEN excluded.source_type
                        ELSE articles.source_type
                    END
                """,
                (url, source, normalize_source_type(source_type), title, published_at, summary, utcnow()),
            )

    def get_article_full_text(self, url: str) -> str | None:
        with self.connect() as conn:
            row = conn.execute(
                "SELECT text FROM article_full_texts WHERE url = ?",
                (url,),
            ).fetchone()
            return None if row is None else str(row["text"])

    def save_article_full_text(self, url: str, text: str) -> None:
        with self.connect() as conn:
            conn.execute(
                """
                INSERT INTO article_full_texts(url, text, fetched_at)
                VALUES(?, ?, ?)
                ON CONFLICT(url) DO UPDATE SET
                    text = excluded.text,
                    fetched_at = excluded.fetched_at
                """,
                (url, text, utcnow()),
            )

    def already_sent(self, chat_id: int, keyword: str, url: str) -> bool:
        with self.connect() as conn:
            row = conn.execute(
                "SELECT 1 FROM matches WHERE chat_id = ? AND keyword = ? AND url = ?",
                (chat_id, keyword, url),
            ).fetchone()
            return row is not None

    def mark_sent(self, chat_id: int, keyword: str, url: str) -> None:
        with self.connect() as conn:
            conn.execute(
                """
                INSERT OR IGNORE INTO matches(chat_id, keyword, url, sent_at)
                VALUES(?, ?, ?, ?)
                """,
                (chat_id, keyword, url, utcnow()),
            )

    def sent_today_count(self, chat_id: int) -> int:
        today = datetime.now(timezone.utc).date().isoformat()
        with self.connect() as conn:
            row = conn.execute(
                "SELECT COUNT(*) AS c FROM matches WHERE chat_id = ? AND sent_at >= ?",
                (chat_id, today),
            ).fetchone()
            return int(row["c"])

    def report_rows(self, chat_id: int, limit: int = 500, since: str | None = None) -> list[sqlite3.Row]:
        where = "WHERE m.chat_id = ?"
        params: list[object] = [chat_id]
        if since:
            where += " AND m.sent_at >= ?"
            params.append(since)
        params.append(limit)
        with self.connect() as conn:
            return list(
                conn.execute(
                    f"""
                    SELECT m.sent_at, m.keyword, a.source, a.source_type, a.title, a.published_at, a.url
                    FROM matches m
                    JOIN articles a ON a.url = m.url
                    {where}
                    ORDER BY m.sent_at DESC
                    LIMIT ?
                    """,
                    params,
                )
            )

    def recent_matches(self, chat_id: int, limit: int = 30) -> list[sqlite3.Row]:
        with self.connect() as conn:
            return list(
                conn.execute(
                    """
                    SELECT
                        m.sent_at,
                        m.keyword,
                        a.source,
                        a.source_type,
                        a.title,
                        a.published_at,
                        a.url,
                        a.summary
                    FROM matches m
                    JOIN articles a ON a.url = m.url
                    WHERE m.chat_id = ?
                    ORDER BY m.sent_at DESC
                    LIMIT ?
                    """,
                    (chat_id, limit),
                )
            )

    def filtered_matches(
        self,
        chat_id: int,
        *,
        limit: int = 500,
        since: str | None = None,
        keyword: str | None = None,
        source: str | None = None,
        source_types: Iterable[str] | None = None,
    ) -> list[sqlite3.Row]:
        where = ["m.chat_id = ?"]
        params: list[object] = [chat_id]
        if since:
            where.append("m.sent_at >= ?")
            params.append(since)
        if keyword:
            where.append("m.keyword = ?")
            params.append(keyword)
        if source:
            where.append("a.source = ?")
            params.append(source)
        types = [normalize_source_type(value) for value in source_types or []]
        types = [value for value in types if value]
        if types:
            placeholders = ",".join("?" for _ in types)
            where.append(f"a.source_type IN ({placeholders})")
            params.extend(types)
        params.append(limit)
        with self.connect() as conn:
            return list(
                conn.execute(
                    f"""
                    SELECT
                        m.sent_at,
                        m.keyword,
                        a.source,
                        a.source_type,
                        a.title,
                        a.published_at,
                        a.url,
                        a.summary
                    FROM matches m
                    JOIN articles a ON a.url = m.url
                    WHERE {" AND ".join(where)}
                    ORDER BY m.sent_at DESC
                    LIMIT ?
                    """,
                    params,
                )
            )

    def digest_rows(self, chat_id: int, since: str, limit: int = 100) -> list[sqlite3.Row]:
        with self.connect() as conn:
            return list(
                conn.execute(
                    """
                    SELECT
                        m.sent_at,
                        m.keyword,
                        a.source,
                        a.source_type,
                        a.title,
                        a.published_at,
                        a.url,
                        a.summary
                    FROM matches m
                    JOIN articles a ON a.url = m.url
                    WHERE m.chat_id = ? AND m.sent_at >= ?
                    ORDER BY m.sent_at DESC
                    LIMIT ?
                    """,
                    (chat_id, since, limit),
                )
            )

    def save_ai_digest(self, chat_id: int, digest: dict, params: dict) -> None:
        with self.connect() as conn:
            conn.execute(
                """
                INSERT INTO ai_digests(chat_id, digest_json, params_json, created_at)
                VALUES(?, ?, ?, ?)
                ON CONFLICT(chat_id) DO UPDATE SET
                    digest_json = excluded.digest_json,
                    params_json = excluded.params_json,
                    created_at = excluded.created_at
                """,
                (
                    chat_id,
                    json.dumps(digest, ensure_ascii=False),
                    json.dumps(params, ensure_ascii=False),
                    utcnow(),
                ),
            )

    def latest_ai_digest(self, chat_id: int) -> sqlite3.Row | None:
        with self.connect() as conn:
            return conn.execute(
                """
                SELECT digest_json, params_json, created_at
                FROM ai_digests
                WHERE chat_id = ?
                """,
                (chat_id,),
            ).fetchone()


def normalize_term(value: str) -> str:
    return " ".join(value.strip().lower().split())


def normalize_url(value: str) -> str:
    return value.strip()


def clamp_int(value: object, minimum: int, maximum: int, fallback: int) -> int:
    try:
        number = int(value)
    except (TypeError, ValueError):
        number = fallback
    return max(minimum, min(maximum, number))


def normalize_choice(value: object, allowed: set[str], fallback: str) -> str:
    text = str(value or "").strip()
    if text in allowed:
        return text
    upper_allowed = {item for item in allowed if item.upper() == item}
    if text.upper() in upper_allowed:
        return text.upper()
    lower_allowed = {item.lower() for item in allowed}
    if text.lower() in lower_allowed:
        return text.lower()
    return fallback


def normalize_source_type(value: object) -> str:
    text = str(value or "").strip().lower()
    if text in {"rss", "telegram", "telegram_paid", "threads", "reddit"}:
        return "telegram" if text == "telegram_paid" else text
    return ""


def dedupe_sources(sources: Iterable[Source]) -> list[Source]:
    seen: set[str] = set()
    result: list[Source] = []
    for source in sources:
        url = normalize_url(source.url)
        if not url or url in seen:
            continue
        seen.add(url)
        result.append(
            Source(
                source.name,
                url,
                source.type or "rss",
                source.rank,
                source.subscribers,
                normalize_country(source.country),
                normalize_language(source.language) if source.language else "",
            )
        )
    return result


FREE_SOURCE_TOP_LIMIT = 20


def _source_kind(source: Source) -> str:
    if source.type in {"registry", "prozorro", "prozorro_plan", "prozorro_sale", "rada_bills"}:
        return "registry"
    return "tg" if source.type in {"telegram", "telegram_paid"} else "rss"


def _source_quality_key(source: Source) -> tuple[int, int]:
    rank = source.rank if source.rank is not None else 10**9
    subscribers = source.subscribers or 0
    return (rank, -subscribers)


def free_source_urls(sources: Iterable[Source], limit: int = FREE_SOURCE_TOP_LIMIT) -> set[str]:
    """URLs available on the free plan: top `limit` sources per (country, kind), ranked by quality."""
    groups: dict[tuple[str, str], list[Source]] = {}
    for source in sources:
        key = (normalize_country(source.country), _source_kind(source))
        groups.setdefault(key, []).append(source)
    allowed: set[str] = set()
    for items in groups.values():
        for source in sorted(items, key=_source_quality_key)[:limit]:
            allowed.add(normalize_url(source.url))
    return allowed


def source_allowed_for_plan(source: Source, plan_id: str, free_urls: set[str] | None = None) -> bool:
    """Business sees every source. Registries are Business-only; Free is limited to top sources."""
    if _source_kind(source) == "registry":
        return plan_id == "business"
    if plan_id != "free":
        return True
    if free_urls is not None:
        return normalize_url(source.url) in free_urls
    # Fallback when the ranked free set is not supplied (kept for backwards compatibility).
    return source.type != "telegram_paid"
