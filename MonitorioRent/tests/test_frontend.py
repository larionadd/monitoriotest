from __future__ import annotations

import unittest
from html.parser import HTMLParser
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class AccessibilityParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.ids: list[str] = []
        self.label_depth = 0
        self.unlabelled_controls: list[str] = []
        self.buttons_without_type = 0

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        values = dict(attrs)
        if values.get("id"):
            self.ids.append(values["id"] or "")
        if tag == "label":
            self.label_depth += 1
        if tag == "button" and not values.get("type"):
            self.buttons_without_type += 1
        if tag in {"input", "select", "textarea"}:
            if values.get("type") == "hidden":
                return
            if self.label_depth == 0 and not values.get("aria-label") and not values.get("aria-labelledby"):
                self.unlabelled_controls.append(values.get("name") or values.get("id") or tag)

    def handle_endtag(self, tag: str) -> None:
        if tag == "label":
            self.label_depth -= 1


class FrontendStructureTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.html = (ROOT / "static" / "index.html").read_text(encoding="utf-8")
        cls.css = (ROOT / "static" / "styles.css").read_text(encoding="utf-8")

    def test_first_question_contains_both_roles(self) -> None:
        self.assertIn("Що ви хочете зробити?", self.html)
        self.assertIn("Орендую квартиру", self.html)
        self.assertIn("Здаю квартиру", self.html)

    def test_forms_and_navigation_are_present(self) -> None:
        self.assertIn('id="searchForm"', self.html)
        self.assertIn('id="listingForm"', self.html)
        self.assertEqual(self.html.count('class="form-step'), 3)
        for tab in ("home", "search", "place", "mine"):
            self.assertIn(f'data-tab="{tab}"', self.html)

    def test_controls_have_labels_and_unique_ids(self) -> None:
        parser = AccessibilityParser()
        parser.feed(self.html)
        self.assertEqual(parser.buttons_without_type, 0)
        self.assertEqual(parser.unlabelled_controls, [])
        self.assertEqual(len(parser.ids), len(set(parser.ids)))

    def test_mobile_accessibility_rules_exist(self) -> None:
        self.assertIn("min-height: 48px", self.css)
        self.assertIn("prefers-reduced-motion", self.css)
        self.assertIn("prefers-color-scheme: dark", self.css)

    def test_dim_ria_attribution_is_visible(self) -> None:
        self.assertIn('href="https://dom.ria.com/uk/"', self.html)
        self.assertIn("DIM.RIA", self.html)


if __name__ == "__main__":
    unittest.main()
