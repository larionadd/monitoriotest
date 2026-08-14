from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

import httpx

from app.db import Database
from app.dim_ria_source import DimRiaSourceSync, normalize_advertisement


DETAIL = {
    "advert_id": 123456,
    "city_name": "Київ",
    "district_name": "Оболонський",
    "street_name": "вул. Героїв Дніпра",
    "building_number_str": "7",
    "price": 22000,
    "currency_type": "UAH",
    "rooms_count": 2,
    "total_square_meters": 58.5,
    "floor": 4,
    "floors_count": 16,
    "advert_type_name": "від власника",
    "description_uk": "Світла квартира, можна з домашніми тваринами.",
    "publishing_date": "2026-08-14T08:00:00+00:00",
    "beautiful_url": "dolgosrochnaya-arenda-kvartira-kiev-obolonskiy-123456",
    "photos": {"1": {"file": "dom/photo/example.jpg"}},
}


class DimRiaSourceTests(unittest.TestCase):
    def test_normalizes_listing_and_photos(self) -> None:
        payload, photos = normalize_advertisement(DETAIL)
        self.assertEqual(payload["external_id"], "123456")
        self.assertEqual(payload["city"], "Київ")
        self.assertEqual(payload["price_uah"], 22000)
        self.assertEqual(payload["rooms"], 2)
        self.assertTrue(payload["owner_only"])
        self.assertTrue(payload["pets_allowed"])
        self.assertEqual(photos, ["https://cdn.riastatic.com/photos/dom/photo/example.jpg"])

    def test_normalizes_live_response_field_names(self) -> None:
        payload, _ = normalize_advertisement({
            "web_id": "abc123",
            "city_name_uk": "Дніпро",
            "district_name_uk": "Тополя-1",
            "street_name_uk": "Запорізьке шосе",
            "price": 13000,
            "currency_type": "грн",
            "rooms_count": 3,
            "floor_info": "9 поверх з 16",
            "withAnimal": True,
            "beautiful_url": "realty-test-34661978.html",
        })
        self.assertEqual(payload["city"], "Дніпро")
        self.assertEqual(payload["floor"], 9)
        self.assertEqual(payload["total_floors"], 16)
        self.assertTrue(payload["pets_allowed"])
        self.assertEqual(payload["source_url"], "https://dom.ria.com/uk/realty-test-34661978.html")

    def test_disabled_without_key_makes_no_request(self) -> None:
        with tempfile.TemporaryDirectory() as folder:
            sync = DimRiaSourceSync(Database(Path(folder) / "test.sqlite3"), api_key="")
            self.assertFalse(sync.enabled)
            self.assertFalse(sync.sync_all()["enabled"])

    def test_sync_fetches_only_unseen_details(self) -> None:
        requests: list[str] = []

        def handler(request: httpx.Request) -> httpx.Response:
            requests.append(request.url.path)
            if request.url.path.endswith("/search"):
                return httpx.Response(200, json={"items": [123456]})
            return httpx.Response(200, json=DETAIL)

        with tempfile.TemporaryDirectory() as folder:
            database = Database(Path(folder) / "test.sqlite3")
            sync = DimRiaSourceSync(
                database,
                api_key="test-key",
                min_interval_seconds=0,
                monthly_budget=10,
            )
            original_client = httpx.Client

            class MockClient(httpx.Client):
                def __init__(self, *args, **kwargs):
                    super().__init__(transport=httpx.MockTransport(handler))

            try:
                httpx.Client = MockClient
                first = sync.sync_all()
                second = sync.sync_all()
            finally:
                httpx.Client = original_client

            self.assertEqual(first["created"], 1)
            self.assertEqual(second["details_fetched"], 0)
            self.assertEqual(requests.count("/dom/info/123456"), 1)

    def test_persistent_interval_and_monthly_budget(self) -> None:
        with tempfile.TemporaryDirectory() as folder:
            database = Database(Path(folder) / "test.sqlite3")
            self.assertTrue(database.claim_source_sync("dimria", 7200))
            self.assertFalse(database.claim_source_sync("dimria", 7200))
            self.assertTrue(database.reserve_source_requests("dimria", 2))
            self.assertTrue(database.reserve_source_requests("dimria", 2))
            self.assertFalse(database.reserve_source_requests("dimria", 2))
            status = database.source_budget_status("dimria", 2)
            self.assertEqual(status["requests_used"], 2)
            self.assertEqual(status["requests_remaining"], 0)


if __name__ == "__main__":
    unittest.main()
