from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from app.db import Database
from app.telegram_sources import TelegramSource, parse_channel_page, parse_listing_text


class TelegramSourceTests(unittest.TestCase):
    def setUp(self) -> None:
        self.source = TelegramSource("rent_test", "Оренда Київ", "Київ", 50)

    def test_parses_ukrainian_listing(self) -> None:
        parsed = parse_listing_text(
            """
            Здається двокімнатна квартира
            💳 19 000 грн | Ернста 12 | 70 м²
            Поверх: 4/9
            Можна з тваринками. Без комісії
            📞 098 123 45 67
            """,
            self.source,
        )
        self.assertIsNotNone(parsed)
        assert parsed is not None
        self.assertEqual(parsed["price_uah"], 19000)
        self.assertEqual(parsed["rooms"], 2)
        self.assertEqual(parsed["area_sqm"], 70)
        self.assertEqual(parsed["floor"], 4)
        self.assertEqual(parsed["total_floors"], 9)
        self.assertTrue(parsed["pets_allowed"])
        self.assertEqual(parsed["commission_pct"], 0)

    def test_skips_tenant_request(self) -> None:
        parsed = parse_listing_text(
            "Шукаю однокімнатну квартиру у Києві. Бюджет до 18000 грн.",
            self.source,
        )
        self.assertIsNone(parsed)

    def test_page_parse_and_database_deduplication(self) -> None:
        html = """
        <div class="tgme_widget_message" data-post="rent_test/123">
          <div class="tgme_widget_message_text">Здається 1к квартира\n💵 15000 грн\n✏️ 40м²\n📍 Оболонь, вул. Озерна 2</div>
          <a class="tgme_widget_message_date" href="https://t.me/rent_test/123"><time datetime="2026-08-12T08:00:00+00:00"></time></a>
          <a class="tgme_widget_message_photo" style="background-image:url('https://example.com/a.jpg')"></a>
        </div>
        """
        items = parse_channel_page(html, self.source)
        self.assertEqual(len(items), 1)
        self.assertEqual(items[0]["external_id"], "rent_test/123")
        self.assertEqual(items[0]["district"], "Оболонь")

        with tempfile.TemporaryDirectory() as directory:
            database = Database(Path(directory) / "rent.sqlite3")
            item = items[0]
            photos = item.pop("photos")
            first, created = database.upsert_external_listing(item, photos)
            second, created_again = database.upsert_external_listing(item, photos)
            self.assertTrue(created)
            self.assertFalse(created_again)
            self.assertEqual(first["id"], second["id"])
            self.assertEqual(second["source_url"], "https://t.me/rent_test/123")


if __name__ == "__main__":
    unittest.main()
