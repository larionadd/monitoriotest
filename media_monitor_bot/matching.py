from __future__ import annotations

import re


def normalize_text(value: str) -> str:
    return " ".join(value.lower().split())


def contains_phrase(text: str, phrase: str) -> bool:
    haystack = normalize_text(text)
    needle = normalize_text(phrase)
    if not needle:
        return False
    if " " in needle:
        return needle in haystack
    return re.search(rf"(?<![\w-]){re.escape(needle)}(?![\w-])", haystack, re.IGNORECASE) is not None


def allowed_by_filters(text: str, stop_words: tuple[str, ...], plus_words: tuple[str, ...]) -> bool:
    if any(contains_phrase(text, word) for word in stop_words):
        return False
    if plus_words and not any(contains_phrase(text, word) for word in plus_words):
        return False
    return True
