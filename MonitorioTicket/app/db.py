from __future__ import annotations

import sqlite3
from contextlib import contextmanager
from datetime import datetime, timezone
from typing import Any, Iterable

from app.config import settings
from app import kiwi, travelpayouts


def now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


@contextmanager
def connect() -> Iterable[sqlite3.Connection]:
    conn = sqlite3.connect(settings.database_path)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


def init_db() -> None:
    with connect() as conn:
        conn.executescript(
            """
            create table if not exists users (
                id integer primary key autoincrement,
                telegram_id integer unique,
                username text,
                first_name text,
                city text,
                plan text not null default 'free',
                status text not null default 'active',
                created_at text not null,
                last_seen_at text
            );

            create table if not exists searches (
                id integer primary key autoincrement,
                user_id integer,
                origin text not null,
                destination text not null,
                date_from text,
                date_to text,
                budget integer,
                currency text not null default 'USD',
                passengers integer not null default 1,
                baggage text not null default 'carry_on',
                stops text not null default 'any',
                status text not null default 'active',
                created_at text not null,
                updated_at text not null,
                last_checked_at text,
                foreign key(user_id) references users(id)
            );

            create table if not exists alerts (
                id integer primary key autoincrement,
                search_id integer,
                kind text not null,
                title text not null,
                price integer,
                currency text not null default 'USD',
                route text,
                depart_at text,
                source text,
                deep_link text,
                created_at text not null,
                foreign key(search_id) references searches(id)
            );

            create table if not exists sources (
                id integer primary key autoincrement,
                name text not null unique,
                type text not null,
                status text not null default 'planned',
                priority integer not null default 100,
                enabled integer not null default 1,
                last_ok_at text,
                last_error text
            );

            create table if not exists plans (
                id integer primary key autoincrement,
                name text not null unique,
                price_month integer not null,
                search_limit integer not null,
                check_interval_minutes integer not null,
                features text not null
            );

            create table if not exists search_requests (
                id integer primary key autoincrement,
                chat_id integer,
                search_type text not null default 'route',
                origin text not null,
                destination text,
                departure_date text,
                return_date text,
                passengers integer not null default 1,
                direct_only integer not null default 0,
                baggage_required integer not null default 0,
                max_price integer,
                currency text not null default 'EUR',
                created_at text not null
            );

            create table if not exists flight_results (
                id integer primary key autoincrement,
                search_request_id integer,
                chat_id integer,
                origin text not null,
                destination text not null,
                departure_at text,
                arrival_at text,
                return_departure_at text,
                return_arrival_at text,
                price integer not null,
                currency text not null default 'EUR',
                airline text,
                stops integer not null default 0,
                baggage text,
                source text,
                booking_url text,
                found_at text not null,
                foreign key(search_request_id) references search_requests(id)
            );

            create table if not exists favorites (
                id integer primary key autoincrement,
                chat_id integer,
                flight_result_id integer,
                created_at text not null,
                unique(chat_id, flight_result_id),
                foreign key(flight_result_id) references flight_results(id)
            );

            create table if not exists price_watches (
                id integer primary key autoincrement,
                chat_id integer,
                flight_result_id integer,
                origin text not null,
                destination text not null,
                departure_date text,
                return_date text,
                target_price integer,
                currency text not null default 'EUR',
                active integer not null default 1,
                silent integer not null default 0,
                paid_until text,
                created_at text not null,
                last_checked_at text,
                foreign key(flight_result_id) references flight_results(id)
            );

            create table if not exists rail_watches (
                id integer primary key autoincrement,
                chat_id integer,
                origin_station text not null,
                origin_station_id text,
                destination_station text not null,
                destination_station_id text,
                travel_date text not null,
                seat_type text not null default 'any',
                train_number text,
                active integer not null default 1,
                last_available integer not null default 0,
                last_status text,
                last_error text,
                created_at text not null,
                last_checked_at text
            );

            create table if not exists clicks (
                id integer primary key autoincrement,
                chat_id integer,
                flight_result_id integer,
                url text not null,
                clicked_at text not null
            );

            create table if not exists ad_impressions (
                id integer primary key autoincrement,
                chat_id integer,
                ad_id text,
                screen text not null,
                shown_at text not null,
                clicked_at text
            );
            """
        )
    seed_demo_data()


def seed_demo_data() -> None:
    ts = now_iso()
    with connect() as conn:
        if conn.execute("select count(*) from sources").fetchone()[0] == 0:
            conn.executemany(
                """
                insert into sources
                (name, type, status, priority, enabled, last_ok_at, last_error)
                values (?, ?, ?, ?, ?, ?, ?)
                """,
                [
                    ("Travelpayouts Data API", "cached_flights", "ready_for_token", 10, 1, None, None),
                    ("Aviasales Flight Search API", "live_flights", "access_required", 20, 1, None, "Requires partner access / MAU threshold."),
                    ("Skyscanner Live Prices", "live_flights", "access_required", 30, 1, None, "Requires partner approval."),
                    ("Kiwi Tequila", "live_flights", "access_required", 40, 1, None, "Useful for virtual interlining and flexible routes."),
                    ("Tour partners", "tour_packages", "planned", 60, 0, None, "Add after flights MVP."),
                    ("Ukrzaliznytsia availability", "rail_tickets", "adapter_ready", 70, 1, None, "Uses public/unofficial UZ endpoints when available; does not auto-buy tickets."),
                    ("Airline websites", "direct_scraping", "research_only", 90, 0, None, "Anti-bot, captcha, ToS, and parsing instability risk."),
                ],
            )
        else:
            conn.execute(
                """
                insert or ignore into sources
                (name, type, status, priority, enabled, last_ok_at, last_error)
                values (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    "Ukrzaliznytsia availability",
                    "rail_tickets",
                    "adapter_ready",
                    70,
                    1,
                    None,
                    "Uses public/unofficial UZ endpoints when available; does not auto-buy tickets.",
                ),
            )

        if conn.execute("select count(*) from plans").fetchone()[0] == 0:
            conn.executemany(
                """
                insert into plans
                (name, price_month, search_limit, check_interval_minutes, features)
                values (?, ?, ?, ?, ?)
                """,
                [
                    ("free", 0, 3, 720, "3 active searches; cached price checks; Telegram alerts"),
                    ("plus", 7, 20, 180, "20 active searches; flexible dates; nearby departure cities"),
                    ("pro", 19, 100, 60, "Priority checks; family/group searches; advanced filters"),
                ],
            )

        if conn.execute("select count(*) from users").fetchone()[0] == 0:
            conn.execute(
                """
                insert into users
                (telegram_id, username, first_name, city, plan, status, created_at, last_seen_at)
                values (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (100001, "demo_user", "Demo", "Batumi", "free", "active", ts, ts),
            )
            user_id = conn.execute("select id from users where telegram_id = 100001").fetchone()[0]
            conn.execute(
                """
                insert into searches
                (user_id, origin, destination, date_from, date_to, budget, currency,
                 passengers, baggage, stops, status, created_at, updated_at, last_checked_at)
                values (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (user_id, "BUS", "TLV", "2026-08-20", "2026-08-23", 150, "USD", 1, "carry_on", "direct_preferred", "active", ts, ts, None),
            )
            search_id = conn.execute("select id from searches order by id desc limit 1").fetchone()[0]
            conn.executemany(
                """
                insert into alerts
                (search_id, kind, title, price, currency, route, depart_at, source, deep_link, created_at)
                values (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                [
                    (search_id, "exact", "Exact date candidate", 168, "USD", "BUS -> TLV", "2026-08-20", "Manual sample", "", ts),
                    (search_id, "near_date", "Cheaper nearby date", 112, "USD", "BUS -> TLV", "2026-08-22", "Manual sample", "", ts),
                    (search_id, "near_origin", "Alternative departure city", 94, "USD", "KUT -> TLV", "2026-08-20", "Manual sample", "", ts),
                ],
            )


def rows(query: str, params: tuple[Any, ...] = ()) -> list[dict[str, Any]]:
    with connect() as conn:
        return [dict(row) for row in conn.execute(query, params).fetchall()]


def one(query: str, params: tuple[Any, ...] = ()) -> dict[str, Any] | None:
    with connect() as conn:
        row = conn.execute(query, params).fetchone()
        return dict(row) if row else None


def dashboard_stats() -> dict[str, Any]:
    return {
        "users": one("select count(*) as value from users")["value"],
        "active_searches": one("select count(*) as value from searches where status = 'active'")["value"],
        "alerts_today": one("select count(*) as value from alerts where created_at >= date('now')")["value"],
        "enabled_sources": one("select count(*) as value from sources where enabled = 1")["value"],
    }


def setup_status() -> dict[str, bool]:
    return {
        "telegram_bot_token": bool(settings.telegram_bot_token),
        "travelpayouts_token": bool(settings.travelpayouts_token),
        "travelpayouts_marker": bool(settings.travelpayouts_marker),
        "skyscanner_api_key": bool(settings.skyscanner_api_key),
        "kiwi_tequila_api_key": bool(settings.kiwi_tequila_api_key),
        "uz_booking_base": bool(settings.uz_booking_base),
    }


def list_users() -> list[dict[str, Any]]:
    return rows("select * from users order by datetime(created_at) desc limit 100")


def get_user(user_id: int) -> dict[str, Any] | None:
    return one("select * from users where id = ?", (user_id,))


def get_user_by_telegram_id(telegram_id: int) -> dict[str, Any] | None:
    return one("select * from users where telegram_id = ?", (telegram_id,))


def list_searches() -> list[dict[str, Any]]:
    return rows(
        """
        select searches.*, users.username, users.first_name
        from searches
        left join users on users.id = searches.user_id
        order by datetime(searches.updated_at) desc
        limit 100
        """
    )


def get_search(search_id: int) -> dict[str, Any] | None:
    return one(
        """
        select searches.*, users.telegram_id, users.username, users.first_name
        from searches
        left join users on users.id = searches.user_id
        where searches.id = ?
        """,
        (search_id,),
    )


def list_user_searches(user_id: int) -> list[dict[str, Any]]:
    return rows(
        """
        select *
        from searches
        where user_id = ?
        order by datetime(updated_at) desc
        limit 50
        """,
        (user_id,),
    )


def list_alerts() -> list[dict[str, Any]]:
    return rows("select * from alerts order by datetime(created_at) desc limit 100")


def list_user_alerts(user_id: int) -> list[dict[str, Any]]:
    return rows(
        """
        select alerts.*
        from alerts
        join searches on searches.id = alerts.search_id
        where searches.user_id = ?
        order by datetime(alerts.created_at) desc
        limit 20
        """,
        (user_id,),
    )


def list_sources() -> list[dict[str, Any]]:
    return rows("select * from sources order by priority asc")


def list_plans() -> list[dict[str, Any]]:
    return rows("select * from plans order by price_month asc")


def create_or_touch_user(telegram_id: int, username: str | None, first_name: str | None) -> int:
    ts = now_iso()
    with connect() as conn:
        existing = conn.execute("select id from users where telegram_id = ?", (telegram_id,)).fetchone()
        if existing:
            conn.execute(
                "update users set username = ?, first_name = ?, last_seen_at = ? where telegram_id = ?",
                (username, first_name, ts, telegram_id),
            )
            return int(existing["id"])
        cur = conn.execute(
            """
            insert into users
            (telegram_id, username, first_name, city, plan, status, created_at, last_seen_at)
            values (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (telegram_id, username, first_name, None, "free", "active", ts, ts),
        )
        return int(cur.lastrowid)


def create_search(
    user_id: int,
    origin: str,
    destination: str,
    date_from: str | None,
    date_to: str | None,
    budget: int | None,
) -> int:
    ts = now_iso()
    with connect() as conn:
        cur = conn.execute(
            """
            insert into searches
            (user_id, origin, destination, date_from, date_to, budget, currency,
             passengers, baggage, stops, status, created_at, updated_at, last_checked_at)
            values (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (user_id, origin, destination, date_from, date_to, budget, "USD", 1, "carry_on", "any", "active", ts, ts, None),
        )
        return int(cur.lastrowid)


def toggle_source(source_id: int) -> None:
    with connect() as conn:
        conn.execute(
            "update sources set enabled = case when enabled = 1 then 0 else 1 end where id = ?",
            (source_id,),
        )


def set_search_status(search_id: int, status: str) -> None:
    if status not in {"active", "paused", "archived"}:
        raise ValueError("Unsupported search status")
    with connect() as conn:
        conn.execute(
            "update searches set status = ?, updated_at = ? where id = ?",
            (status, now_iso(), search_id),
        )


def set_user_plan(user_id: int, plan: str) -> None:
    allowed = {row["name"] for row in list_plans()}
    if plan not in allowed:
        raise ValueError("Unknown plan")
    with connect() as conn:
        conn.execute("update users set plan = ? where id = ?", (plan, user_id))


AIRPORTS = [
    {"city": "Будапешт", "country": "Угорщина", "code": "BUD", "names": "budapest будапешт bud"},
    {"city": "Бухарест", "country": "Румунія", "code": "OTP", "names": "bucharest бухарест otp"},
    {"city": "Берлін", "country": "Німеччина", "code": "BER", "names": "berlin берлін берлин ber"},
    {"city": "Барселона", "country": "Іспанія", "code": "BCN", "names": "barcelona барселона bcn"},
    {"city": "Баку", "country": "Азербайджан", "code": "GYD", "names": "baku баку baku gyd"},
    {"city": "Базель", "country": "Швейцарія", "code": "BSL", "names": "basel базель bsl"},
    {"city": "Батумі", "country": "Грузія", "code": "BUS", "names": "batumi батумі батуми bus"},
    {"city": "Тель-Авів", "country": "Ізраїль", "code": "TLV", "names": "tel aviv тель-авів тель авив tlv"},
    {"city": "Варшава", "country": "Польща", "code": "WAW", "names": "warsaw варшава waw"},
    {"city": "Кутаїсі", "country": "Грузія", "code": "KUT", "names": "kutaisi кутаїсі кутаиси kut"},
    {"city": "Тбілісі", "country": "Грузія", "code": "TBS", "names": "tbilisi тбілісі тбилиси tbs"},
    {"city": "Відень", "country": "Австрія", "code": "VIE", "names": "vienna відень вена vie"},
    {"city": "Рим", "country": "Італія", "code": "FCO", "names": "rome рим fco"},
    {"city": "Париж", "country": "Франція", "code": "PAR", "names": "paris париж par cdg ory"},
    {"city": "Лондон", "country": "Велика Британія", "code": "LON", "names": "london лондон lon ltn stn gatwick"},
    {"city": "Краків", "country": "Польща", "code": "KRK", "names": "krakow kraków краків краков krk"},
    {"city": "Валенсія", "country": "Іспанія", "code": "VLC", "names": "valencia валенсія валенсия vlc"},
]


RAIL_STATIONS = [
    {"name": "Київ-Пасажирський", "city": "Київ", "aliases": "київ киев kyiv kiev київ-пасажирський"},
    {"name": "Львів", "city": "Львів", "aliases": "львів львов lviv"},
    {"name": "Одеса-Головна", "city": "Одеса", "aliases": "одеса одесса odesa odessa"},
    {"name": "Дніпро-Головний", "city": "Дніпро", "aliases": "дніпро днепр dnipro dnepr"},
    {"name": "Харків-Пасажирський", "city": "Харків", "aliases": "харків харьков kharkiv kharkov"},
    {"name": "Запоріжжя 1", "city": "Запоріжжя", "aliases": "запоріжжя запорожье zaporizhzhia zaporozhye"},
    {"name": "Івано-Франківськ", "city": "Івано-Франківськ", "aliases": "івано-франківськ ивано-франковск ivano-frankivsk"},
    {"name": "Ужгород", "city": "Ужгород", "aliases": "ужгород uzhhorod"},
    {"name": "Чернівці", "city": "Чернівці", "aliases": "чернівці черновцы chernivtsi"},
    {"name": "Вінниця", "city": "Вінниця", "aliases": "вінниця винница vinnytsia"},
    {"name": "Тернопіль", "city": "Тернопіль", "aliases": "тернопіль тернополь ternopil"},
    {"name": "Хмельницький", "city": "Хмельницький", "aliases": "хмельницький хмельницкий khmelnytskyi"},
    {"name": "Полтава-Київська", "city": "Полтава", "aliases": "полтава poltava"},
    {"name": "Суми", "city": "Суми", "aliases": "суми сумы sumy"},
    {"name": "Краматорськ", "city": "Краматорськ", "aliases": "краматорськ краматорск kramatorsk"},
    {"name": "Перемишль-Головний", "city": "Перемишль", "aliases": "перемишль przemysl пшемысль"},
]


def suggest_airports(query: str, limit: int = 8) -> list[dict[str, Any]]:
    q = query.strip().lower()
    if not q:
        return AIRPORTS[:limit]
    matched = []
    for airport in AIRPORTS:
        haystack = f"{airport['city']} {airport['country']} {airport['code']} {airport['names']}".lower()
        if haystack.startswith(q) or f" {q}" in haystack or airport["code"].lower().startswith(q):
            matched.append(airport)
    return matched[:limit]


def suggest_rail_stations(query: str, limit: int = 8) -> list[dict[str, Any]]:
    q = query.strip().lower()
    if not q:
        return RAIL_STATIONS[:limit]
    matched = []
    for station in RAIL_STATIONS:
        haystack = f"{station['name']} {station['city']} {station['aliases']}".lower()
        if haystack.startswith(q) or f" {q}" in haystack:
            matched.append(station)
    return matched[:limit]


def resolve_rail_station_name(value: str | None) -> str | None:
    if not value:
        return None
    cleaned = value.strip()
    lowered = cleaned.lower()
    for station in RAIL_STATIONS:
        haystack = f"{station['name']} {station['city']} {station['aliases']}".lower()
        if lowered in {station["name"].lower(), station["city"].lower()} or lowered in haystack:
            return station["name"]
    return cleaned


def resolve_airport_code(value: str | None) -> str | None:
    if not value:
        return None
    cleaned = value.strip()
    upper = cleaned.upper()
    if len(upper) == 3 and upper.isascii() and upper.isalpha():
        return upper
    lowered = cleaned.lower()
    for airport in AIRPORTS:
        haystack = f"{airport['city']} {airport['country']} {airport['code']} {airport['names']}".lower()
        if lowered == airport["city"].lower() or lowered == airport["code"].lower() or lowered in haystack:
            return airport["code"]
    return upper if upper.isascii() else cleaned


def _airport_label(code_or_city: str | None) -> str:
    if not code_or_city:
        return "Куди дешево"
    value = code_or_city.strip().lower()
    for airport in AIRPORTS:
        if value in {airport["code"].lower(), airport["city"].lower()}:
            return airport["city"]
    return code_or_city.upper() if len(code_or_city) == 3 else code_or_city


def create_search_request(
    chat_id: int | None,
    search_type: str,
    origin: str,
    destination: str | None,
    departure_date: str | None,
    return_date: str | None,
    passengers: int,
    direct_only: bool,
    baggage_required: bool,
    max_price: int | None,
    currency: str,
) -> int:
    with connect() as conn:
        cur = conn.execute(
            """
            insert into search_requests
            (chat_id, search_type, origin, destination, departure_date, return_date, passengers,
             direct_only, baggage_required, max_price, currency, created_at)
            values (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                chat_id,
                search_type,
                origin.upper(),
                destination.upper() if destination else None,
                departure_date,
                return_date,
                passengers,
                1 if direct_only else 0,
                1 if baggage_required else 0,
                max_price,
                currency,
                now_iso(),
            ),
        )
        return int(cur.lastrowid)


def create_demo_flight_results(
    search_request_id: int,
    chat_id: int | None,
    search_type: str,
    origin: str,
    destination: str | None,
    departure_date: str | None,
    return_date: str | None,
    currency: str,
    max_price: int | None,
) -> list[dict[str, Any]]:
    origin_code = origin.upper()
    destination_codes = [destination.upper()] if destination else ["BCN", "ROM", "VIE", "BUD"]
    base_prices = [49, 64, 83, 112]
    airlines = ["Ryanair", "Wizz Air", "Pegasus", "LOT"]
    created_ids: list[int] = []
    with connect() as conn:
        for index, dest_code in enumerate(destination_codes[:4]):
            price = base_prices[index]
            if max_price and price > max_price and index == 0:
                price = max(39, max_price - 7)
            stops = 0 if index < 2 else 1
            booking_url = (
                "https://www.aviasales.com/search/"
                f"{origin_code}{departure_date or '2026-09-12'}{dest_code}1"
            )
            cur = conn.execute(
                """
                insert into flight_results
                (search_request_id, chat_id, origin, destination, departure_at, arrival_at,
                 return_departure_at, return_arrival_at, price, currency, airline, stops,
                 baggage, source, booking_url, found_at)
                values (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    search_request_id,
                    chat_id,
                    origin_code,
                    dest_code,
                    f"{departure_date or '2026-09-12'} 08:40",
                    f"{departure_date or '2026-09-12'} 11:55",
                    f"{return_date} 17:20" if return_date else None,
                    f"{return_date} 20:35" if return_date else None,
                    price,
                    currency,
                    airlines[index % len(airlines)],
                    stops,
                    "ручна поклажа" if index < 2 else "невідомо",
                    "Aviasales / affiliate sample",
                    booking_url,
                    now_iso(),
                ),
            )
            created_ids.append(int(cur.lastrowid))
    return get_flight_results(created_ids)


def create_flight_results_from_travelpayouts(
    search_request_id: int,
    chat_id: int | None,
    origin: str,
    destination: str | None,
    departure_date: str | None,
    return_date: str | None,
    currency: str,
    direct_only: bool,
    max_price: int | None,
) -> list[dict[str, Any]]:
    offers = travelpayouts.prices_for_dates(
        origin=origin,
        destination=destination,
        departure_date=departure_date,
        return_date=return_date,
        currency=currency,
        direct_only=direct_only,
        limit=20,
    )
    if max_price:
        offers = [offer for offer in offers if int(offer.get("price") or offer.get("value") or 0) <= max_price]
    created_ids: list[int] = []
    with connect() as conn:
        for offer in offers[:12]:
            price = int(offer.get("price") or offer.get("value") or 0)
            if price <= 0:
                continue
            offer_origin = offer.get("origin") or origin.upper()
            offer_destination = offer.get("destination") or (destination.upper() if destination else "")
            if not offer_destination:
                continue
            transfers = int(offer.get("transfers") if offer.get("transfers") is not None else offer.get("number_of_changes") or 0)
            departure_at = offer.get("departure_at") or offer.get("depart_date") or departure_date
            return_at = offer.get("return_at") or offer.get("return_date") or return_date
            booking_url = travelpayouts.aviasales_link(
                None,
                offer_origin,
                offer_destination,
                (departure_at or departure_date or "")[:10],
            )
            cur = conn.execute(
                """
                insert into flight_results
                (search_request_id, chat_id, origin, destination, departure_at, arrival_at,
                 return_departure_at, return_arrival_at, price, currency, airline, stops,
                 baggage, source, booking_url, found_at)
                values (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    search_request_id,
                    chat_id,
                    offer_origin,
                    offer_destination,
                    departure_at,
                    None,
                    return_at,
                    None,
                    price,
                    offer.get("currency") or currency,
                    offer.get("airline") or "невідомо",
                    transfers,
                    "невідомо",
                    "Travelpayouts / Aviasales Data API",
                    booking_url,
                    offer.get("found_at") or now_iso(),
                ),
            )
            created_ids.append(int(cur.lastrowid))
    return get_flight_results(created_ids)


def create_flight_results_from_kiwi(
    search_request_id: int,
    chat_id: int | None,
    origin: str,
    destination: str | None,
    departure_date: str | None,
    return_date: str | None,
    passengers: int,
    currency: str,
    direct_only: bool,
    max_price: int | None,
) -> list[dict[str, Any]]:
    offers = kiwi.search_flights(
        origin=origin,
        destination=destination,
        departure_date=departure_date,
        return_date=return_date,
        passengers=passengers,
        currency=currency,
        direct_only=direct_only,
        limit=20,
    )
    if max_price:
        offers = [offer for offer in offers if int(offer.get("price") or 0) <= max_price]
    created_ids: list[int] = []
    with connect() as conn:
        for offer in offers[:12]:
            price = int(offer.get("price") or 0)
            if price <= 0:
                continue
            offer_origin = offer.get("flyFrom") or offer.get("cityCodeFrom") or origin.upper()
            offer_destination = offer.get("flyTo") or offer.get("cityCodeTo") or (destination.upper() if destination else "")
            if not offer_destination:
                continue
            cur = conn.execute(
                """
                insert into flight_results
                (search_request_id, chat_id, origin, destination, departure_at, arrival_at,
                 return_departure_at, return_arrival_at, price, currency, airline, stops,
                 baggage, source, booking_url, found_at)
                values (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    search_request_id,
                    chat_id,
                    offer_origin,
                    offer_destination,
                    offer.get("local_departure") or departure_date,
                    offer.get("local_arrival"),
                    offer.get("route", [{}])[-1].get("local_departure") if return_date and isinstance(offer.get("route"), list) and offer.get("route") else return_date,
                    None,
                    price,
                    offer.get("currency") or currency,
                    kiwi.airline_label(offer),
                    kiwi.stops_count(offer),
                    "за умовами Kiwi",
                    "Kiwi / Tequila API",
                    offer.get("deep_link") or "https://www.kiwi.com/",
                    now_iso(),
                ),
            )
            created_ids.append(int(cur.lastrowid))
    return get_flight_results(created_ids)


def create_flight_results_from_sources(
    search_request_id: int,
    chat_id: int | None,
    origin: str,
    destination: str | None,
    departure_date: str | None,
    return_date: str | None,
    passengers: int,
    currency: str,
    direct_only: bool,
    max_price: int | None,
) -> list[dict[str, Any]]:
    results: list[dict[str, Any]] = []
    results.extend(
        create_flight_results_from_travelpayouts(
            search_request_id=search_request_id,
            chat_id=chat_id,
            origin=origin,
            destination=destination,
            departure_date=departure_date,
            return_date=return_date,
            currency=currency,
            direct_only=direct_only,
            max_price=max_price,
        )
    )
    results.extend(
        create_flight_results_from_kiwi(
            search_request_id=search_request_id,
            chat_id=chat_id,
            origin=origin,
            destination=destination,
            departure_date=departure_date,
            return_date=return_date,
            passengers=passengers,
            currency=currency,
            direct_only=direct_only,
            max_price=max_price,
        )
    )
    return sorted(results, key=lambda item: int(item.get("price") or 0))


def get_flight_results(ids: list[int]) -> list[dict[str, Any]]:
    if not ids:
        return []
    placeholders = ",".join("?" for _ in ids)
    return rows(f"select * from flight_results where id in ({placeholders}) order by price asc", tuple(ids))


def list_latest_results(chat_id: int | None = None, limit: int = 20) -> list[dict[str, Any]]:
    if chat_id:
        return rows(
            "select * from flight_results where chat_id = ? order by datetime(found_at) desc limit ?",
            (chat_id, limit),
        )
    return rows("select * from flight_results order by datetime(found_at) desc limit ?", (limit,))


def list_search_history(chat_id: int | None = None, limit: int = 30) -> list[dict[str, Any]]:
    if chat_id:
        return rows(
            """
            select search_requests.*,
                   min(flight_results.price) as best_price,
                   count(flight_results.id) as result_count
            from search_requests
            left join flight_results on flight_results.search_request_id = search_requests.id
            where search_requests.chat_id = ?
            group by search_requests.id
            order by datetime(search_requests.created_at) desc
            limit ?
            """,
            (chat_id, limit),
        )
    return rows(
        """
        select search_requests.*,
               min(flight_results.price) as best_price,
               count(flight_results.id) as result_count
        from search_requests
        left join flight_results on flight_results.search_request_id = search_requests.id
        group by search_requests.id
        order by datetime(search_requests.created_at) desc
        limit ?
        """,
        (limit,),
    )


def add_favorite(chat_id: int, flight_result_id: int) -> None:
    with connect() as conn:
        conn.execute(
            "insert or ignore into favorites (chat_id, flight_result_id, created_at) values (?, ?, ?)",
            (chat_id, flight_result_id, now_iso()),
        )


def list_favorites(chat_id: int | None = None) -> list[dict[str, Any]]:
    if not chat_id:
        return []
    return rows(
        """
        select flight_results.*, favorites.created_at as saved_at
        from favorites
        join flight_results on flight_results.id = favorites.flight_result_id
        where favorites.chat_id = ?
        order by datetime(favorites.created_at) desc
        """,
        (chat_id,),
    )


def create_price_watch(chat_id: int, flight_result_id: int, target_price: int | None = None) -> None:
    result = one("select * from flight_results where id = ?", (flight_result_id,))
    if not result:
        raise ValueError("Flight result not found")
    with connect() as conn:
        conn.execute(
            """
            insert into price_watches
            (chat_id, flight_result_id, origin, destination, departure_date, return_date,
             target_price, currency, active, silent, paid_until, created_at, last_checked_at)
            values (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                chat_id,
                flight_result_id,
                result["origin"],
                result["destination"],
                result["departure_at"],
                result["return_departure_at"],
                target_price or result["price"],
                result["currency"],
                1,
                0,
                None,
                now_iso(),
                None,
            ),
        )


def create_rail_watch(
    chat_id: int,
    origin_station: str,
    destination_station: str,
    travel_date: str,
    seat_type: str = "any",
    train_number: str | None = None,
    origin_station_id: str | None = None,
    destination_station_id: str | None = None,
) -> dict[str, Any]:
    allowed_seat_types = {"any", "coupe", "platzkart", "lux", "sitting", "intercity"}
    normalized_seat_type = seat_type if seat_type in allowed_seat_types else "any"
    normalized_train = train_number.strip() if train_number else None
    with connect() as conn:
        cur = conn.execute(
            """
            insert into rail_watches
            (chat_id, origin_station, origin_station_id, destination_station, destination_station_id,
             travel_date, seat_type, train_number, active, created_at)
            values (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                chat_id,
                resolve_rail_station_name(origin_station) or origin_station,
                origin_station_id,
                resolve_rail_station_name(destination_station) or destination_station,
                destination_station_id,
                travel_date,
                normalized_seat_type,
                normalized_train,
                1,
                now_iso(),
            ),
        )
        watch_id = int(cur.lastrowid)
    created = get_rail_watch(watch_id)
    if not created:
        raise ValueError("Rail watch was not created")
    return created


def get_rail_watch(watch_id: int) -> dict[str, Any] | None:
    return one("select * from rail_watches where id = ?", (watch_id,))


def list_rail_watches(
    chat_id: int | None = None,
    active_only: bool = False,
    limit: int = 100,
) -> list[dict[str, Any]]:
    clauses = []
    params: list[Any] = []
    if chat_id:
        clauses.append("chat_id = ?")
        params.append(chat_id)
    if active_only:
        clauses.append("active = 1")
    where = f"where {' and '.join(clauses)}" if clauses else ""
    params.append(limit)
    return rows(
        f"""
        select *
        from rail_watches
        {where}
        order by active desc, datetime(created_at) desc
        limit ?
        """,
        tuple(params),
    )


def set_rail_watch_active(watch_id: int, active: bool) -> None:
    with connect() as conn:
        conn.execute("update rail_watches set active = ? where id = ?", (1 if active else 0, watch_id))


def update_rail_watch_check(
    watch_id: int,
    available: bool,
    status: str,
    error: str | None = None,
    origin_station_id: str | None = None,
    destination_station_id: str | None = None,
) -> None:
    with connect() as conn:
        conn.execute(
            """
            update rail_watches
            set last_available = ?,
                last_status = ?,
                last_error = ?,
                last_checked_at = ?,
                origin_station_id = coalesce(?, origin_station_id),
                destination_station_id = coalesce(?, destination_station_id)
            where id = ?
            """,
            (
                1 if available else 0,
                status,
                error,
                now_iso(),
                origin_station_id,
                destination_station_id,
                watch_id,
            ),
        )


def record_click(chat_id: int | None, flight_result_id: int, url: str) -> None:
    with connect() as conn:
        conn.execute(
            "insert into clicks (chat_id, flight_result_id, url, clicked_at) values (?, ?, ?, ?)",
            (chat_id, flight_result_id, url, now_iso()),
        )


def remove_sample_results() -> int:
    with connect() as conn:
        sample_ids = [
            row["id"]
            for row in conn.execute(
                "select id from flight_results where source = 'Aviasales / affiliate sample'"
            ).fetchall()
        ]
        if not sample_ids:
            return 0
        placeholders = ",".join("?" for _ in sample_ids)
        conn.execute(f"delete from favorites where flight_result_id in ({placeholders})", tuple(sample_ids))
        conn.execute(f"delete from price_watches where flight_result_id in ({placeholders})", tuple(sample_ids))
        conn.execute(f"delete from clicks where flight_result_id in ({placeholders})", tuple(sample_ids))
        conn.execute(f"delete from flight_results where id in ({placeholders})", tuple(sample_ids))
        return len(sample_ids)
