from __future__ import annotations

import html
from pathlib import Path
from typing import Any

import requests


class TelegramApi:
    def __init__(self, token: str, timeout: int = 30):
        self.base_url = f"https://api.telegram.org/bot{token}"
        self.timeout = timeout

    def get_updates(self, offset: int | None = None, timeout: int = 30) -> list[dict[str, Any]]:
        params: dict[str, Any] = {
            "timeout": timeout,
            "allowed_updates": ["message", "pre_checkout_query"],
        }
        if offset is not None:
            params["offset"] = offset
        response = requests.get(f"{self.base_url}/getUpdates", params=params, timeout=timeout + 5)
        response.raise_for_status()
        payload = response.json()
        if not payload.get("ok"):
            raise RuntimeError(payload)
        return payload["result"]

    def send_message(
        self,
        chat_id: int,
        text: str,
        disable_web_page_preview: bool = False,
        reply_markup: dict[str, Any] | None = None,
    ) -> None:
        payload: dict[str, Any] = {
            "chat_id": chat_id,
            "text": text,
            "parse_mode": "HTML",
            "disable_web_page_preview": disable_web_page_preview,
        }
        if reply_markup is not None:
            payload["reply_markup"] = reply_markup
        response = requests.post(
            f"{self.base_url}/sendMessage",
            json=payload,
            timeout=self.timeout,
        )
        response.raise_for_status()

    def send_document(self, chat_id: int, path: Path, caption: str = "") -> None:
        with path.open("rb") as fh:
            response = requests.post(
                f"{self.base_url}/sendDocument",
                data={"chat_id": chat_id, "caption": caption},
                files={"document": (path.name, fh)},
                timeout=self.timeout,
            )
        response.raise_for_status()

    def send_invoice(
        self,
        chat_id: int,
        title: str,
        description: str,
        payload: str,
        prices: list[dict[str, Any]],
    ) -> None:
        response = requests.post(
            f"{self.base_url}/sendInvoice",
            json={
                "chat_id": chat_id,
                "title": title,
                "description": description,
                "payload": payload,
                "provider_token": "",
                "currency": "XTR",
                "prices": prices,
            },
            timeout=self.timeout,
        )
        response.raise_for_status()

    def create_invoice_link(
        self,
        title: str,
        description: str,
        payload: str,
        prices: list[dict[str, Any]],
    ) -> str:
        response = requests.post(
            f"{self.base_url}/createInvoiceLink",
            json={
                "title": title,
                "description": description,
                "payload": payload,
                "provider_token": "",
                "currency": "XTR",
                "prices": prices,
            },
            timeout=self.timeout,
        )
        response.raise_for_status()
        payload_json = response.json()
        if not payload_json.get("ok"):
            raise RuntimeError(payload_json)
        return str(payload_json["result"])

    def answer_pre_checkout_query(
        self,
        pre_checkout_query_id: str,
        ok: bool,
        error_message: str | None = None,
    ) -> None:
        payload: dict[str, Any] = {
            "pre_checkout_query_id": pre_checkout_query_id,
            "ok": ok,
        }
        if error_message:
            payload["error_message"] = error_message
        response = requests.post(
            f"{self.base_url}/answerPreCheckoutQuery",
            json=payload,
            timeout=self.timeout,
        )
        response.raise_for_status()

    def set_my_commands(self, commands: list[dict[str, str]], language_code: str | None = None) -> None:
        payload: dict[str, Any] = {"commands": commands}
        if language_code:
            payload["language_code"] = language_code
        response = requests.post(
            f"{self.base_url}/setMyCommands",
            json=payload,
            timeout=self.timeout,
        )
        response.raise_for_status()

    def set_chat_menu_button(self, text: str, url: str) -> None:
        response = requests.post(
            f"{self.base_url}/setChatMenuButton",
            json={
                "menu_button": {
                    "type": "web_app",
                    "text": text,
                    "web_app": {"url": url},
                }
            },
            timeout=self.timeout,
        )
        response.raise_for_status()

    def set_default_chat_menu_button(self) -> None:
        response = requests.post(
            f"{self.base_url}/setChatMenuButton",
            json={"menu_button": {"type": "default"}},
            timeout=self.timeout,
        )
        response.raise_for_status()


def escape(value: object) -> str:
    return html.escape("" if value is None else str(value), quote=False)
