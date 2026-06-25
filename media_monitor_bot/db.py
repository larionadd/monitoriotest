from __future__ import annotations

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
class UserMonitoring:
    chat_id: int
    language_code: str
    country_code: str
    onboarding_completed: bool
    keywords: tuple[str, ...]
    stop_words: tuple[str, ...]
    plus_words: tuple[str, ...]
    full_text_enabled: bool
    disabled_source_urls: tuple[str, ...]
    custom_sources: tuple[Source, ...]


@dataclass(frozen=True)
class UserSettings:
    chat_id: int
    language_code: str
    country_code: str
    onboarding_completed: bool


class Database:
    def __init__(self, path: Path):
        self.path = path
        self.path.parent.mkdir(parents=True, exist_ok=True)

    @contextmanager
    def connect(self):
        conn = sqlite3.connect(self.path)
        conn.row_factory = sqlite3.Row
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
                    title TEXT NOT NULL,
                    published_at TEXT,
                    summary TEXT,
                    first_seen_at TEXT NOT NULL
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
            user_source_columns = {
                row["name"]
                for row in conn.execute("PRAGMA table_info(user_sources)")
            }
            if "country_code" not in user_source_columns:
                conn.execute(
                    "ALTER TABLE user_sources ADD COLUMN country_code TEXT NOT NULL DEFAULT 'ua'"
                )

    def touch_user(self, chat_id: int, onboarding_completed_default: bool = True) -> None:
        now = utcnow()
        with self.connect() as conn:
            conn.execute(
                """
                INSERT INTO users(
                    chat_id,
                    created_at,
                    last_seen_at,
                    language_code,
                    country_code,
                    onboarding_completed
                )
                VALUES(?, ?, ?, ?, ?, ?)
                ON CONFLICT(chat_id) DO UPDATE SET last_seen_at = excluded.last_seen_at
                """,
                (
                    chat_id,
                    now,
                    now,
                    DEFAULT_LANGUAGE,
                    DEFAULT_COUNTRY,
                    1 if onboarding_completed_default else 0,
                ),
            )

    def get_user_settings(self, chat_id: int) -> UserSettings:
        self.touch_user(chat_id)
        with self.connect() as conn:
            row = conn.execute(
                "SELECT language_code, country_code, onboarding_completed FROM users WHERE chat_id = ?",
                (chat_id,),
            ).fetchone()
        return UserSettings(
            chat_id=chat_id,
            language_code=normalize_language(row["language_code"] if row else DEFAULT_LANGUAGE),
            country_code=normalize_country(row["country_code"] if row else DEFAULT_COUNTRY),
            onboarding_completed=bool(row["onboarding_completed"]) if row else True,
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

    def add_keyword(self, chat_id: int, phrase: str) -> bool:
        return self._add_term("keywords", chat_id, phrase)

    def set_full_text_enabled(self, chat_id: int, enabled: bool) -> None:
        self.touch_user(chat_id)
        with self.connect() as conn:
            conn.execute(
                "UPDATE users SET full_text_enabled = ? WHERE chat_id = ?",
                (1 if enabled else 0, chat_id),
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

    def remove_keyword(self, chat_id: int, phrase: str) -> bool:
        with self.connect() as conn:
            cur = conn.execute(
                "DELETE FROM keywords WHERE chat_id = ? AND phrase = ?",
                (chat_id, normalize_term(phrase)),
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
                "SELECT full_text_enabled, language_code, country_code, onboarding_completed FROM users WHERE chat_id = ?",
                (chat_id,),
            ).fetchone()
            full_text_enabled = bool(row["full_text_enabled"]) if row else False
            language_code = normalize_language(row["language_code"] if row else DEFAULT_LANGUAGE)
            country_code = normalize_country(row["country_code"] if row else DEFAULT_COUNTRY)
            onboarding_completed = bool(row["onboarding_completed"]) if row else True
            keywords = tuple(
                row["phrase"]
                for row in conn.execute(
                    "SELECT phrase FROM keywords WHERE chat_id = ? ORDER BY phrase", (chat_id,)
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
            keywords,
            stop_words,
            plus_words,
            full_text_enabled,
            disabled_source_urls,
            custom_sources,
        )

    def get_enabled_sources(self, chat_id: int, default_sources: list[Source]) -> list[Source]:
        monitoring = self.get_user_monitoring(chat_id)
        plan = self.get_active_plan(chat_id)
        disabled = set(monitoring.disabled_source_urls)
        sources = [
            source
            for source in default_sources
            if normalize_url(source.url) not in disabled
            and source_allowed_for_plan(source, plan.id)
            and normalize_country(source.country) == monitoring.country_code
        ]
        sources.extend(
            source
            for source in monitoring.custom_sources[: plan.max_custom_sources]
            if normalize_country(source.country) == monitoring.country_code
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

    def save_article(self, url: str, source: str, title: str, published_at: str, summary: str) -> None:
        with self.connect() as conn:
            conn.execute(
                """
                INSERT OR IGNORE INTO articles(url, source, title, published_at, summary, first_seen_at)
                VALUES(?, ?, ?, ?, ?, ?)
                """,
                (url, source, title, published_at, summary, utcnow()),
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

    def report_rows(self, chat_id: int, limit: int = 500) -> list[sqlite3.Row]:
        with self.connect() as conn:
            return list(
                conn.execute(
                    """
                    SELECT m.sent_at, m.keyword, a.source, a.title, a.published_at, a.url
                    FROM matches m
                    JOIN articles a ON a.url = m.url
                    WHERE m.chat_id = ?
                    ORDER BY m.sent_at DESC
                    LIMIT ?
                    """,
                    (chat_id, limit),
                )
            )


def normalize_term(value: str) -> str:
    return " ".join(value.strip().lower().split())


def normalize_url(value: str) -> str:
    return value.strip()


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


def source_allowed_for_plan(source: Source, plan_id: str) -> bool:
    return source.type != "telegram_paid" or plan_id != "free"
