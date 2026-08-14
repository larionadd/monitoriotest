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
            sync = DimRiaSourceSync(database, api_key="test-key")
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


if __name__ == "__main__":
    unittest.main()
