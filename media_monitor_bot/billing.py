from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone


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
            "1 \u043a\u043b\u044e\u0447, \u0441\u0442\u0430\u043d\u0434\u0430\u0440\u0442\u043d\u0456 RSS, "
            "\u0431\u0435\u0437 \u0431\u0430\u0437\u0438 \u043f\u043b\u0430\u0442\u043d\u0438\u0445 TG-\u043a\u0430\u043d\u0430\u043b\u0456\u0432, "
            "15 \u0441\u043f\u043e\u0432\u0456\u0449\u0435\u043d\u044c \u043d\u0430 \u0434\u0435\u043d\u044c, "
            "\u043c\u043e\u043d\u0456\u0442\u043e\u0440\u0438\u043d\u0433 \u0440\u0430\u0437 \u043d\u0430 \u0433\u043e\u0434\u0438\u043d\u0443"
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
            "10 \u043a\u043b\u044e\u0447\u0456\u0432, 3 \u0432\u043b\u0430\u0441\u043d\u0456 RSS/TG, "
            "\u0431\u0430\u0437\u0430 230 TG-\u043a\u0430\u043d\u0430\u043b\u0456\u0432 \u0456 TG-\u043f\u0430\u043a\u0435\u0442\u0438, "
            "100 \u0441\u043f\u043e\u0432\u0456\u0449\u0435\u043d\u044c \u043d\u0430 \u0434\u0435\u043d\u044c, "
            "\u043c\u043e\u043d\u0456\u0442\u043e\u0440\u0438\u043d\u0433 \u043a\u043e\u0436\u043d\u0456 30 \u0445\u0432\u0438\u043b\u0438\u043d"
        ),
    ),
    "pro": Plan(
        id="pro",
        name="Pro",
        stars=399,
        days=30,
        max_keywords=50,
        max_custom_sources=15,
        alerts_per_day=500,
        full_text=True,
        description=(
            "50 \u043a\u043b\u044e\u0447\u0456\u0432, 15 \u0432\u043b\u0430\u0441\u043d\u0438\u0445 RSS/TG, "
            "\u0431\u0430\u0437\u0430 230 TG-\u043a\u0430\u043d\u0430\u043b\u0456\u0432 \u0456 TG-\u043f\u0430\u043a\u0435\u0442\u0438, "
            "\u043f\u043e\u0432\u043d\u0438\u0439 \u0442\u0435\u043a\u0441\u0442, "
            "500 \u0441\u043f\u043e\u0432\u0456\u0449\u0435\u043d\u044c \u043d\u0430 \u0434\u0435\u043d\u044c, "
            "\u043c\u043e\u043d\u0456\u0442\u043e\u0440\u0438\u043d\u0433 \u043a\u043e\u0436\u043d\u0456 30 \u0445\u0432\u0438\u043b\u0438\u043d"
        ),
    ),
    "business": Plan(
        id="business",
        name="Business",
        stars=999,
        days=30,
        max_keywords=100000,
        max_custom_sources=100000,
        alerts_per_day=100000,
        full_text=True,
        description=(
            "\u0431\u0435\u0437\u043b\u0456\u043c\u0456\u0442\u043d\u0456 \u043a\u043b\u044e\u0447\u0456, "
            "\u0431\u0435\u0437\u043b\u0456\u043c\u0456\u0442\u043d\u0456 RSS/TG, "
            "\u0431\u0430\u0437\u0430 230 TG-\u043a\u0430\u043d\u0430\u043b\u0456\u0432 \u0456 TG-\u043f\u0430\u043a\u0435\u0442\u0438, "
            "\u043f\u043e\u0432\u043d\u0438\u0439 \u0442\u0435\u043a\u0441\u0442, "
            "\u0431\u0435\u0437\u043b\u0456\u043c\u0456\u0442\u043d\u0456 \u0441\u043f\u043e\u0432\u0456\u0449\u0435\u043d\u043d\u044f, "
            "\u043c\u043e\u043d\u0456\u0442\u043e\u0440\u0438\u043d\u0433 \u043a\u043e\u0436\u043d\u0456 5 \u0445\u0432\u0438\u043b\u0438\u043d"
        ),
    ),
}


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
