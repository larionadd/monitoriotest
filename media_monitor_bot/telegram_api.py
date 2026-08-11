from __future__ import annotations

import html
import logging
from pathlib import Path
import time
from typing import Any

import requests
from requests import HTTPError, RequestException

log = logging.getLogger(__name__)


class TelegramApi:
    def __init__(self, token: str, timeout: int = 30):
        self.base_url = f"https://api.telegram.org/bot{token}"
        self.timeout = timeout

    def _request(self, method: str, endpoint: str, attempts: int = 3, **kwargs: Any) -> requests.Response:
        last_error: RequestException | None = None
        for attempt in range(1, attempts + 1):
            try:
                response = requests.request(method, f"{self.base_url}/{endpoint}", **kwargs)
                response.raise_for_status()
                return response
            except RequestException as exc:
                last_error = exc
                if attempt >= attempts:
                    break
                delay = min(2 * attempt, 5)
                log.warning("Telegram %s failed for %s (attempt %s/%s): %s", method, endpoint, attempt, attempts, exc)
                time.sleep(delay)
        assert last_error is not None
        raise last_error

    def get_updates(self, offset: int | None = None, timeout: int = 30) -> list[dict[str, Any]]:
        params: dict[str, Any] = {
            "timeout": timeout,
            "allowed_updates": ["message", "pre_checkout_query"],
        }
        if offset is not None:
            params["offset"] = offset
        request_timeout = max(self.timeout, timeout + 15)
        response = self._request("GET", "getUpdates", attempts=2, params=params, timeout=request_timeout)
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
        disable_notification: bool = False,
    ) -> None:
        payload: dict[str, Any] = {
            "chat_id": chat_id,
            "text": text,
            "parse_mode": "HTML",
            "disable_web_page_preview": disable_web_page_preview,
            "disable_notification": disable_notification,
        }
        if reply_markup is not None:
            payload["reply_markup"] = reply_markup
        try:
            self._request(
                "POST",
                "sendMessage",
                json=payload,
                timeout=self.timeout,
            )
        except HTTPError as exc:
            if exc.response is not None and exc.response.status_code == 403:
                log.warning("Telegram chat %s is unavailable for sendMessage: %s", chat_id, exc)
                return
            raise

    def send_document(self, chat_id: int, path: Path, caption: str = "") -> None:
        with path.open("rb") as fh:
            self._request(
                "POST",
                "sendDocument",
                attempts=1,
                data={"chat_id": chat_id, "caption": caption},
                files={"document": (path.name, fh)},
                timeout=self.timeout,
            )

    def send_invoice(
        self,
        chat_id: int,
        title: str,
        description: str,
        payload: str,
        prices: list[dict[str, Any]],
    ) -> None:
        self._request(
            "POST",
            "sendInvoice",
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

    def create_invoice_link(
        self,
        title: str,
        description: str,
        payload: str,
        prices: list[dict[str, Any]],
    ) -> str:
        response = self._request(
            "POST",
            "createInvoiceLink",
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
        self._request(
            "POST",
            "answerPreCheckoutQuery",
            json=payload,
            timeout=self.timeout,
        )

    def set_my_commands(self, commands: list[dict[str, str]], language_code: str | None = None) -> None:
        payload: dict[str, Any] = {"commands": commands}
        if language_code:
            payload["language_code"] = language_code
        self._request(
            "POST",
            "setMyCommands",
            json=payload,
            timeout=self.timeout,
        )

    def set_chat_menu_button(self, text: str, url: str) -> None:
        self._request(
            "POST",
            "setChatMenuButton",
            json={
                "menu_button": {
                    "type": "web_app",
                    "text": text,
                    "web_app": {"url": url},
                }
            },
            timeout=self.timeout,
        )

    def set_default_chat_menu_button(self) -> None:
        self._request(
            "POST",
            "setChatMenuButton",
            json={"menu_button": {"type": "default"}},
            timeout=self.timeout,
        )


def escape(value: object) -> str:
    return html.escape("" if value is None else str(value), quote=False)
