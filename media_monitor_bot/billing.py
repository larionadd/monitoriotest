from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from decimal import Decimal


@dataclass(frozen=True)
class Plan:
    id: str
    name: str
    stars: int
    days: int
    max_keywords: int
    max_custom_sources: int
    alerts_per_day: int
    full_text: bool
    description: str


PLANS: dict[str, Plan] = {
    "free": Plan(
        id="free",
        name="Free",
        stars=0,
        days=0,
        max_keywords=1,
        max_custom_sources=0,
        alerts_per_day=15,
        full_text=False,
        description=(
            "🔑 1 ключ • 📰 топ-20 RSS + топ-20 TG-каналів з будь-якої обраної країни • 🔔 15 сповіщень/день • ⏱ моніторинг раз на годину • 💬 підтримка у платних тарифах"

        ),
    ),
    "basic": Plan(
        id="basic",
        name="Basic",
        stars=149,
        days=30,
        max_keywords=10,
        max_custom_sources=3,
        alerts_per_day=100,
        full_text=False,
        description=(
            "🔑 10 ключів • 🧩 3 власні RSS/TG • 📡 повна база TG-каналів • 💬 підтримка • 🔔 100 сповіщень/день • ⏱ моніторинг кожні 30 хвилин"

        ),
    ),
    "pro": Plan(
        id="pro",
        name="Pro",
        stars=399,
        days=30,
        max_keywords=50,
        max_custom_sources=15,
        alerts_per_day=250,
        full_text=False,
        description=(
            "🔑 50 ключів • 🧩 15 власних RSS/TG • 📡 повна база TG-каналів • 💬 підтримка • 🔔 250 сповіщень/день • ⏱ моніторинг кожні 30 хвилин"

        ),
    ),
    "business": Plan(
        id="business",
        name="Business",
        stars=500,
        days=30,
        max_keywords=250,
        max_custom_sources=500,
        alerts_per_day=1000,
        full_text=True,
        description=(
            "🔑 250 ключів • 🧩 500 власних RSS/TG • 📡 повна база TG-каналів • 🧾 пошук по повному тексту • 🏛 пошук по реєстрах • 💬 підтримка • 🔔 1000 сповіщень/день • ⚡ моніторинг кожні 5 хвилин"

        ),
    ),
}

DEFAULT_CRYPTO_PRICES_USD: dict[str, Decimal] = {
    "basic": Decimal("5.00"),
    "pro": Decimal("10.00"),
    "business": Decimal("12.00"),
}

MIN_MONITOR_INTERVAL_MINUTES: dict[str, int] = {
    "free": 60,
    "basic": 30,
    "pro": 30,
    "business": 1,
}
DEFAULT_MONITOR_INTERVAL_MINUTES: dict[str, int] = {
    "free": 60,
    "basic": 30,
    "pro": 30,
    "business": 1,
}
MAX_MONITOR_INTERVAL_MINUTES = 1440


def monitor_interval_bounds(plan_id: str) -> tuple[int, int]:
    return (
        MIN_MONITOR_INTERVAL_MINUTES.get(plan_id.lower(), 60),
        MAX_MONITOR_INTERVAL_MINUTES,
    )


def default_monitor_interval_minutes(plan_id: str) -> int:
    return DEFAULT_MONITOR_INTERVAL_MINUTES.get(plan_id.lower(), 60)


def clamp_monitor_interval_minutes(value: int | None, plan_id: str) -> int:
    minimum, maximum = monitor_interval_bounds(plan_id)
    fallback = default_monitor_interval_minutes(plan_id)
    try:
        minutes = int(value if value is not None else fallback)
    except (TypeError, ValueError):
        minutes = fallback
    return max(minimum, min(maximum, minutes))


def paid_plans() -> list[Plan]:
    return [PLANS["basic"], PLANS["pro"], PLANS["business"]]


def plan_by_id(plan_id: str) -> Plan:
    return PLANS.get(plan_id.lower(), PLANS["free"])


def is_subscription_active(expires_at: str | None) -> bool:
    if not expires_at:
        return False
    try:
        expires = datetime.fromisoformat(expires_at)
    except ValueError:
        return False
    if expires.tzinfo is None:
        expires = expires.replace(tzinfo=timezone.utc)
    return expires > datetime.now(timezone.utc)


def plan_text(plan: Plan) -> str:
    if plan.id == "free":
        return f"{plan.name}: {plan.description}"
    return f"{plan.name}: {plan.stars} Stars / {plan.days} \u0434\u043d\u0456\u0432. {plan.description}"
