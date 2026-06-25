from __future__ import annotations

from dataclasses import dataclass


DEFAULT_LANGUAGE = "en"
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
    "en": Language("en", "English", "English"),
    "uk": Language("uk", "Українська", "Українська"),
    "pl": Language("pl", "Polski", "Polski"),
    "de": Language("de", "Deutsch", "Deutsch"),
    "es": Language("es", "Español", "Español"),
    "it": Language("it", "Italiano", "Italiano"),
    "be": Language("be", "Беларуская", "Беларуская"),
}

COUNTRIES: dict[str, Country] = {
    "ua": Country(
        "ua",
        "Ukraine",
        {
            "en": "Ukraine",
            "uk": "Україна",
            "pl": "Ukraina",
            "de": "Ukraine",
            "es": "Ucrania",
            "it": "Ucraina",
            "be": "Украіна",
        },
    ),
    "pl": Country(
        "pl",
        "Poland",
        {
            "en": "Poland",
            "uk": "Польща",
            "pl": "Polska",
            "de": "Polen",
            "es": "Polonia",
            "it": "Polonia",
            "be": "Польшча",
        },
    ),
    "gb": Country(
        "gb",
        "United Kingdom",
        {
            "en": "United Kingdom",
            "uk": "Велика Британія",
            "pl": "Wielka Brytania",
            "de": "Vereinigtes Königreich",
            "es": "Reino Unido",
            "it": "Regno Unito",
            "be": "Вялікая Брытанія",
        },
    ),
    "de": Country(
        "de",
        "Germany",
        {
            "en": "Germany",
            "uk": "Німеччина",
            "pl": "Niemcy",
            "de": "Deutschland",
            "es": "Alemania",
            "it": "Germania",
            "be": "Германія",
        },
    ),
    "es": Country(
        "es",
        "Spain",
        {
            "en": "Spain",
            "uk": "Іспанія",
            "pl": "Hiszpania",
            "de": "Spanien",
            "es": "España",
            "it": "Spagna",
            "be": "Іспанія",
        },
    ),
    "it": Country(
        "it",
        "Italy",
        {
            "en": "Italy",
            "uk": "Італія",
            "pl": "Włochy",
            "de": "Italien",
            "es": "Italia",
            "it": "Italia",
            "be": "Італія",
        },
    ),
    "by": Country(
        "by",
        "Belarus",
        {
            "en": "Belarus",
            "uk": "Білорусь",
            "pl": "Białoruś",
            "de": "Belarus",
            "es": "Bielorrusia",
            "it": "Bielorussia",
            "be": "Беларусь",
        },
    ),
}

LANGUAGE_FLAGS: dict[str, str] = {
    "en": "🇬🇧",
    "uk": "🇺🇦",
    "pl": "🇵🇱",
    "de": "🇩🇪",
    "es": "🇪🇸",
    "it": "🇮🇹",
    "be": "⬜️🟥⬜️",
}

COUNTRY_FLAGS: dict[str, str] = {
    "ua": "🇺🇦",
    "pl": "🇵🇱",
    "gb": "🇬🇧",
    "de": "🇩🇪",
    "es": "🇪🇸",
    "it": "🇮🇹",
    "by": "⬜️🟥⬜️",
}


MESSAGES: dict[str, dict[str, str]] = {
    "en": {
        "welcome": (
            "👋 Welcome to Monitorio.\n\n"
            "I monitor online media and public Telegram channels by your keywords.\n\n"
            "What you can do here:\n"
            "🔎 track mentions of brands, people, companies, topics, or domains;\n"
            "📰 monitor RSS/news sites and public Telegram channels;\n"
            "🌍 choose a monitoring region and switch it later;\n"
            "🧾 search in headlines/RSS summaries or in the full article text;\n"
            "🚫 use stop words and required words to clean up results;\n"
            "📄 download CSV reports and source lists.\n\n"
            "First, choose your interface language."
        ),
        "choose_language": "Choose the interface language.",
        "language_saved": "Interface language saved: {language}.",
        "choose_country": "Choose the region for automatic monitoring.",
        "country_saved": "Monitoring region saved: {country}.",
        "onboarding_done": "Setup is complete. Add keywords and the bot will monitor sources for the selected region.",
        "trial_started": "Trial access activated for {days} days: {plan}.",
        "settings": "Settings",
        "language": "Language",
        "country": "Monitoring region",
        "text_mode_label": "Text mode",
        "text_mode_full": "full article text",
        "text_mode_fast": "headline + RSS summary",
        "change_language": "Change language",
        "change_country": "Change region",
        "change_text_mode": "Change text mode",
        "unknown_language": "Unknown language. Choose an option using the button.",
        "unknown_country": "Unknown region. Choose an option using the button.",
        "alert_template": "📰 New mention\n\nKeyword: {keyword}\nSource: {source}\nTitle: {title}\nDate: {published_at}\n\n{url}",
    },
    "uk": {
        "welcome": (
            "👋 Вітаю в Monitorio.\n\n"
            "Я моніторю онлайн-медіа та публічні Telegram-канали за вашими ключовими словами.\n\n"
            "Що можна робити:\n"
            "🔎 відстежувати згадки брендів, людей, компаній, тем або доменів;\n"
            "📰 моніторити RSS/новинні сайти та публічні Telegram-канали;\n"
            "🌍 обирати регіон моніторингу і змінювати його пізніше;\n"
            "🧾 шукати в заголовках/RSS-анонсах або в повному тексті новини;\n"
            "🚫 використовувати стоп-слова та обов'язкові слова для чистіших результатів;\n"
            "📄 завантажувати CSV-звіти і списки джерел.\n\n"
            "Спочатку оберіть мову інтерфейсу."
        ),
        "choose_language": "Оберіть мову інтерфейсу.",
        "language_saved": "Мову інтерфейсу збережено: {language}.",
        "choose_country": "Оберіть регіон для автоматичного моніторингу.",
        "country_saved": "Регіон моніторингу збережено: {country}.",
        "onboarding_done": "Налаштування завершено. Додайте ключові слова, і бот почне моніторинг джерел обраного регіону.",
        "trial_started": "Тестовий доступ активовано на {days} днів: {plan}.",
        "settings": "Налаштування",
        "language": "Мова",
        "country": "Регіон моніторингу",
        "text_mode_label": "Режим тексту",
        "text_mode_full": "повний текст новини",
        "text_mode_fast": "заголовок + RSS-анонс",
        "change_language": "Змінити мову",
        "change_country": "Змінити регіон",
        "change_text_mode": "Змінити режим тексту",
        "unknown_language": "Невідома мова. Оберіть варіант кнопкою.",
        "unknown_country": "Невідомий регіон. Оберіть варіант кнопкою.",
        "alert_template": "📰 Нова згадка\n\nКлюч: {keyword}\nДжерело: {source}\nЗаголовок: {title}\nДата: {published_at}\n\n{url}",
    },
    "pl": {
        "welcome": (
            "👋 Witaj w Monitorio.\n\n"
            "Monitoruję media online i publiczne kanały Telegram według Twoich słów kluczowych.\n\n"
            "Możesz tutaj:\n"
            "🔎 śledzić wzmianki o markach, osobach, firmach, tematach lub domenach;\n"
            "📰 monitorować RSS/serwisy informacyjne i publiczne kanały Telegram;\n"
            "🌍 wybrać region monitoringu i zmienić go później;\n"
            "🧾 szukać w nagłówkach/RSS albo w pełnym tekście artykułu;\n"
            "🚫 używać stop-słów i słów wymaganych, aby oczyścić wyniki;\n"
            "📄 pobierać raporty CSV i listy źródeł.\n\n"
            "Najpierw wybierz język interfejsu."
        ),
        "choose_language": "Wybierz język interfejsu.",
        "language_saved": "Język interfejsu zapisany: {language}.",
        "choose_country": "Wybierz region do automatycznego monitoringu.",
        "country_saved": "Region monitoringu zapisany: {country}.",
        "onboarding_done": "Konfiguracja zakończona. Dodaj słowa kluczowe, a bot rozpocznie monitoring źródeł wybranego regionu.",
        "trial_started": "Dostęp testowy aktywowany na {days} dni: {plan}.",
        "settings": "Ustawienia",
        "language": "Język",
        "country": "Region monitoringu",
        "text_mode_label": "Tryb tekstu",
        "text_mode_full": "pełny tekst artykułu",
        "text_mode_fast": "nagłówek + opis RSS",
        "change_language": "Zmień język",
        "change_country": "Zmień region",
        "change_text_mode": "Zmień tryb tekstu",
        "unknown_language": "Nieznany język. Wybierz opcję przyciskiem.",
        "unknown_country": "Nieznany region. Wybierz opcję przyciskiem.",
        "alert_template": "📰 Nowa wzmianka\n\nSłowo kluczowe: {keyword}\nŹródło: {source}\nTytuł: {title}\nData: {published_at}\n\n{url}",
    },
    "de": {
        "welcome": (
            "👋 Willkommen bei Monitorio.\n\n"
            "Ich beobachte Online-Medien und öffentliche Telegram-Kanäle nach deinen Keywords.\n\n"
            "Du kannst hier:\n"
            "🔎 Erwähnungen von Marken, Personen, Unternehmen, Themen oder Domains verfolgen;\n"
            "📰 RSS/Nachrichtenseiten und öffentliche Telegram-Kanäle monitoren;\n"
            "🌍 eine Monitoring-Region wählen und später ändern;\n"
            "🧾 in Überschriften/RSS-Zusammenfassungen oder im Volltext suchen;\n"
            "🚫 Stoppwörter und Pflichtwörter für sauberere Ergebnisse nutzen;\n"
            "📄 CSV-Berichte und Quellenlisten herunterladen.\n\n"
            "Wähle zuerst die Sprache der Oberfläche."
        ),
        "choose_language": "Wähle die Sprache der Oberfläche.",
        "language_saved": "Sprache gespeichert: {language}.",
        "choose_country": "Wähle die Region für das automatische Monitoring.",
        "country_saved": "Monitoring-Region gespeichert: {country}.",
        "onboarding_done": "Einrichtung abgeschlossen. Füge Keywords hinzu, und der Bot überwacht Quellen aus der gewählten Region.",
        "trial_started": "Testzugang für {days} Tage aktiviert: {plan}.",
        "settings": "Einstellungen",
        "language": "Sprache",
        "country": "Monitoring-Region",
        "text_mode_label": "Textmodus",
        "text_mode_full": "voller Artikeltext",
        "text_mode_fast": "Überschrift + RSS-Zusammenfassung",
        "change_language": "Sprache ändern",
        "change_country": "Region ändern",
        "change_text_mode": "Textmodus ändern",
        "unknown_language": "Unbekannte Sprache. Bitte wähle eine Option per Button.",
        "unknown_country": "Unbekannte Region. Bitte wähle eine Option per Button.",
        "alert_template": "📰 Neue Erwähnung\n\nKeyword: {keyword}\nQuelle: {source}\nTitel: {title}\nDatum: {published_at}\n\n{url}",
    },
    "es": {
        "welcome": (
            "👋 Bienvenido a Monitorio.\n\n"
            "Monitorizo medios online y canales públicos de Telegram por tus palabras clave.\n\n"
            "Aquí puedes:\n"
            "🔎 seguir menciones de marcas, personas, empresas, temas o dominios;\n"
            "📰 monitorizar RSS/sitios de noticias y canales públicos de Telegram;\n"
            "🌍 elegir una región de monitoreo y cambiarla después;\n"
            "🧾 buscar en titulares/resúmenes RSS o en el texto completo;\n"
            "🚫 usar palabras excluidas y palabras obligatorias para limpiar resultados;\n"
            "📄 descargar informes CSV y listas de fuentes.\n\n"
            "Primero, elige el idioma de la interfaz."
        ),
        "choose_language": "Elige el idioma de la interfaz.",
        "language_saved": "Idioma guardado: {language}.",
        "choose_country": "Elige la región para el monitoreo automático.",
        "country_saved": "Región de monitoreo guardada: {country}.",
        "onboarding_done": "Configuración completada. Añade palabras clave y el bot monitorizará fuentes de la región seleccionada.",
        "trial_started": "Acceso de prueba activado por {days} días: {plan}.",
        "settings": "Configuración",
        "language": "Idioma",
        "country": "Región de monitoreo",
        "text_mode_label": "Modo de texto",
        "text_mode_full": "texto completo del artículo",
        "text_mode_fast": "titular + resumen RSS",
        "change_language": "Cambiar idioma",
        "change_country": "Cambiar región",
        "change_text_mode": "Cambiar modo de texto",
        "unknown_language": "Idioma desconocido. Elige una opción con el botón.",
        "unknown_country": "Región desconocida. Elige una opción con el botón.",
        "alert_template": "📰 Nueva mención\n\nPalabra clave: {keyword}\nFuente: {source}\nTítulo: {title}\nFecha: {published_at}\n\n{url}",
    },
    "it": {
        "welcome": (
            "👋 Benvenuto in Monitorio.\n\n"
            "Monitoro media online e canali Telegram pubblici in base alle tue parole chiave.\n\n"
            "Qui puoi:\n"
            "🔎 seguire menzioni di brand, persone, aziende, temi o domini;\n"
            "📰 monitorare RSS/siti di notizie e canali Telegram pubblici;\n"
            "🌍 scegliere una regione di monitoraggio e cambiarla dopo;\n"
            "🧾 cercare nei titoli/RSS o nel testo completo degli articoli;\n"
            "🚫 usare parole escluse e parole obbligatorie per pulire i risultati;\n"
            "📄 scaricare report CSV e liste di fonti.\n\n"
            "Per prima cosa, scegli la lingua dell'interfaccia."
        ),
        "choose_language": "Scegli la lingua dell'interfaccia.",
        "language_saved": "Lingua salvata: {language}.",
        "choose_country": "Scegli la regione per il monitoraggio automatico.",
        "country_saved": "Regione di monitoraggio salvata: {country}.",
        "onboarding_done": "Configurazione completata. Aggiungi parole chiave e il bot monitorerà le fonti della regione selezionata.",
        "trial_started": "Accesso di prova attivato per {days} giorni: {plan}.",
        "settings": "Impostazioni",
        "language": "Lingua",
        "country": "Regione di monitoraggio",
        "text_mode_label": "Modalità testo",
        "text_mode_full": "testo completo dell'articolo",
        "text_mode_fast": "titolo + riepilogo RSS",
        "change_language": "Cambia lingua",
        "change_country": "Cambia regione",
        "change_text_mode": "Cambia modalità testo",
        "unknown_language": "Lingua sconosciuta. Scegli un'opzione con il pulsante.",
        "unknown_country": "Regione sconosciuta. Scegli un'opzione con il pulsante.",
        "alert_template": "📰 Nuova menzione\n\nParola chiave: {keyword}\nFonte: {source}\nTitolo: {title}\nData: {published_at}\n\n{url}",
    },
    "be": {
        "welcome": (
            "👋 Вітаем у Monitorio.\n\n"
            "Я манітору анлайн-медыя і публічныя Telegram-каналы па вашых ключавых словах.\n\n"
            "Тут можна:\n"
            "🔎 адсочваць згадкі брэндаў, людзей, кампаній, тэм або даменаў;\n"
            "📰 маніторыць RSS/навінавыя сайты і публічныя Telegram-каналы;\n"
            "🌍 выбіраць рэгіён маніторынгу і змяняць яго пазней;\n"
            "🧾 шукаць у загалоўках/RSS-анонсах або ў поўным тэксце артыкула;\n"
            "🚫 выкарыстоўваць стоп-словы і абавязковыя словы для чысцейшых вынікаў;\n"
            "📄 спампоўваць CSV-справаздачы і спісы крыніц.\n\n"
            "Спачатку выберыце мову інтэрфейсу."
        ),
        "choose_language": "Выберыце мову інтэрфейсу.",
        "language_saved": "Мова інтэрфейсу захавана: {language}.",
        "choose_country": "Выберыце рэгіён для аўтаматычнага маніторынгу.",
        "country_saved": "Рэгіён маніторынгу захаваны: {country}.",
        "onboarding_done": "Наладка завершана. Дадайце ключавыя словы, і бот пачне маніторынг крыніц абранага рэгіёну.",
        "trial_started": "Тэставы доступ актываваны на {days} дзён: {plan}.",
        "settings": "Налады",
        "language": "Мова",
        "country": "Рэгіён маніторынгу",
        "text_mode_label": "Рэжым тэксту",
        "text_mode_full": "поўны тэкст артыкула",
        "text_mode_fast": "загаловак + RSS-анонс",
        "change_language": "Змяніць мову",
        "change_country": "Змяніць рэгіён",
        "change_text_mode": "Змяніць рэжым тэксту",
        "unknown_language": "Невядомая мова. Выберыце варыянт кнопкай.",
        "unknown_country": "Невядомы рэгіён. Выберыце варыянт кнопкай.",
        "alert_template": "📰 Новая згадка\n\nКлюч: {keyword}\nКрыніца: {source}\nЗагаловак: {title}\nДата: {published_at}\n\n{url}",
    },
}

EXTRA_MESSAGES: dict[str, dict[str, str]] = {
    "en": {
        "button_add": "➕ Add keyword",
        "button_remove": "➖ Remove keyword",
        "button_info": "📋 My monitoring",
        "button_check": "🔎 Check now",
        "button_sources": "📰 Sources",
        "button_report": "📄 Report",
        "button_filters": "⚙️ Filters",
        "button_text_mode": "🧾 Text mode",
        "button_plans": "💳 Plans",
        "button_help": "ℹ️ Help",
        "button_app": "📱 Cabinet",
        "button_source_list": "📋 Source list",
        "button_tg_blocks": "📦 TG packages",
        "button_sources_file": "📎 Sources file",
        "button_source_add": "➕ Add RSS",
        "button_tg_add": "➕ Add TG",
        "button_source_disable": "⛔ Disable source",
        "button_source_enable": "✅ Enable source",
        "button_source_remove": "🗑️ Remove my source",
        "button_full_text_on": "✅ Full text",
        "button_full_text_off": "⚡ RSS summary",
        "button_stop_add": "🚫 Add stop word",
        "button_stop_remove": "✅ Remove stop word",
        "button_plus_add": "➕ Add required word",
        "button_plus_remove": "➖ Remove required word",
        "button_back": "⬅️ Main menu",
        "button_language": "🌐 Language",
        "button_country": "🌍 Region",
        "button_settings": "⚙️ Settings",
        "help_text": (
            "Monitorio monitors online media and public Telegram channels by keywords.\n\n"
            "Automatic monitoring frequency: Free once per hour, Basic/Pro every 30 minutes, Business every 5 minutes.\n"
            "Add keywords, choose a country, and the bot will send new mentions.\n\n"
            "Commands:\n"
            "/add keyword - add a keyword\n"
            "/remove keyword - remove a keyword\n"
            "/settings - language, region, and text mode\n"
            "/rss list - show RSS and Telegram sources\n"
            "/rss add URL - add your RSS source\n"
            "/tg add @channel - add a public Telegram channel\n"
            "/tgblocks - manage paid Telegram packages by blocks of 50\n"
            "/sourcesfile - receive a CSV file with all source numbers\n"
            "/check - check sources now\n"
            "/report - receive a CSV report"
        ),
        "filters_title": "Filter settings:",
        "main_menu_title": "Main menu:",
        "choose_menu_action": "Choose an action from the menu or use /help.",
        "prompt_add_keyword": "Send the keyword phrase in one message.",
        "prompt_remove_keyword": "Send the keyword phrase you want to remove.",
        "prompt_add_stop_word": "Send the stop word in one message.",
        "prompt_remove_stop_word": "Send the stop word you want to remove.",
        "prompt_add_plus_word": "Send the required word in one message.",
        "prompt_remove_plus_word": "Send the required word you want to remove.",
        "prompt_add_rss": "Send the RSS feed URL. Example:\nhttps://example.com/rss.xml",
        "prompt_add_tg": "Send a username or URL of a public Telegram channel. Example:\n@channel\nhttps://t.me/channel",
        "prompt_disable_source": "Send the number, @username, or URL of the source you want to disable.",
        "prompt_enable_source": "Send the number, @username, or URL of the source you want to enable.",
        "prompt_remove_source": "Send the number, @username, or URL of your own source to remove.",
        "keyword_label": "Keyword",
        "stop_word_label": "Stop word",
        "plus_word_label": "Required word",
        "added": "added",
        "already_exists": "already exists",
        "removed": "removed",
        "not_found": "not found",
        "empty_terms": "none",
        "fulltext_unavailable": "Full-text search is available in Pro and Business plans.",
        "fulltext_enabled": "Full-text mode is enabled. The bot will search in the title, RSS summary, and article page text.",
        "fast_mode_enabled": "Fast mode is enabled. The bot will search only in the title and RSS summary.",
        "info_title": "My monitoring",
        "keywords": "Keywords",
        "stop_words": "Stop words",
        "plus_words": "Required words",
        "search_mode": "Search mode",
        "active_sources": "Active sources",
        "auto_check": "Automatic check",
        "interval_business": "every 5 minutes",
        "interval_paid": "every 30 minutes",
        "interval_free": "once per hour",
        "text_mode_intro": "Search mode defines where the bot looks for your keywords.",
        "current_mode": "Current mode",
        "text_mode_note": "Full text is more precise, but checks take longer and depend on site availability.",
        "manual_check_start": "Starting a manual source check.",
        "manual_check_busy": "A background check is still running for more than a minute. Try /check a little later.",
        "manual_check_done": "Check complete. New notifications sent: {sent}",
        "sources_file_caption": "Sources table: numbers, TG ranking, subscribers, and disable commands",
        "report_caption": "CSV report with found mentions",
        "mini_app_business_only": "The cabinet is available only in the Business plan. Upgrade via /plans.",
        "mini_app_bad_data": "Mini App sent invalid data.",
        "mini_app_unknown_action": "Unknown Mini App action.",
        "mini_app_action_failed": "Could not complete the Mini App action. Try again.",
        "message_failed": "Could not process the message. Try again.",
        "fulltext_status": "Full-text search is {status}.",
        "status_enabled": "enabled",
        "status_disabled": "disabled",
        "plans_title": "Telegram Stars plans:",
        "current_plan": "Current plan",
        "expires_at": "Valid until",
        "no_expiry": "none",
        "payment_command": "Payment",
        "plan_activation_note": "After payment, the plan is activated automatically for 30 days.",
        "choose_paid_plan": "Choose a paid plan: /buy basic, /buy pro or /buy business.",
        "invoice_title": "Plan {plan} for {days} days",
        "invoice_price_label": "{plan} / {days} days",
        "unknown_plan_checkout": "Unknown plan. Try starting the payment again.",
        "payment_unknown_plan": "Payment received, but the plan was not recognized. Contact the administrator.",
        "payment_success": "Payment received. Plan {plan} {status} until {expires}.",
        "payment_status_activated": "activated",
        "payment_status_already": "was already activated",
        "admin_only": "This command is available only to the administrator.",
        "grant_format": "Format: /grant chat_id pro 30",
        "grant_plan_format": "Format: /grant chat_id basic|pro|business 30",
        "grant_success": "Granted {plan} to {chat_id} until {expires}.",
        "users_count": "Users in database: {total}",
        "users_shown": "Showing recent active users: {shown}",
        "users_empty": "No users yet.",
        "users_plan_line": "   plan: {plan}; keywords: {keywords}; custom sources: {sources}",
        "users_last_seen": "   last activity: {last_seen}",
        "users_expires": "   valid until: {expires}",
        "keyword_limit": "Keyword limit for {plan}: {limit}. Upgrade via /plans.",
        "custom_rss_limit": "Custom RSS limit for {plan}: {limit}. Upgrade via /plans.",
        "custom_source_limit": "Custom source limit for {plan}: {limit}. Upgrade via /plans.",
        "rss_add_format": "Format: /rss add https://example.com/rss.xml",
        "rss_unknown_action": "Unknown RSS action.\n\nAvailable: /rss list, /rss add URL, /rss off number, /rss on number, /rss remove number.",
        "tg_add_format": "Format: /tg add @channel or /tg add https://t.me/channel",
        "tg_available": "Available: /tg add @channel, /tg blocks, /tg off 1, /tg on 1",
        "tgblocks_available": "Available: /tgblocks, /tgblocks off 1, /tgblocks on 1",
        "paid_tg_only": "Telegram channel packages are available only in paid plans. Upgrade via /plans.",
        "tg_block_number_prompt": "Send a package number: 1, 2, 3... or open /tgblocks.",
        "tg_block_updated": "TG package {block} {status}. Sources changed: {changed}.",
        "paid_tg_empty": "Paid Telegram sources have not been added yet.",
        "paid_tg_title": "Paid Telegram packages:",
        "active_word": "active",
        "tg_blocks_total": "Total: {active}/{total} active.",
        "tg_blocks_hint": "Buttons below disable or enable the whole package.",
        "tg_blocks_commands": "Commands: /tgblocks off 1, /tgblocks on 1.",
        "top_block_first": "Top 50 ({start}-{end})",
        "top_block": "Top {end} ({start}-{end})",
        "invalid_rss_url": "Send a valid RSS feed URL starting with http:// or https://.",
        "rss_read_failed": "Could not read this RSS feed. Check the URL and try again.",
        "rss_empty": "The RSS feed opened, but the bot did not find news in it. The source was not added.",
        "custom_rss_added": "Custom RSS source added",
        "custom_rss_exists": "This RSS source already exists",
        "invalid_tg_url": "Send a username or URL of a public Telegram channel. Example: @channel",
        "tg_read_failed": "Could not read this Telegram channel. Check that it is public and available through t.me/s/.",
        "tg_empty": "The channel opened, but the bot did not find available posts. The source was not added.",
        "custom_tg_added": "Telegram channel added",
        "custom_tg_exists": "This Telegram channel already exists",
        "source_lookup_prompt": "Send a number from the list, @username, or source URL.",
        "custom_sources_not_disabled": "Custom sources cannot be disabled. Remove them with the remove-my-source button.",
        "source_already_disabled": "This source is already disabled.",
        "source_disabled": "Source disabled: {source}",
        "custom_sources_already_active": "Custom sources are already active. Remove a source if you no longer need it.",
        "source_already_enabled": "This source is already enabled.",
        "source_enabled": "Source enabled: {source}",
        "custom_source_lookup_prompt": "Send the number, @username, or URL of your own source from the list.",
        "standard_sources_not_removed": "Standard RSS sources cannot be removed. You can disable them.",
        "custom_source_removed": "Custom source removed",
        "source_not_found": "Source not found",
        "sources_title": "Sources: {active} active of {total}",
        "source_kind_custom": "custom",
        "source_kind_standard": "standard",
        "paid_tg_summary": "Paid Telegram channels: {active}/{total} active.",
        "paid_tg_manage_hint": "Manage them in blocks of 50 with the TG packages button or /tgblocks.",
        "rss_commands_hint": "Commands: /rss off number, /rss on number, /rss add URL, /rss remove number",
        "default_source_name": "My source",
        "plan_free_description": "1 keyword, standard RSS, no paid TG channel database, 15 alerts per day, monitoring once per hour",
        "plan_basic_description": "10 keywords, 3 custom RSS/TG sources, paid TG channel database and TG packages, 100 alerts per day, monitoring every 30 minutes",
        "plan_pro_description": "50 keywords, 15 custom RSS/TG sources, paid TG channel database and TG packages, full text, 500 alerts per day, monitoring every 30 minutes",
        "plan_business_description": "unlimited keywords, unlimited RSS/TG sources, paid TG channel database and TG packages, full text, unlimited alerts, monitoring every 5 minutes",
        "plan_paid_template": "{name}: {stars} Stars / {days} days. {description}",
        "plan_free_template": "{name}: {description}",
    },
    "uk": {
        "button_add": "➕ Додати ключ",
        "button_remove": "➖ Видалити ключ",
        "button_info": "📋 Мій моніторинг",
        "button_check": "🔎 Перевірити зараз",
        "button_sources": "📰 Джерела",
        "button_report": "📄 Звіт",
        "button_filters": "⚙️ Фільтри",
        "button_text_mode": "🧾 Режим тексту",
        "button_plans": "💳 Тарифи",
        "button_help": "ℹ️ Допомога",
        "button_app": "📱 Кабінет",
        "button_source_list": "📋 Список джерел",
        "button_tg_blocks": "📦 TG-пакети",
        "button_sources_file": "📎 Файл джерел",
        "button_source_add": "➕ Додати RSS",
        "button_tg_add": "➕ Додати TG",
        "button_source_disable": "⛔ Вимкнути джерело",
        "button_source_enable": "✅ Увімкнути джерело",
        "button_source_remove": "🗑️ Видалити моє джерело",
        "button_full_text_on": "✅ Повний текст",
        "button_full_text_off": "⚡ RSS-анонс",
        "button_stop_add": "🚫 Додати стоп-слово",
        "button_stop_remove": "✅ Видалити стоп-слово",
        "button_plus_add": "➕ Додати плюс-слово",
        "button_plus_remove": "➖ Видалити плюс-слово",
        "button_back": "⬅️ Головне меню",
        "button_language": "🌐 Мова",
        "button_country": "🌍 Регіон",
        "button_settings": "⚙️ Налаштування",
        "help_text": (
            "Monitorio моніторить онлайн-медіа та публічні Telegram-канали за ключовими словами.\n\n"
            "Автоматичний моніторинг: Free раз на годину, Basic/Pro кожні 30 хвилин, Business кожні 5 хвилин.\n"
            "Додайте ключі, оберіть країну, і бот надсилатиме нові згадки.\n\n"
            "Команди:\n"
            "/add ключ - додати ключ\n"
            "/remove ключ - видалити ключ\n"
            "/settings - мова, регіон і режим тексту\n"
            "/rss list - показати RSS і Telegram-джерела\n"
            "/rss add URL - додати власне RSS-джерело\n"
            "/tg add @channel - додати публічний Telegram-канал\n"
            "/tgblocks - керувати TG-пакетами по 50\n"
            "/sourcesfile - отримати CSV з номерами джерел\n"
            "/check - перевірити зараз\n"
            "/report - отримати CSV-звіт"
        ),
        "filters_title": "Налаштування фільтрів:",
        "main_menu_title": "Головне меню:",
        "choose_menu_action": "Оберіть дію в меню або скористайтеся /help.",
        "prompt_add_keyword": "Надішліть ключову фразу одним повідомленням.",
        "prompt_remove_keyword": "Надішліть ключову фразу, яку потрібно видалити.",
        "prompt_add_stop_word": "Надішліть стоп-слово одним повідомленням.",
        "prompt_remove_stop_word": "Надішліть стоп-слово, яке потрібно видалити.",
        "prompt_add_plus_word": "Надішліть плюс-слово одним повідомленням.",
        "prompt_remove_plus_word": "Надішліть плюс-слово, яке потрібно видалити.",
        "prompt_add_rss": "Надішліть URL RSS-стрічки. Наприклад:\nhttps://example.com/rss.xml",
        "prompt_add_tg": "Надішліть username або URL публічного Telegram-каналу. Наприклад:\n@channel\nhttps://t.me/channel",
        "prompt_disable_source": "Надішліть номер, @username або URL джерела, яке потрібно вимкнути.",
        "prompt_enable_source": "Надішліть номер, @username або URL джерела, яке потрібно увімкнути.",
        "prompt_remove_source": "Надішліть номер, @username або URL власного джерела, яке потрібно видалити.",
        "keyword_label": "Ключову фразу",
        "stop_word_label": "Стоп-слово",
        "plus_word_label": "Плюс-слово",
        "added": "додано",
        "already_exists": "вже є",
        "removed": "видалено",
        "not_found": "не знайдено",
        "empty_terms": "немає",
        "fulltext_unavailable": "Пошук у повному тексті доступний у тарифах Pro та Business.",
        "fulltext_enabled": "Режим повного тексту увімкнено. Бот шукатиме в заголовку, RSS-анонсі та тексті сторінки.",
        "fast_mode_enabled": "Швидкий режим увімкнено. Бот шукатиме тільки в заголовку та RSS-анонсі.",
        "info_title": "Мій моніторинг",
        "keywords": "Ключові фрази",
        "stop_words": "Стоп-слова",
        "plus_words": "Плюс-слова",
        "search_mode": "Режим пошуку",
        "active_sources": "Активні джерела",
        "auto_check": "Автоматична перевірка",
        "interval_business": "кожні 5 хвилин",
        "interval_paid": "кожні 30 хвилин",
        "interval_free": "раз на годину",
        "text_mode_intro": "Режим пошуку визначає, де бот шукає ваші ключові слова.",
        "current_mode": "Поточний режим",
        "text_mode_note": "Повний текст точніший, але перевірка триває довше і залежить від доступності сайту.",
        "manual_check_start": "Починаю ручну перевірку джерел.",
        "manual_check_busy": "Фонова перевірка ще триває довше хвилини. Спробуйте /check трохи пізніше.",
        "manual_check_done": "Перевірку завершено. Нових сповіщень надіслано: {sent}",
        "sources_file_caption": "Таблиця джерел: номери, TG-рейтинг, підписники і команди вимкнення",
        "report_caption": "CSV-звіт за знайденими згадками",
        "mini_app_business_only": "Кабінет доступний тільки у тарифі Business. Оновіть тариф через /plans.",
        "mini_app_bad_data": "Mini App надіслав некоректні дані.",
        "mini_app_unknown_action": "Невідома дія Mini App.",
        "mini_app_action_failed": "Не вдалося виконати дію з Mini App. Спробуйте ще раз.",
        "message_failed": "Не вдалося обробити повідомлення. Спробуйте ще раз.",
        "fulltext_status": "Пошук у повному тексті {status}.",
        "status_enabled": "увімкнено",
        "status_disabled": "вимкнено",
        "plans_title": "Тарифи Telegram Stars:",
        "current_plan": "Поточний тариф",
        "expires_at": "Діє до",
        "no_expiry": "немає",
        "payment_command": "Оплата",
        "plan_activation_note": "Після оплати тариф активується автоматично на 30 днів.",
        "choose_paid_plan": "Оберіть платний тариф: /buy basic, /buy pro або /buy business.",
        "invoice_title": "Тариф {plan} на {days} днів",
        "invoice_price_label": "{plan} / {days} днів",
        "unknown_plan_checkout": "Невідомий тариф. Спробуйте оформити оплату ще раз.",
        "payment_unknown_plan": "Оплату отримано, але тариф не розпізнано. Напишіть адміністратору.",
        "payment_success": "Оплату отримано. Тариф {plan} {status} до {expires}.",
        "payment_status_activated": "активовано",
        "payment_status_already": "вже було активовано",
        "admin_only": "Ця команда доступна тільки адміністратору.",
        "grant_format": "Формат: /grant chat_id pro 30",
        "grant_plan_format": "Формат: /grant chat_id basic|pro|business 30",
        "grant_success": "Видано {plan} для {chat_id} до {expires}.",
        "users_count": "Користувачів у базі: {total}",
        "users_shown": "Показано останніх активних: {shown}",
        "users_empty": "Користувачів ще немає.",
        "users_plan_line": "   тариф: {plan}; ключів: {keywords}; власних джерел: {sources}",
        "users_last_seen": "   остання активність: {last_seen}",
        "users_expires": "   діє до: {expires}",
        "keyword_limit": "Ліміт ключів для тарифу {plan}: {limit}. Оновіть тариф через /plans.",
        "custom_rss_limit": "Ліміт власних RSS для тарифу {plan}: {limit}. Оновіть тариф через /plans.",
        "custom_source_limit": "Ліміт власних джерел для тарифу {plan}: {limit}. Оновіть тариф через /plans.",
        "rss_add_format": "Формат: /rss add https://example.com/rss.xml",
        "rss_unknown_action": "Невідома дія RSS.\n\nДоступно: /rss list, /rss add URL, /rss off номер, /rss on номер, /rss remove номер.",
        "tg_add_format": "Формат: /tg add @channel або /tg add https://t.me/channel",
        "tg_available": "Доступно: /tg add @channel, /tg blocks, /tg off 1, /tg on 1",
        "tgblocks_available": "Доступно: /tgblocks, /tgblocks off 1, /tgblocks on 1",
        "paid_tg_only": "Пакети Telegram-каналів доступні тільки у платних тарифах. Оновіть тариф через /plans.",
        "tg_block_number_prompt": "Надішліть номер пакета: 1, 2, 3... або відкрийте /tgblocks.",
        "tg_block_updated": "TG-пакет {block} {status}. Змінено джерел: {changed}.",
        "paid_tg_empty": "Платні Telegram-джерела ще не додані.",
        "paid_tg_title": "Платні Telegram-пакети:",
        "active_word": "активні",
        "tg_blocks_total": "Разом: {active}/{total} активні.",
        "tg_blocks_hint": "Кнопки нижче вимикають або вмикають весь пакет.",
        "tg_blocks_commands": "Команди: /tgblocks off 1, /tgblocks on 1.",
        "top_block_first": "Топ 50 ({start}-{end})",
        "top_block": "Топ {end} ({start}-{end})",
        "invalid_rss_url": "Надішліть коректний URL RSS-стрічки, який починається з http:// або https://.",
        "rss_read_failed": "Не вдалося прочитати цю RSS-стрічку. Перевірте URL і спробуйте ще раз.",
        "rss_empty": "RSS-стрічка відкрилася, але бот не знайшов у ній новин. Таке джерело не додано.",
        "custom_rss_added": "Власне RSS-джерело додано",
        "custom_rss_exists": "Таке RSS-джерело вже є",
        "invalid_tg_url": "Надішліть username або URL публічного Telegram-каналу. Наприклад: @channel",
        "tg_read_failed": "Не вдалося прочитати цей Telegram-канал. Перевірте, що канал публічний і доступний через t.me/s/.",
        "tg_empty": "Канал відкрився, але бот не знайшов доступних постів. Джерело не додано.",
        "custom_tg_added": "Telegram-канал додано",
        "custom_tg_exists": "Такий Telegram-канал уже є",
        "source_lookup_prompt": "Надішліть номер зі списку, @username або URL джерела.",
        "custom_sources_not_disabled": "Власні джерела не вимикаються. Їх можна видалити кнопкою видалення власного джерела.",
        "source_already_disabled": "Це джерело вже вимкнене.",
        "source_disabled": "Джерело вимкнено: {source}",
        "custom_sources_already_active": "Власні джерела вже активні. Якщо джерело не потрібне, видаліть його.",
        "source_already_enabled": "Це джерело вже увімкнене.",
        "source_enabled": "Джерело увімкнено: {source}",
        "custom_source_lookup_prompt": "Надішліть номер власного джерела зі списку, @username або URL.",
        "standard_sources_not_removed": "Стандартні RSS не видаляються. Їх можна вимкнути.",
        "custom_source_removed": "Власне джерело видалено",
        "source_not_found": "Джерело не знайдено",
        "sources_title": "Джерела: {active} активних із {total}",
        "source_kind_custom": "власне",
        "source_kind_standard": "стандартне",
        "paid_tg_summary": "Платні Telegram-канали: {active}/{total} активні.",
        "paid_tg_manage_hint": "Керуйте ними блоками по 50 через кнопку TG-пакети або команду /tgblocks.",
        "rss_commands_hint": "Команди: /rss off номер, /rss on номер, /rss add URL, /rss remove номер",
        "default_source_name": "Моє джерело",
        "plan_free_description": "1 ключ, стандартні RSS, без бази платних TG-каналів, 15 сповіщень на день, моніторинг раз на годину",
        "plan_basic_description": "10 ключів, 3 власні RSS/TG, база платних TG-каналів і TG-пакети, 100 сповіщень на день, моніторинг кожні 30 хвилин",
        "plan_pro_description": "50 ключів, 15 власних RSS/TG, база платних TG-каналів і TG-пакети, повний текст, 500 сповіщень на день, моніторинг кожні 30 хвилин",
        "plan_business_description": "безлімітні ключі, безлімітні RSS/TG, база платних TG-каналів і TG-пакети, повний текст, безлімітні сповіщення, моніторинг кожні 5 хвилин",
        "plan_paid_template": "{name}: {stars} Stars / {days} днів. {description}",
        "plan_free_template": "{name}: {description}",
    },
}

for language_code in ("pl", "de", "es", "it", "be"):
    EXTRA_MESSAGES[language_code] = {
        **EXTRA_MESSAGES["en"],
        **MESSAGES[language_code],
    }

EXTRA_MESSAGES["pl"].update(
    {
        "button_add": "➕ Dodaj słowo",
        "button_remove": "➖ Usuń słowo",
        "button_info": "📋 Mój monitoring",
        "button_check": "🔎 Sprawdź teraz",
        "button_sources": "📰 Źródła",
        "button_report": "📄 Raport",
        "button_filters": "⚙️ Filtry",
        "button_text_mode": "🧾 Tryb tekstu",
        "button_plans": "💳 Plany",
        "button_help": "ℹ️ Pomoc",
        "button_settings": "⚙️ Ustawienia",
        "button_back": "⬅️ Menu główne",
        "help_text": EXTRA_MESSAGES["en"]["help_text"].replace("Monitorio monitors", "Monitorio monitoruje"),
        "filters_title": "Ustawienia filtrów:",
        "main_menu_title": "Menu główne:",
        "choose_menu_action": "Wybierz akcję z menu albo użyj /help.",
        "prompt_add_keyword": "Wyślij słowo kluczowe w jednej wiadomości.",
        "prompt_remove_keyword": "Wyślij słowo kluczowe, które chcesz usunąć.",
        "prompt_add_stop_word": "Wyślij stop-słowo w jednej wiadomości.",
        "prompt_remove_stop_word": "Wyślij stop-słowo, które chcesz usunąć.",
        "prompt_add_plus_word": "Wyślij wymagane słowo w jednej wiadomości.",
        "prompt_remove_plus_word": "Wyślij wymagane słowo, które chcesz usunąć.",
        "keyword_label": "Słowo kluczowe",
        "stop_word_label": "Stop-słowo",
        "plus_word_label": "Wymagane słowo",
        "added": "dodano",
        "already_exists": "już istnieje",
        "removed": "usunięto",
        "not_found": "nie znaleziono",
        "empty_terms": "brak",
        "fulltext_unavailable": "Wyszukiwanie w pełnym tekście jest dostępne w planach Pro i Business.",
        "fulltext_enabled": "Tryb pełnego tekstu jest włączony.",
        "fast_mode_enabled": "Szybki tryb jest włączony.",
        "info_title": "Mój monitoring",
        "keywords": "Słowa kluczowe",
        "stop_words": "Stop-słowa",
        "plus_words": "Wymagane słowa",
        "search_mode": "Tryb wyszukiwania",
        "active_sources": "Aktywne źródła",
        "auto_check": "Automatyczne sprawdzanie",
        "manual_check_start": "Rozpoczynam ręczne sprawdzanie źródeł.",
        "manual_check_done": "Sprawdzanie zakończone. Wysłane nowe powiadomienia: {sent}",
    }
)

EXTRA_MESSAGES["de"].update(
    {
        "button_add": "➕ Keyword hinzufügen",
        "button_remove": "➖ Keyword entfernen",
        "button_info": "📋 Mein Monitoring",
        "button_check": "🔎 Jetzt prüfen",
        "button_sources": "📰 Quellen",
        "button_report": "📄 Bericht",
        "button_filters": "⚙️ Filter",
        "button_text_mode": "🧾 Textmodus",
        "button_plans": "💳 Tarife",
        "button_help": "ℹ️ Hilfe",
        "button_settings": "⚙️ Einstellungen",
        "button_back": "⬅️ Hauptmenü",
        "help_text": EXTRA_MESSAGES["en"]["help_text"].replace("Monitorio monitors", "Monitorio beobachtet"),
        "filters_title": "Filtereinstellungen:",
        "main_menu_title": "Hauptmenü:",
        "choose_menu_action": "Wähle eine Aktion im Menü oder nutze /help.",
        "prompt_add_keyword": "Sende das Keyword in einer Nachricht.",
        "prompt_remove_keyword": "Sende das Keyword, das du entfernen möchtest.",
        "prompt_add_stop_word": "Sende das Stoppwort in einer Nachricht.",
        "prompt_remove_stop_word": "Sende das Stoppwort, das du entfernen möchtest.",
        "prompt_add_plus_word": "Sende das Pflichtwort in einer Nachricht.",
        "prompt_remove_plus_word": "Sende das Pflichtwort, das du entfernen möchtest.",
        "keyword_label": "Keyword",
        "stop_word_label": "Stoppwort",
        "plus_word_label": "Pflichtwort",
        "added": "hinzugefügt",
        "already_exists": "existiert bereits",
        "removed": "entfernt",
        "not_found": "nicht gefunden",
        "empty_terms": "keine",
        "fulltext_unavailable": "Volltextsuche ist in Pro und Business verfügbar.",
        "fulltext_enabled": "Volltextmodus ist aktiviert.",
        "fast_mode_enabled": "Schnellmodus ist aktiviert.",
        "info_title": "Mein Monitoring",
        "keywords": "Keywords",
        "stop_words": "Stoppwörter",
        "plus_words": "Pflichtwörter",
        "search_mode": "Suchmodus",
        "active_sources": "Aktive Quellen",
        "auto_check": "Automatische Prüfung",
        "manual_check_start": "Manuelle Quellenprüfung wird gestartet.",
        "manual_check_done": "Prüfung abgeschlossen. Neue Benachrichtigungen gesendet: {sent}",
    }
)

EXTRA_MESSAGES["es"].update(
    {
        "button_add": "➕ Añadir clave",
        "button_remove": "➖ Eliminar clave",
        "button_info": "📋 Mi monitoreo",
        "button_check": "🔎 Comprobar ahora",
        "button_sources": "📰 Fuentes",
        "button_report": "📄 Informe",
        "button_filters": "⚙️ Filtros",
        "button_text_mode": "🧾 Modo de texto",
        "button_plans": "💳 Planes",
        "button_help": "ℹ️ Ayuda",
        "button_settings": "⚙️ Configuración",
        "button_back": "⬅️ Menú principal",
        "help_text": EXTRA_MESSAGES["en"]["help_text"].replace("Monitorio monitors", "Monitorio monitoriza"),
        "filters_title": "Configuración de filtros:",
        "main_menu_title": "Menú principal:",
        "choose_menu_action": "Elige una acción del menú o usa /help.",
        "prompt_add_keyword": "Envía la palabra clave en un solo mensaje.",
        "prompt_remove_keyword": "Envía la palabra clave que quieres eliminar.",
        "prompt_add_stop_word": "Envía la palabra excluida en un solo mensaje.",
        "prompt_remove_stop_word": "Envía la palabra excluida que quieres eliminar.",
        "prompt_add_plus_word": "Envía la palabra obligatoria en un solo mensaje.",
        "prompt_remove_plus_word": "Envía la palabra obligatoria que quieres eliminar.",
        "keyword_label": "Palabra clave",
        "stop_word_label": "Palabra excluida",
        "plus_word_label": "Palabra obligatoria",
        "added": "añadida",
        "already_exists": "ya existe",
        "removed": "eliminada",
        "not_found": "no encontrada",
        "empty_terms": "ninguna",
        "fulltext_unavailable": "La búsqueda de texto completo está disponible en Pro y Business.",
        "fulltext_enabled": "El modo de texto completo está activado.",
        "fast_mode_enabled": "El modo rápido está activado.",
        "info_title": "Mi monitoreo",
        "keywords": "Palabras clave",
        "stop_words": "Palabras excluidas",
        "plus_words": "Palabras obligatorias",
        "search_mode": "Modo de búsqueda",
        "active_sources": "Fuentes activas",
        "auto_check": "Comprobación automática",
        "manual_check_start": "Inicio la comprobación manual de fuentes.",
        "manual_check_done": "Comprobación completada. Nuevas notificaciones enviadas: {sent}",
    }
)

EXTRA_MESSAGES["it"].update(
    {
        "button_add": "➕ Aggiungi chiave",
        "button_remove": "➖ Rimuovi chiave",
        "button_info": "📋 Il mio monitoraggio",
        "button_check": "🔎 Controlla ora",
        "button_sources": "📰 Fonti",
        "button_report": "📄 Report",
        "button_filters": "⚙️ Filtri",
        "button_text_mode": "🧾 Modalità testo",
        "button_plans": "💳 Piani",
        "button_help": "ℹ️ Aiuto",
        "button_settings": "⚙️ Impostazioni",
        "button_back": "⬅️ Menu principale",
        "help_text": EXTRA_MESSAGES["en"]["help_text"].replace("Monitorio monitors", "Monitorio monitora"),
        "filters_title": "Impostazioni filtri:",
        "main_menu_title": "Menu principale:",
        "choose_menu_action": "Scegli un'azione dal menu o usa /help.",
        "prompt_add_keyword": "Invia la parola chiave in un solo messaggio.",
        "prompt_remove_keyword": "Invia la parola chiave che vuoi rimuovere.",
        "prompt_add_stop_word": "Invia la parola esclusa in un solo messaggio.",
        "prompt_remove_stop_word": "Invia la parola esclusa che vuoi rimuovere.",
        "prompt_add_plus_word": "Invia la parola obbligatoria in un solo messaggio.",
        "prompt_remove_plus_word": "Invia la parola obbligatoria che vuoi rimuovere.",
        "keyword_label": "Parola chiave",
        "stop_word_label": "Parola esclusa",
        "plus_word_label": "Parola obbligatoria",
        "added": "aggiunta",
        "already_exists": "esiste già",
        "removed": "rimossa",
        "not_found": "non trovata",
        "empty_terms": "nessuna",
        "fulltext_unavailable": "La ricerca nel testo completo è disponibile nei piani Pro e Business.",
        "fulltext_enabled": "La modalità testo completo è attiva.",
        "fast_mode_enabled": "La modalità rapida è attiva.",
        "info_title": "Il mio monitoraggio",
        "keywords": "Parole chiave",
        "stop_words": "Parole escluse",
        "plus_words": "Parole obbligatorie",
        "search_mode": "Modalità di ricerca",
        "active_sources": "Fonti attive",
        "auto_check": "Controllo automatico",
        "manual_check_start": "Avvio il controllo manuale delle fonti.",
        "manual_check_done": "Controllo completato. Nuove notifiche inviate: {sent}",
    }
)

EXTRA_MESSAGES["be"].update(
    {
        "button_add": "➕ Дадаць ключ",
        "button_remove": "➖ Выдаліць ключ",
        "button_info": "📋 Мой маніторынг",
        "button_check": "🔎 Праверыць зараз",
        "button_sources": "📰 Крыніцы",
        "button_report": "📄 Справаздача",
        "button_filters": "⚙️ Фільтры",
        "button_text_mode": "🧾 Рэжым тэксту",
        "button_plans": "💳 Тарыфы",
        "button_help": "ℹ️ Дапамога",
        "button_settings": "⚙️ Налады",
        "button_back": "⬅️ Галоўнае меню",
        "help_text": EXTRA_MESSAGES["en"]["help_text"].replace("Monitorio monitors", "Monitorio маніторыць"),
        "filters_title": "Налады фільтраў:",
        "main_menu_title": "Галоўнае меню:",
        "choose_menu_action": "Выберыце дзеянне ў меню або скарыстайцеся /help.",
        "prompt_add_keyword": "Адпраўце ключавую фразу адным паведамленнем.",
        "prompt_remove_keyword": "Адпраўце ключавую фразу, якую трэба выдаліць.",
        "prompt_add_stop_word": "Адпраўце стоп-слова адным паведамленнем.",
        "prompt_remove_stop_word": "Адпраўце стоп-слова, якое трэба выдаліць.",
        "prompt_add_plus_word": "Адпраўце абавязковае слова адным паведамленнем.",
        "prompt_remove_plus_word": "Адпраўце абавязковае слова, якое трэба выдаліць.",
        "keyword_label": "Ключавая фраза",
        "stop_word_label": "Стоп-слова",
        "plus_word_label": "Абавязковае слова",
        "added": "дададзена",
        "already_exists": "ужо ёсць",
        "removed": "выдалена",
        "not_found": "не знойдзена",
        "empty_terms": "няма",
        "fulltext_unavailable": "Пошук у поўным тэксце даступны ў тарыфах Pro і Business.",
        "fulltext_enabled": "Рэжым поўнага тэксту ўключаны.",
        "fast_mode_enabled": "Хуткі рэжым уключаны.",
        "info_title": "Мой маніторынг",
        "keywords": "Ключавыя фразы",
        "stop_words": "Стоп-словы",
        "plus_words": "Абавязковыя словы",
        "search_mode": "Рэжым пошуку",
        "active_sources": "Актыўныя крыніцы",
        "auto_check": "Аўтаматычная праверка",
        "manual_check_start": "Пачынаю ручную праверку крыніц.",
        "manual_check_done": "Праверка завершана. Новых апавяшчэнняў адпраўлена: {sent}",
    }
)

for language_code, messages in EXTRA_MESSAGES.items():
    MESSAGES.setdefault(language_code, {}).update(messages)


def language_name(code: str) -> str:
    return LANGUAGES.get(normalize_language(code), LANGUAGES[DEFAULT_LANGUAGE]).name


def language_button_text(code: str) -> str:
    language = LANGUAGES.get(normalize_language(code), LANGUAGES[DEFAULT_LANGUAGE])
    flag = LANGUAGE_FLAGS.get(language.code, "")
    return f"{flag} {language.button}".strip()


def country_name(code: str, language_code: str) -> str:
    country = COUNTRIES.get(normalize_country(code), COUNTRIES[DEFAULT_COUNTRY])
    language = normalize_language(language_code)
    return country.name_by_language.get(language) or country.name_by_language[DEFAULT_LANGUAGE]


def country_button_text(code: str, language_code: str) -> str:
    country_code = normalize_country(code)
    flag = COUNTRY_FLAGS.get(country_code, "")
    return f"{flag} {country_name(country_code, language_code)}".strip()


def normalize_language(value: str | None) -> str:
    code = (value or "").strip().lower()
    return code if code in LANGUAGES else DEFAULT_LANGUAGE


def normalize_country(value: str | None) -> str:
    code = (value or "").strip().lower()
    if code == "uk":
        code = "gb"
    if code == "belarus":
        code = "by"
    return code if code in COUNTRIES else DEFAULT_COUNTRY


def language_from_button(value: str) -> str | None:
    needle = value.strip().lower()
    for language in LANGUAGES.values():
        names = {
            language.code,
            language.button.lower(),
            language.name.lower(),
            language_button_text(language.code).lower(),
        }
        if needle in names:
            return language.code
    return None


def country_from_button(value: str) -> str | None:
    needle = value.strip().lower()
    for country in COUNTRIES.values():
        names = {
            country.code,
            country.button.lower(),
            *(country_button_text(country.code, language_code).lower() for language_code in LANGUAGES),
            *(name.lower() for name in country.name_by_language.values()),
        }
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
