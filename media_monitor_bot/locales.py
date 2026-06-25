from __future__ import annotations

from dataclasses import dataclass


DEFAULT_LANGUAGE = "uk"
DEFAULT_COUNTRY = "ua"


@dataclass(frozen=True)
class Language:
    code: str
    button: str
    name: str


@dataclass(frozen=True)
class Country:
    code: str
    button: str
    name_by_language: dict[str, str]


LANGUAGES: dict[str, Language] = {
    "uk": Language("uk", "Українська", "Українська"),
    "pl": Language("pl", "Polski", "Polski"),
    "en": Language("en", "English", "English"),
}

COUNTRIES: dict[str, Country] = {
    "ua": Country("ua", "Україна", {"uk": "Україна", "pl": "Ukraina", "en": "Ukraine"}),
    "pl": Country("pl", "Polska", {"uk": "Польща", "pl": "Polska", "en": "Poland"}),
    "gb": Country("gb", "United Kingdom", {"uk": "Велика Британія", "pl": "Wielka Brytania", "en": "United Kingdom"}),
}


MESSAGES: dict[str, dict[str, str]] = {
    "uk": {
        "choose_language": "Оберіть мову інтерфейсу.",
        "language_saved": "Мову інтерфейсу збережено: {language}.",
        "choose_country": "Оберіть країну для автоматичного моніторингу.",
        "country_saved": "Країну моніторингу збережено: {country}.",
        "onboarding_done": "Налаштування завершено. Додайте ключові слова, і бот почне моніторинг джерел обраної країни.",
        "trial_started": "Тестовий доступ активовано на {days} днів: {plan}.",
        "settings": "Налаштування",
        "language": "Мова",
        "country": "Країна моніторингу",
        "change_language": "Змінити мову",
        "change_country": "Змінити країну",
        "unknown_language": "Невідома мова. Оберіть варіант кнопкою.",
        "unknown_country": "Невідома країна. Оберіть варіант кнопкою.",
        "alert_template": "📰 Нова згадка\n\nКлюч: {keyword}\nДжерело: {source}\nЗаголовок: {title}\nДата: {published_at}\n\n{url}",
    },
    "pl": {
        "choose_language": "Wybierz język interfejsu.",
        "language_saved": "Język interfejsu zapisany: {language}.",
        "choose_country": "Wybierz kraj do automatycznego monitoringu.",
        "country_saved": "Kraj monitoringu zapisany: {country}.",
        "onboarding_done": "Konfiguracja zakończona. Dodaj słowa kluczowe, a bot rozpocznie monitoring źródeł wybranego kraju.",
        "trial_started": "Dostęp testowy aktywowany na {days} dni: {plan}.",
        "settings": "Ustawienia",
        "language": "Język",
        "country": "Kraj monitoringu",
        "change_language": "Zmień język",
        "change_country": "Zmień kraj",
        "unknown_language": "Nieznany język. Wybierz opcję przyciskiem.",
        "unknown_country": "Nieznany kraj. Wybierz opcję przyciskiem.",
        "alert_template": "📰 Nowa wzmianka\n\nSłowo kluczowe: {keyword}\nŹródło: {source}\nTytuł: {title}\nData: {published_at}\n\n{url}",
    },
    "en": {
        "choose_language": "Choose the interface language.",
        "language_saved": "Interface language saved: {language}.",
        "choose_country": "Choose the country for automatic monitoring.",
        "country_saved": "Monitoring country saved: {country}.",
        "onboarding_done": "Setup is complete. Add keywords and the bot will monitor sources for the selected country.",
        "trial_started": "Trial access activated for {days} days: {plan}.",
        "settings": "Settings",
        "language": "Language",
        "country": "Monitoring country",
        "change_language": "Change language",
        "change_country": "Change country",
        "unknown_language": "Unknown language. Choose an option using the button.",
        "unknown_country": "Unknown country. Choose an option using the button.",
        "alert_template": "📰 New mention\n\nKeyword: {keyword}\nSource: {source}\nTitle: {title}\nDate: {published_at}\n\n{url}",
    },
}


def language_name(code: str) -> str:
    return LANGUAGES.get(normalize_language(code), LANGUAGES[DEFAULT_LANGUAGE]).name


def country_name(code: str, language_code: str) -> str:
    country = COUNTRIES.get(normalize_country(code), COUNTRIES[DEFAULT_COUNTRY])
    language = normalize_language(language_code)
    return country.name_by_language.get(language) or country.name_by_language[DEFAULT_LANGUAGE]


def normalize_language(value: str | None) -> str:
    code = (value or "").strip().lower()
    return code if code in LANGUAGES else DEFAULT_LANGUAGE


def normalize_country(value: str | None) -> str:
    code = (value or "").strip().lower()
    if code == "uk":
        code = "gb"
    return code if code in COUNTRIES else DEFAULT_COUNTRY


def language_from_button(value: str) -> str | None:
    needle = value.strip().lower()
    for language in LANGUAGES.values():
        if needle in {language.code, language.button.lower(), language.name.lower()}:
            return language.code
    return None


def country_from_button(value: str) -> str | None:
    needle = value.strip().lower()
    for country in COUNTRIES.values():
        names = {country.code, country.button.lower(), *(name.lower() for name in country.name_by_language.values())}
        if needle in names:
            return country.code
    return None


def text(language_code: str, key: str, **kwargs: object) -> str:
    return template_text(language_code, key).format(**kwargs)


def template_text(language_code: str, key: str) -> str:
    language = normalize_language(language_code)
    template = MESSAGES.get(language, MESSAGES[DEFAULT_LANGUAGE]).get(key)
    if template is None:
        template = MESSAGES[DEFAULT_LANGUAGE][key]
    return template
