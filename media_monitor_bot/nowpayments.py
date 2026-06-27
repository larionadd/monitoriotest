from __future__ import annotations

import hashlib
import hmac
import json
from dataclasses import dataclass
from decimal import Decimal
from typing import Any

import requests


class NowPaymentsError(RuntimeError):
    pass


@dataclass(frozen=True)
class NowPaymentsInvoice:
    invoice_id: str
    invoice_url: str
    raw: dict[str, Any]


class NowPaymentsClient:
    def __init__(self, api_key: str, ipn_secret: str, api_base: str = "https://api.nowpayments.io/v1", timeout: int = 30):
        self.api_key = api_key.strip()
        self.ipn_secret = ipn_secret.strip()
        self.api_base = api_base.rstrip("/")
        self.timeout = timeout

    @property
    def enabled(self) -> bool:
        return bool(self.api_key and self.ipn_secret)

    def create_invoice(
        self,
        *,
        price_amount: Decimal,
        price_currency: str,
        order_id: str,
        order_description: str,
        ipn_callback_url: str,
        success_url: str = "",
        cancel_url: str = "",
    ) -> NowPaymentsInvoice:
        if not self.api_key:
            raise NowPaymentsError("NOWPayments API key is not configured")
        payload: dict[str, Any] = {
            "price_amount": str(price_amount),
            "price_currency": price_currency.lower(),
            "order_id": order_id,
            "order_description": order_description,
            "ipn_callback_url": ipn_callback_url,
        }
        if success_url:
            payload["success_url"] = success_url
        if cancel_url:
            payload["cancel_url"] = cancel_url
        response = requests.post(
            f"{self.api_base}/invoice",
            json=payload,
            headers={"x-api-key": self.api_key, "Content-Type": "application/json"},
            timeout=self.timeout,
        )
        if response.status_code >= 400:
            raise NowPaymentsError(f"NOWPayments invoice failed: {response.status_code} {response.text[:300]}")
        data = response.json()
        invoice_url = str(data.get("invoice_url") or "")
        invoice_id = str(data.get("id") or data.get("invoice_id") or "")
        if not invoice_url:
            raise NowPaymentsError("NOWPayments did not return invoice_url")
        return NowPaymentsInvoice(invoice_id=invoice_id, invoice_url=invoice_url, raw=data)

    def verify_ipn(self, raw_body: bytes, signature: str | None) -> dict[str, Any]:
        if not self.ipn_secret:
            raise NowPaymentsError("NOWPayments IPN secret is not configured")
        if not signature:
            raise NowPaymentsError("Missing NOWPayments IPN signature")
        try:
            payload = json.loads(raw_body.decode("utf-8"))
        except json.JSONDecodeError as exc:
            raise NowPaymentsError("Invalid NOWPayments IPN JSON") from exc
        canonical = canonical_json(payload).encode("utf-8")
        expected = hmac.new(self.ipn_secret.encode("utf-8"), canonical, hashlib.sha512).hexdigest()
        if not hmac.compare_digest(expected.lower(), signature.lower()):
            raise NowPaymentsError("Invalid NOWPayments IPN signature")
        return payload


def canonical_json(value: Any) -> str:
    return json.dumps(_sort_json(value), ensure_ascii=False, separators=(",", ":"))


def _sort_json(value: Any) -> Any:
    if isinstance(value, dict):
        return {key: _sort_json(value[key]) for key in sorted(value)}
    if isinstance(value, list):
        return [_sort_json(item) for item in value]
    return value


PAID_PAYMENT_STATUSES = {"confirmed", "finished"}
