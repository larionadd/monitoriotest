from __future__ import annotations

import logging
import os
import sqlite3
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import requests

from .telegram_api import escape

log = logging.getLogger(__name__)


@dataclass(frozen=True)
class SupportConfig:
    token: str
    admin_chat_id: int
    database_path: Path
    poll_timeout: int = 30


class SupportTelegram:
    def __init__(self, token: str, timeout: int = 30):
        self.base_url = f"https://api.telegram.org/bot{token}"
        self.timeout = timeout

    def request(self, method: str, payload: dict[str, Any]) -> dict[str, Any]:
        response = requests.post(f"{self.base_url}/{method}", json=payload, timeout=self.timeout)
        response.raise_for_status()
        result = response.json()
        if not result.get("ok"):
            raise RuntimeError(result)
        return result["result"]

    def get_updates(self, offset: int | None, timeout: int) -> list[dict[str, Any]]:
        payload: dict[str, Any] = {"timeout": timeout, "allowed_updates": ["message"]}
        if offset is not None:
            payload["offset"] = offset
        response = requests.get(f"{self.base_url}/getUpdates", params=payload, timeout=timeout + 5)
        response.raise_for_status()
        result = response.json()
        if not result.get("ok"):
            raise RuntimeError(result)
        return result["result"]

    def send_message(self, chat_id: int, text: str, reply_to_message_id: int | None = None) -> int:
        payload: dict[str, Any] = {
            "chat_id": chat_id,
            "text": text,
            "parse_mode": "HTML",
            "disable_web_page_preview": True,
        }
        if reply_to_message_id:
            payload["reply_to_message_id"] = reply_to_message_id
            payload["allow_sending_without_reply"] = True
        message = self.request("sendMessage", payload)
        return int(message["message_id"])

    def copy_message(self, chat_id: int, from_chat_id: int, message_id: int) -> int:
        message = self.request(
            "copyMessage",
            {
                "chat_id": chat_id,
                "from_chat_id": from_chat_id,
                "message_id": message_id,
            },
        )
        return int(message["message_id"])


class SupportDatabase:
    def __init__(self, path: Path):
        self.path = path
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.init()

    def connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.path)
        conn.row_factory = sqlite3.Row
        return conn

    def init(self) -> None:
        with self.connect() as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS support_messages (
                    admin_chat_id INTEGER NOT NULL,
                    admin_message_id INTEGER NOT NULL,
                    user_chat_id INTEGER NOT NULL,
                    user_message_id INTEGER,
                    created_at INTEGER NOT NULL,
                    PRIMARY KEY(admin_chat_id, admin_message_id)
                )
                """
            )
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS support_users (
                    user_chat_id INTEGER PRIMARY KEY,
                    username TEXT,
                    first_name TEXT,
                    last_name TEXT,
                    last_seen INTEGER NOT NULL
                )
                """
            )
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS support_meta (
                    key TEXT PRIMARY KEY,
                    value TEXT NOT NULL
                )
                """
            )

    def offset(self) -> int | None:
        with self.connect() as conn:
            row = conn.execute("SELECT value FROM support_meta WHERE key = 'offset'").fetchone()
        return int(row["value"]) if row else None

    def set_offset(self, offset: int) -> None:
        with self.connect() as conn:
            conn.execute(
                """
                INSERT INTO support_meta(key, value) VALUES('offset', ?)
                ON CONFLICT(key) DO UPDATE SET value = excluded.value
                """,
                (str(offset),),
            )

    def save_user(self, user: dict[str, Any]) -> None:
        with self.connect() as conn:
            conn.execute(
                """
                INSERT INTO support_users(user_chat_id, username, first_name, last_name, last_seen)
                VALUES(?, ?, ?, ?, ?)
                ON CONFLICT(user_chat_id) DO UPDATE SET
                    username = excluded.username,
                    first_name = excluded.first_name,
                    last_name = excluded.last_name,
                    last_seen = excluded.last_seen
                """,
                (
                    int(user["id"]),
                    user.get("username") or "",
                    user.get("first_name") or "",
                    user.get("last_name") or "",
                    int(time.time()),
                ),
            )

    def map_admin_message(
        self,
        admin_chat_id: int,
        admin_message_id: int,
        user_chat_id: int,
        user_message_id: int | None,
    ) -> None:
        with self.connect() as conn:
            conn.execute(
                """
                INSERT OR REPLACE INTO support_messages(
                    admin_chat_id, admin_message_id, user_chat_id, user_message_id, created_at
                )
                VALUES(?, ?, ?, ?, ?)
                """,
                (admin_chat_id, admin_message_id, user_chat_id, user_message_id, int(time.time())),
            )

    def user_for_admin_message(self, admin_chat_id: int, admin_message_id: int) -> sqlite3.Row | None:
        with self.connect() as conn:
            return conn.execute(
                """
                SELECT user_chat_id, user_message_id
                FROM support_messages
                WHERE admin_chat_id = ? AND admin_message_id = ?
                """,
                (admin_chat_id, admin_message_id),
            ).fetchone()


def load_support_config() -> SupportConfig:
    token = os.getenv("SUPPORT_BOT_TOKEN", "").strip()
    admin_chat_id = os.getenv("SUPPORT_ADMIN_CHAT_ID", "").strip()
    if not token:
        raise RuntimeError("Set SUPPORT_BOT_TOKEN")
    if not admin_chat_id:
        raise RuntimeError("Set SUPPORT_ADMIN_CHAT_ID")
    return SupportConfig(
        token=token,
        admin_chat_id=int(admin_chat_id),
        database_path=Path(os.getenv("SUPPORT_DB_PATH", "data/support_bot.sqlite3")),
        poll_timeout=int(os.getenv("SUPPORT_POLL_TIMEOUT", "30")),
    )


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
    config = load_support_config()
    telegram = SupportTelegram(config.token)
    db = SupportDatabase(config.database_path)
    log.info("Support bot started. Admin chat: %s", config.admin_chat_id)

    while True:
        try:
            offset = db.offset()
            updates = telegram.get_updates(offset=offset, timeout=config.poll_timeout)
            for update in updates:
                db.set_offset(int(update["update_id"]) + 1)
                message = update.get("message")
                if message:
                    handle_message(message, config, db, telegram)
        except Exception:
            log.exception("Support bot polling error")
            time.sleep(5)


def handle_message(message: dict[str, Any], config: SupportConfig, db: SupportDatabase, telegram: SupportTelegram) -> None:
    chat = message.get("chat") or {}
    chat_id = int(chat.get("id") or 0)
    message_id = int(message.get("message_id") or 0)
    if not chat_id or not message_id:
        return

    if chat_id == config.admin_chat_id:
        handle_admin_message(message, config, db, telegram)
        return

    user = message.get("from") or chat
    db.save_user(user)
    text = str(message.get("text") or "").strip()
    if text in {"/start", "/help"}:
        telegram.send_message(
            chat_id,
            "Hello. Send your question, complaint, or feedback here. The Monitorio team will reply in this chat.",
        )
        return

    username = ("@" + user["username"]) if user.get("username") else "-"
    name = " ".join(part for part in [user.get("first_name"), user.get("last_name")] if part) or "-"
    header = telegram.send_message(
        config.admin_chat_id,
        "<b>New support message</b>\n"
        f"User ID: <code>{chat_id}</code>\n"
        f"Name: {escape(name)}\n"
        f"Username: {escape(username)}\n\n"
        "Reply to this message or to the copied user message to answer.",
    )
    copied = telegram.copy_message(config.admin_chat_id, chat_id, message_id)
    db.map_admin_message(config.admin_chat_id, header, chat_id, message_id)
    db.map_admin_message(config.admin_chat_id, copied, chat_id, message_id)
    telegram.send_message(chat_id, "Thank you. Your message was sent to Monitorio support.")


def handle_admin_message(
    message: dict[str, Any],
    config: SupportConfig,
    db: SupportDatabase,
    telegram: SupportTelegram,
) -> None:
    reply = message.get("reply_to_message") or {}
    reply_message_id = int(reply.get("message_id") or 0)
    if not reply_message_id:
        return
    target = db.user_for_admin_message(config.admin_chat_id, reply_message_id)
    if target is None:
        telegram.send_message(config.admin_chat_id, "I cannot find the user for this reply.")
        return
    user_chat_id = int(target["user_chat_id"])
    text = str(message.get("text") or "").strip()
    if text:
        telegram.send_message(user_chat_id, f"<b>Monitorio support:</b>\n{text}")
    else:
        telegram.copy_message(user_chat_id, config.admin_chat_id, int(message["message_id"]))
    telegram.send_message(config.admin_chat_id, "Reply sent.", reply_to_message_id=int(message["message_id"]))


if __name__ == "__main__":
    main()
