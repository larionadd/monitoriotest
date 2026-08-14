from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from fastapi.testclient import TestClient

from app import main
from app.db import Database, utc_now


class MonitorioRentApiTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        root = Path(self.temp_dir.name)
        main.database = Database(root / "test.sqlite3")
        main.UPLOAD_DIR = root / "uploads"
        main.UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
        main.ADMIN_TOKEN = "test-admin-token"
        self.client = TestClient(main.app)
        self.user_id = "test-user"

    def tearDown(self) -> None:
        self.client.close()
        self.temp_dir.cleanup()

    def test_health_and_initial_state(self) -> None:
        self.assertEqual(self.client.get("/api/health").json(), {"status": "ok"})
        response = self.client.get("/api/state", params={"user_id": self.user_id})
        self.assertEqual(response.status_code, 200)
        self.assertIsNone(response.json()["profile"])

    def test_role_and_saved_search_flow(self) -> None:
        profile = self.client.post(
            "/api/profile",
            json={"user_id": self.user_id, "role": "renter"},
        )
        self.assertEqual(profile.status_code, 200)
        self.assertEqual(profile.json()["profile"]["role"], "renter")

        search = self.client.post(
            "/api/searches",
            json={
                "user_id": self.user_id,
                "city": "Київ",
                "district": "Позняки",
                "price_min": 12000,
                "price_max": 22000,
                "rooms_min": 1,
                "rooms_max": 2,
                "pets_allowed": True,
                "no_commission": True,
                "owner_only": True,
            },
        )
        self.assertEqual(search.status_code, 201)
        search_data = search.json()["search"]
        self.assertTrue(search_data["pets_allowed"])

        state = self.client.get("/api/state", params={"user_id": self.user_id}).json()
        self.assertEqual(len(state["searches"]), 1)

        deleted = self.client.delete(
            f"/api/searches/{search_data['id']}",
            params={"user_id": self.user_id},
        )
        self.assertEqual(deleted.status_code, 200)
        self.assertTrue(deleted.json()["deleted"])

    def test_search_returns_only_recent_matches_and_zero_message(self) -> None:
        base = {
            "channel": "test", "source": "telegram:test", "city": "Київ",
            "district": "Оболонь", "address": "вул. Озерна, 1", "price_uah": 18000,
            "rooms": 1, "area_sqm": 40, "description": "Здається квартира",
            "source_title": "Test", "source_url": "https://t.me/test/1",
            "price_original": "18000 грн", "currency": "UAH",
        }
        main.database.upsert_external_listing(
            {**base, "external_id": "test/1", "published_at": utc_now()}, []
        )
        main.database.upsert_external_listing(
            {**base, "external_id": "test/old", "source_url": "https://t.me/test/old", "published_at": "2020-01-01T08:00:00+00:00"}, []
        )
        response = self.client.post(
            "/api/searches",
            json={
                "user_id": self.user_id, "city": "Київ", "price_max": 20000,
                "rooms_min": 1, "rooms_max": 1, "lookback_days": 3,
            },
        )
        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.json()["match_count"], 1)

        empty = self.client.post(
            "/api/searches",
            json={
                "user_id": self.user_id, "city": "Одеса", "price_max": 5000,
                "rooms_min": 1, "rooms_max": 1, "lookback_days": 3,
            },
        )
        self.assertEqual(empty.json()["match_count"], 0)
        self.assertIn("немає", empty.json()["message"])

    def test_similar_matches_relax_only_district(self) -> None:
        main.database.upsert_external_listing(
            {
                "channel": "test", "source": "telegram:test", "external_id": "similar/1",
                "city": "Київ", "district": "Оболонь", "address": "вул. Озерна, 1",
                "price_uah": 18000, "rooms": 2, "area_sqm": 50,
                "description": "Свіжа двокімнатна квартира", "source_title": "Test",
                "source_url": "https://t.me/test/1", "published_at": utc_now(),
            },
            [],
        )
        search = {
            "city": "Київ", "district": "Теремки", "price_min": 0,
            "price_max": 20000, "rooms_min": 2, "rooms_max": 2,
            "pets_allowed": False, "no_commission": False, "owner_only": False,
            "lookback_days": 3,
        }
        self.assertEqual(main.database.matches_for_search(search), [])
        alternatives = main.database.similar_matches_for_search(search)
        self.assertEqual(len(alternatives), 1)
        self.assertEqual(alternatives[0]["district"], "Оболонь")

    def test_similar_matches_reserve_dim_ria_slot(self) -> None:
        base = {
            "city": "Київ", "district": "Оболонь", "address": "вул. Озерна, 1",
            "price_uah": 18000, "rooms": 1, "area_sqm": 40,
            "description": "Свіжа квартира", "published_at": utc_now(),
        }
        for number in range(6):
            main.database.upsert_external_listing(
                {
                    **base, "channel": "test", "source": "telegram:test",
                    "external_id": f"telegram/{number}", "source_title": "Telegram",
                    "source_url": f"https://t.me/test/{number}",
                },
                [],
            )
        main.database.upsert_external_listing(
            {
                **base, "channel": "dimria", "source": "dimria",
                "external_id": "dimria/1", "source_title": "DIM.RIA",
                "source_url": "https://dom.ria.com/uk/realty-test.html",
            },
            ["https://example.com/photo.jpg"],
        )
        search = {
            "city": "Київ", "district": "Нивки", "price_min": 0,
            "price_max": 20000, "rooms_min": 1, "rooms_max": 1,
            "lookback_days": 3,
        }
        alternatives = main.database.similar_matches_for_search(search, limit=5)
        self.assertEqual(len(alternatives), 5)
        self.assertEqual(alternatives[0]["source"], "dimria")

    def test_owner_can_submit_listing_for_moderation(self) -> None:
        response = self.client.post(
            "/api/listings",
            data={
                "user_id": self.user_id,
                "city": "Львів",
                "district": "Галицький",
                "address": "вул. Шевченка, 10",
                "price_uah": "18000",
                "rooms": "2",
                "area_sqm": "54.5",
                "floor": "3",
                "total_floors": "6",
                "pets_allowed": "true",
                "commission_pct": "0",
                "description": "Світла квартира з меблями, технікою та готовністю до заселення.",
                "contact_name": "Олена",
                "contact_phone": "+380 67 123 45 67",
            },
        )
        self.assertEqual(response.status_code, 201, response.text)
        listing = response.json()["listing"]
        self.assertEqual(listing["status"], "pending")
        self.assertEqual(listing["contact_phone"], "+380671234567")

        state = self.client.get("/api/state", params={"user_id": self.user_id}).json()
        self.assertEqual(len(state["my_listings"]), 1)
        self.assertEqual(len(state["feed"]), 1)

        moderated = self.client.post(
            f"/api/admin/listings/{listing['id']}/status",
            headers={"X-Admin-Token": "test-admin-token"},
            json={"status": "active"},
        )
        self.assertEqual(moderated.status_code, 200)
        public_feed = self.client.get("/api/listings", params={"city": "Львів"}).json()
        self.assertEqual(len(public_feed["listings"]), 1)

    def test_listing_rejects_impossible_floor(self) -> None:
        response = self.client.post(
            "/api/listings",
            data={
                "user_id": self.user_id,
                "city": "Київ",
                "address": "вул. Хрещатик, 1",
                "price_uah": "30000",
                "rooms": "2",
                "area_sqm": "60",
                "floor": "12",
                "total_floors": "5",
                "description": "Повний коректний опис квартири для перевірки валідації поверху.",
                "contact_name": "Іван",
                "contact_phone": "+380501234567",
            },
        )
        self.assertEqual(response.status_code, 422)
        self.assertIn("Поверх", response.json()["detail"])


if __name__ == "__main__":
    unittest.main()
