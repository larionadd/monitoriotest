from __future__ import annotations

import asyncio

from fastapi import FastAPI, Form, Request
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from app import db, travelpayouts, uz
from app.config import settings


app = FastAPI(title=settings.app_name)
app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")


@app.on_event("startup")
async def startup() -> None:
    db.init_db()
    if settings.run_telegram_bot and settings.telegram_bot_token:
        from app.bot import run_bot_async

        asyncio.create_task(run_bot_async())
    if settings.run_rail_monitor:
        from app.rail_monitor import run_monitor_loop

        asyncio.create_task(run_monitor_loop())


@app.get("/", response_class=HTMLResponse)
async def dashboard(request: Request) -> HTMLResponse:
    return templates.TemplateResponse(
        "dashboard.html",
        {
            "request": request,
            "stats": db.dashboard_stats(),
            "users": db.list_users(),
            "searches": db.list_searches(),
            "alerts": db.list_alerts(),
            "sources": db.list_sources(),
            "plans": db.list_plans(),
            "setup": db.setup_status(),
            "app_name": settings.app_name,
        },
    )


@app.get("/miniapp", response_class=HTMLResponse)
async def miniapp(request: Request) -> HTMLResponse:
    return templates.TemplateResponse(
        "miniapp.html",
        {
            "request": request,
            "app_name": settings.app_name,
        },
    )


@app.get("/api/miniapp/state")
async def miniapp_state(telegram_id: int | None = None) -> JSONResponse:
    user = db.get_user_by_telegram_id(telegram_id) if telegram_id else None
    chat_id = user["telegram_id"] if user else telegram_id
    payload = {
        "app": settings.app_name,
        "user": user,
        "stats": db.dashboard_stats(),
        "setup": db.setup_status(),
        "finds": db.list_latest_results(chat_id),
        "history": db.list_search_history(chat_id),
        "favorites": db.list_favorites(chat_id),
        "rail_watches": db.list_rail_watches(chat_id),
        "sources": db.list_sources() if telegram_id in settings.telegram_admin_ids else [],
        "is_admin": bool(telegram_id and telegram_id in settings.telegram_admin_ids),
    }
    return JSONResponse(payload)


@app.get("/api/miniapp/airports")
async def miniapp_airports(q: str = "") -> JSONResponse:
    return JSONResponse({"items": db.suggest_airports(q)})


@app.get("/api/miniapp/rail/stations")
async def miniapp_rail_stations(q: str = "") -> JSONResponse:
    return JSONResponse({"items": db.suggest_rail_stations(q)})


@app.post("/api/miniapp/search")
async def miniapp_search(
    telegram_id: int | None = Form(None),
    search_type: str = Form("route"),
    origin: str = Form(...),
    destination: str = Form(""),
    departure_date: str = Form(""),
    return_date: str = Form(""),
    passengers: int = Form(1),
    direct_only: bool = Form(False),
    baggage_required: bool = Form(False),
    max_price: str | None = Form(None),
    currency: str = Form("EUR"),
) -> JSONResponse:
    parsed_max_price = int(max_price) if max_price and max_price.isdigit() else None
    origin_code = db.resolve_airport_code(origin) or origin
    destination_code = db.resolve_airport_code(destination) if destination else None
    request_id = db.create_search_request(
        chat_id=telegram_id,
        search_type=search_type,
        origin=origin_code,
        destination=destination_code,
        departure_date=departure_date or None,
        return_date=return_date or None,
        passengers=passengers,
        direct_only=direct_only,
        baggage_required=baggage_required,
        max_price=parsed_max_price,
        currency=currency,
    )
    results = db.create_flight_results_from_sources(
        search_request_id=request_id,
        chat_id=telegram_id,
        origin=origin_code,
        destination=destination_code,
        departure_date=departure_date or None,
        return_date=return_date or None,
        passengers=passengers,
        currency=currency,
        direct_only=direct_only,
        max_price=parsed_max_price,
    )
    search_link = travelpayouts.aviasales_link(
        None,
        origin_code,
        destination_code,
        departure_date or None,
    )
    return JSONResponse(
        {
            "status": "ok",
            "search_request_id": request_id,
            "results": results,
            "search_link": search_link,
            "source": "multi_source" if results else "manual_search",
        }
    )


@app.post("/api/miniapp/favorites")
async def miniapp_favorite(
    telegram_id: int = Form(...),
    flight_result_id: int = Form(...),
) -> dict[str, str]:
    db.add_favorite(telegram_id, flight_result_id)
    return {"status": "ok"}


@app.post("/api/miniapp/watch")
async def miniapp_watch(
    telegram_id: int = Form(...),
    flight_result_id: int = Form(...),
    target_price: int | None = Form(None),
) -> dict[str, str]:
    db.create_price_watch(telegram_id, flight_result_id, target_price)
    return {"status": "ok", "payment": "pending", "amount": "10", "currency": "USD"}


@app.post("/api/miniapp/rail/watch")
async def miniapp_rail_watch(
    telegram_id: int = Form(...),
    origin_station: str = Form(...),
    destination_station: str = Form(...),
    travel_date: str = Form(...),
    seat_type: str = Form("any"),
    train_number: str | None = Form(None),
) -> JSONResponse:
    watch = db.create_rail_watch(
        chat_id=telegram_id,
        origin_station=origin_station,
        destination_station=destination_station,
        travel_date=travel_date,
        seat_type=seat_type,
        train_number=train_number,
    )
    return JSONResponse({"status": "ok", "watch": watch, "search_url": uz.official_search_url()})


@app.get("/api/miniapp/rail/watches")
async def miniapp_rail_watches(telegram_id: int | None = None) -> JSONResponse:
    return JSONResponse({"items": db.list_rail_watches(telegram_id)})


@app.post("/api/miniapp/rail/watches/{watch_id}/check")
async def miniapp_rail_watch_check(watch_id: int) -> JSONResponse:
    watch = db.get_rail_watch(watch_id)
    if not watch:
        return JSONResponse({"status": "not_found"}, status_code=404)
    result = uz.check_availability(watch)
    db.update_rail_watch_check(
        watch_id,
        available=bool(result["available"]),
        status=result["status"],
        error=result["error"],
        origin_station_id=result.get("origin_station_id"),
        destination_station_id=result.get("destination_station_id"),
    )
    return JSONResponse({"status": "ok", "result": result, "watch": db.get_rail_watch(watch_id)})


@app.post("/api/miniapp/rail/watches/{watch_id}/toggle")
async def miniapp_rail_watch_toggle(watch_id: int, active: bool = Form(...)) -> dict[str, str]:
    db.set_rail_watch_active(watch_id, active)
    return {"status": "ok"}


@app.post("/api/miniapp/click")
async def miniapp_click(
    telegram_id: int | None = Form(None),
    flight_result_id: int = Form(...),
    url: str = Form(...),
) -> dict[str, str]:
    db.record_click(telegram_id, flight_result_id, url)
    return {"status": "ok"}


@app.post("/api/miniapp/searches/{search_id}/status")
async def miniapp_search_status(search_id: int, status: str = Form(...)) -> dict[str, str]:
    db.set_search_status(search_id, status)
    return {"status": "ok"}


@app.post("/api/miniapp/sources/{source_id}/toggle")
async def miniapp_source_toggle(source_id: int) -> dict[str, str]:
    db.toggle_source(source_id)
    return {"status": "ok"}


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok", "app": settings.app_name}


@app.post("/sources/{source_id}/toggle")
async def toggle_source(source_id: int) -> RedirectResponse:
    db.toggle_source(source_id)
    return RedirectResponse(url="/#sources", status_code=303)


@app.post("/searches/{search_id}/status")
async def update_search_status(search_id: int, status: str = Form(...)) -> RedirectResponse:
    db.set_search_status(search_id, status)
    return RedirectResponse(url="/#searches", status_code=303)


@app.post("/users/{user_id}/plan")
async def update_user_plan(user_id: int, plan: str = Form(...)) -> RedirectResponse:
    db.set_user_plan(user_id, plan)
    return RedirectResponse(url="/#users", status_code=303)
