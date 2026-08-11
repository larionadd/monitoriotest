from __future__ import annotations

import asyncio
import os
import re
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Literal
from uuid import uuid4

from fastapi import FastAPI, File, Form, Header, HTTPException, Query, UploadFile
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field, model_validator

from .db import Database
from .telegram_sources import TelegramSourceSync


ROOT = Path(__file__).resolve().parents[1]
STATIC_DIR = ROOT / "static"
UPLOAD_DIR = Path(os.getenv("MONITORIO_RENT_UPLOAD_DIR", ROOT / "uploads"))
DATABASE_PATH = Path(os.getenv("MONITORIO_RENT_DATABASE", ROOT / "data" / "monitorio_rent.sqlite3"))
ADMIN_TOKEN = os.getenv("MONITORIO_RENT_ADMIN_TOKEN", "")
MAX_PHOTOS = 8
MAX_PHOTO_BYTES = 8 * 1024 * 1024
PHOTO_TYPES = {
    "image/jpeg": ".jpg",
    "image/png": ".png",
    "image/webp": ".webp",
}

UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
database = Database(DATABASE_PATH)
telegram_source_sync = TelegramSourceSync(database)
SOURCE_SYNC_ENABLED = os.getenv("MONITORIO_RENT_TELEGRAM_SYNC", "1").lower() not in {"0", "false", "no"}
SOURCE_SYNC_INTERVAL_SECONDS = max(300, int(os.getenv("MONITORIO_RENT_SYNC_INTERVAL", "7200")))


def run_source_sync() -> dict:
    telegram_source_sync.database = database
    return telegram_source_sync.sync_all()


async def source_sync_loop() -> None:
    await asyncio.sleep(3)
    while True:
        await asyncio.to_thread(run_source_sync)
        await asyncio.sleep(SOURCE_SYNC_INTERVAL_SECONDS)


@asynccontextmanager
async def lifespan(_: FastAPI):
    task = asyncio.create_task(source_sync_loop()) if SOURCE_SYNC_ENABLED else None
    try:
        yield
    finally:
        if task:
            task.cancel()

app = FastAPI(title="MonitorioRent", version="0.2.0", lifespan=lifespan)
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")
app.mount("/uploads", StaticFiles(directory=UPLOAD_DIR), name="uploads")


class ProfileInput(BaseModel):
    user_id: str = Field(min_length=1, max_length=128)
    role: Literal["renter", "landlord"]


class SearchInput(BaseModel):
    user_id: str = Field(min_length=1, max_length=128)
    city: str = Field(min_length=2, max_length=80)
    district: str = Field(default="", max_length=120)
    price_min: int = Field(default=0, ge=0, le=1_000_000)
    price_max: int = Field(ge=1, le=1_000_000)
    rooms_min: int = Field(default=1, ge=1, le=10)
    rooms_max: int = Field(default=1, ge=1, le=10)
    pets_allowed: bool = False
    no_commission: bool = False
    owner_only: bool = False

    @model_validator(mode="after")
    def validate_ranges(self) -> "SearchInput":
        if self.price_min > self.price_max:
            raise ValueError("Мінімальна ціна не може перевищувати максимальну")
        if self.rooms_min > self.rooms_max:
            raise ValueError("Мінімальна кількість кімнат не може перевищувати максимальну")
        return self


class ListingStatusInput(BaseModel):
    status: Literal["pending", "active", "rejected", "archived"]


@app.get("/")
def index() -> FileResponse:
    return FileResponse(STATIC_DIR / "index.html")


@app.get("/api/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/api/sources")
def sources() -> dict:
    return {
        "sync_enabled": SOURCE_SYNC_ENABLED,
        "interval_seconds": SOURCE_SYNC_INTERVAL_SECONDS,
        "sources": telegram_source_sync.source_status(),
    }


@app.get("/api/state")
def state(user_id: str = Query(min_length=1, max_length=128)) -> dict:
    return {
        "profile": database.get_profile(user_id),
        "searches": database.list_searches(user_id),
        "my_listings": database.list_user_listings(user_id),
        "feed": database.list_feed(limit=20, include_pending_for_user=user_id),
    }


@app.post("/api/profile")
def save_profile(payload: ProfileInput) -> dict:
    return {"profile": database.set_role(payload.user_id.strip(), payload.role)}


@app.post("/api/searches", status_code=201)
def create_search(payload: SearchInput) -> dict:
    data = payload.model_dump()
    user_id = data.pop("user_id").strip()
    data["city"] = data["city"].strip()
    data["district"] = data["district"].strip()
    return {"search": database.create_search(user_id, data)}


@app.delete("/api/searches/{search_id}")
def delete_search(
    search_id: str,
    user_id: str = Query(min_length=1, max_length=128),
) -> dict[str, bool]:
    if not database.delete_search(search_id, user_id):
        raise HTTPException(status_code=404, detail="Пошук не знайдено")
    return {"deleted": True}


@app.get("/api/listings")
def listings(
    city: str = Query(default="", max_length=80),
    district: str = Query(default="", max_length=120),
    price_min: int | None = Query(default=None, ge=0, le=1_000_000),
    price_max: int | None = Query(default=None, ge=1, le=1_000_000),
    rooms: int | None = Query(default=None, ge=1, le=10),
    rooms_min: int | None = Query(default=None, ge=1, le=10),
    rooms_max: int | None = Query(default=None, ge=1, le=10),
    pets_allowed: bool = Query(default=False),
    no_commission: bool = Query(default=False),
    owner_only: bool = Query(default=False),
    limit: int = Query(default=30, ge=1, le=100),
) -> dict:
    return {
        "listings": database.list_feed(
            city=city.strip(),
            district=district.strip(),
            price_min=price_min,
            price_max=price_max,
            rooms=rooms,
            rooms_min=rooms_min,
            rooms_max=rooms_max,
            pets_allowed=pets_allowed,
            no_commission=no_commission,
            owner_only=owner_only,
            limit=limit,
        )
    }


def require_admin(x_admin_token: str | None) -> None:
    if not ADMIN_TOKEN:
        raise HTTPException(status_code=503, detail="Модераторський доступ ще не налаштовано")
    if x_admin_token != ADMIN_TOKEN:
        raise HTTPException(status_code=401, detail="Невірний модераторський токен")


@app.get("/api/admin/listings")
def admin_listings(
    status: Literal["pending", "active", "rejected", "archived"] = "pending",
    limit: int = Query(default=100, ge=1, le=200),
    x_admin_token: str | None = Header(default=None),
) -> dict:
    require_admin(x_admin_token)
    return {"listings": database.list_listings_by_status(status, limit)}


@app.post("/api/admin/listings/{listing_id}/status")
def admin_listing_status(
    listing_id: str,
    payload: ListingStatusInput,
    x_admin_token: str | None = Header(default=None),
) -> dict:
    require_admin(x_admin_token)
    listing = database.set_listing_status(listing_id, payload.status)
    if not listing:
        raise HTTPException(status_code=404, detail="Оголошення не знайдено")
    return {"listing": listing}


@app.post("/api/admin/sources/sync")
async def admin_sync_sources(x_admin_token: str | None = Header(default=None)) -> dict:
    require_admin(x_admin_token)
    return await asyncio.to_thread(run_source_sync)


@app.post("/api/listings", status_code=201)
async def create_listing(
    user_id: str = Form(min_length=1, max_length=128),
    city: str = Form(min_length=2, max_length=80),
    district: str = Form(default="", max_length=120),
    address: str = Form(min_length=3, max_length=180),
    price_uah: int = Form(ge=1, le=1_000_000),
    rooms: int = Form(ge=1, le=10),
    area_sqm: float = Form(gt=5, le=1000),
    floor: int | None = Form(default=None, ge=0, le=200),
    total_floors: int | None = Form(default=None, ge=1, le=200),
    pets_allowed: bool = Form(default=False),
    commission_pct: int = Form(default=0, ge=0, le=100),
    description: str = Form(min_length=30, max_length=5000),
    contact_name: str = Form(min_length=2, max_length=100),
    contact_phone: str = Form(min_length=7, max_length=32),
    photos: list[UploadFile] = File(default=[]),
) -> dict:
    if floor is not None and total_floors is not None and floor > total_floors:
        raise HTTPException(status_code=422, detail="Поверх не може бути вищим за поверховість будинку")
    if len(photos) > MAX_PHOTOS:
        raise HTTPException(status_code=422, detail=f"Можна додати не більше {MAX_PHOTOS} фото")
    normalized_phone = re.sub(r"[^0-9+]", "", contact_phone)
    if len(re.sub(r"\D", "", normalized_phone)) < 7:
        raise HTTPException(status_code=422, detail="Вкажіть коректний номер телефону")

    photo_urls: list[str] = []
    written_files: list[Path] = []
    try:
        for photo in photos:
            extension = PHOTO_TYPES.get(photo.content_type or "")
            if not extension:
                raise HTTPException(status_code=422, detail="Фото мають бути у форматі JPG, PNG або WebP")
            content = await photo.read(MAX_PHOTO_BYTES + 1)
            if len(content) > MAX_PHOTO_BYTES:
                raise HTTPException(status_code=422, detail="Одне фото не може перевищувати 8 МБ")
            filename = f"{uuid4().hex}{extension}"
            destination = UPLOAD_DIR / filename
            destination.write_bytes(content)
            written_files.append(destination)
            photo_urls.append(f"/uploads/{filename}")

        payload = {
            "city": city.strip(),
            "district": district.strip(),
            "address": address.strip(),
            "price_uah": price_uah,
            "rooms": rooms,
            "area_sqm": area_sqm,
            "floor": floor,
            "total_floors": total_floors,
            "pets_allowed": pets_allowed,
            "commission_pct": commission_pct,
            "description": description.strip(),
            "contact_name": contact_name.strip(),
            "contact_phone": normalized_phone,
        }
        listing = database.create_listing(user_id.strip(), payload, photo_urls)
    except Exception:
        for path in written_files:
            path.unlink(missing_ok=True)
        raise
    return {
        "listing": listing,
        "message": "Оголошення надіслано на перевірку",
    }
