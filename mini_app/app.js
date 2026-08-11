(function () {
  const tg = window.Telegram && window.Telegram.WebApp;
  const apiBase = configuredApiBase();
  const hiddenMentionSourceTypes = new Set(["threads", "reddit"]);
  const threadsUiEnabled = false;
  let loaderHidden = false;
  let recentRequestId = 0;
  const state = {
    data: null,
    recent: [],
    language: "en",
    pendingLanguage: "",
    newsSort: "date",
    newsFilters: {
      country: "",
      date: "",
      keyword: "",
      source: "",
      source_type: ""
    },
    reportFilters: {
      country: "",
      keyword: "",
      source: "",
      source_type: ""
    },
    sourceQuery: "",
    sourcePage: {}
  };

  const labels = {
    en: {
      plan: "Plan",
      sources: "Sources",
      monitoringSources: "total in monitoring",
      today: "Today",
      tabNews: "News",
      tabSettings: "Settings",
      tabFilters: "Filters",
      tabSources: "Sources",
      recentMentions: "Recent mentions",
      refresh: "Refresh",
      checkNow: "Check now",
      csvReport: "CSV report",
      downloadCsv: "Download CSV",
      sortNews: "Sort",
      sortDate: "Date",
      sortCountry: "Country",
      sortKeyword: "Keyword",
      sortSource: "Source",
      csvPeriod: "Report period",
      csvDay: "Previous day",
      csvWeek: "Last 7 days",
      csvDownloading: "Preparing CSV report...",
      csvDownloaded: "CSV report downloaded.",
      filterCountry: "Country",
      filterDate: "Date",
      filterKeyword: "Keyword",
      filterSource: "Source",
      allCountries: "All countries",
      allDates: "All dates",
      allKeywords: "All keywords",
      allSources: "All sources",
      dateDay: "Last 24 hours",
      dateWeek: "Last 7 days",
      monitorInterval: "News delivery interval",
      intervalBusinessHint: "1 minute is available only on Business. You can choose up to once per day.",
      intervalPlanHint: "Your current plan allows this interval range.",
      language: "Language",
      region: "Monitoring region",
      autoMonitoring: "Automatic monitoring",
      fullText: "Full text",
      plans: "Plans",
      keyword: "Keyword",
      keywordPlaceholder: "for example: bitcoin",
      addKeyword: "Add keyword",
      stopWord: "Stop word",
      stopPlaceholder: "word to exclude",
      plusWord: "Required word",
      plusPlaceholder: "extra condition",
      add: "Add",
      addRss: "Add RSS",
      rssPlaceholder: "https://example.com or https://example.com/rss.xml",
      addTelegram: "Add Telegram",
      addTg: "Add TG",
      tgPlaceholder: "@channel or https://t.me/channel",
      tgBlocks: "TG packages",
      sourceOverview: "Source overview",
      sourcesFile: "Sources file",
      sourceSearchPlaceholder: "Search sources",
      sourcesMore: "+{count} more — use search",
      sourcesNoMatch: "No sources found",
      sourcesFreeNote: "Free plan: top 20 RSS sources and top 20 Telegram channels from any selected country. Upgrade to unlock all sources.",
      opening: "Opening cabinet...",
      openTelegram: "Open this Mini App through Telegram.",
      loadError: "Could not load the cabinet.",
      sent: "Action sent to the bot.",
      typeKeyword: "Enter a keyword phrase.",
      typeStop: "Enter a stop word.",
      typePlus: "Enter a required word.",
      typeRss: "Enter a site URL or RSS URL.",
      typeTg: "Enter a Telegram channel.",
      noNews: "No mentions found yet",
      noNewsHint: "Run a check or add keywords for the selected region.",
      automatic: "Scheduled checks enabled",
      manual: "Manual checks only",
      fullTextOn: "Full-text search enabled",
      fullTextDelayWarning: "Checks may take longer because the bot opens article pages.",
      fullTextOff: "Fast title and RSS-summary search",
      fullTextBusinessOnly: "Full-text search is available only on Business.",
      locked: "Mini App locked",
      active: "active",
      open: "Open",
      remove: "Remove",
      off: "Off",
      on: "On"
    },
    uk: {
      plan: "Тариф",
      sources: "Джерела",
      monitoringSources: "усього в моніторингу",
      today: "Сьогодні",
      tabNews: "Новини",
      tabSettings: "Налаштування",
      tabFilters: "Фільтри",
      tabSources: "Джерела",
      recentMentions: "Останні згадки",
      refresh: "Оновити",
      checkNow: "Перевірити зараз",
      csvReport: "CSV-звіт",
      downloadCsv: "Завантажити CSV",
      sortNews: "Сортування",
      sortDate: "Дата",
      sortCountry: "Країна",
      sortKeyword: "Ключ",
      sortSource: "Джерело",
      csvPeriod: "Період звіту",
      csvDay: "Попередня доба",
      csvWeek: "Останні 7 днів",
      csvDownloading: "Готуємо CSV-звіт...",
      csvDownloaded: "CSV-звіт завантажено.",
      filterCountry: "Країна",
      filterDate: "Дата",
      filterKeyword: "Ключ",
      filterSource: "Джерело",
      allCountries: "Усі країни",
      allDates: "Усі дати",
      allKeywords: "Усі ключі",
      allSources: "Усі джерела",
      dateDay: "Останні 24 години",
      dateWeek: "Останні 7 днів",
      monitorInterval: "Інтервал видачі новин",
      intervalBusinessHint: "1 хвилина доступна тільки на Business. Максимум - раз на добу.",
      intervalPlanHint: "Ваш тариф дозволяє цей діапазон інтервалів.",
      language: "Мова",
      region: "Регіон моніторингу",
      autoMonitoring: "Автоматичний моніторинг",
      fullText: "Повний текст",
      plans: "Тарифи",
      keyword: "Ключове слово",
      keywordPlaceholder: "наприклад: bitcoin",
      addKeyword: "Додати ключ",
      stopWord: "Стоп-слово",
      stopPlaceholder: "слово для виключення",
      plusWord: "Обов'язкове слово",
      plusPlaceholder: "додаткова умова",
      add: "Додати",
      addRss: "Додати RSS",
      rssPlaceholder: "https://example.com або https://example.com/rss.xml",
      addTelegram: "Додати Telegram",
      addTg: "Додати TG",
      tgPlaceholder: "@channel або https://t.me/channel",
      tgBlocks: "TG-пакети",
      sourceOverview: "Огляд джерел",
      sourcesFile: "Файл джерел",
      sourceSearchPlaceholder: "Пошук джерел",
      sourcesMore: "+{count} ще — скористайтесь пошуком",
      sourcesNoMatch: "Джерел не знайдено",
      sourcesFreeNote: "Безкоштовний тариф: топ-20 RSS та топ-20 Telegram-каналів з будь-якої обраної країни. Оновіть тариф, щоб відкрити всі джерела.",
      opening: "Відкриваємо кабінет...",
      openTelegram: "Відкрийте Mini App через Telegram.",
      loadError: "Не вдалося завантажити кабінет.",
      sent: "Дію надіслано боту.",
      typeKeyword: "Введіть ключову фразу.",
      typeStop: "Введіть стоп-слово.",
      typePlus: "Введіть обов'язкове слово.",
      typeRss: "Введіть URL сайту або RSS.",
      typeTg: "Введіть Telegram-канал.",
      noNews: "Поки немає знайдених згадок",
      noNewsHint: "Запустіть перевірку або додайте ключі для вибраного регіону.",
      automatic: "Планові перевірки увімкнені",
      manual: "Тільки ручні перевірки",
      fullTextOn: "Пошук у повному тексті увімкнено",
      fullTextDelayWarning: "Якщо увімкнено, перевірка може тривати довше: бот відкриває сторінки новин.",
      fullTextOff: "Швидкий пошук за заголовком і RSS-анонсом",
      fullTextBusinessOnly: "Повний текст доступний тільки на Business.",
      locked: "Mini App заблоковано",
      active: "активні",
      open: "Відкрити",
      remove: "Видалити",
      off: "Вимк.",
      on: "Увімк."
    },
    ru: {
      plan: "Тариф",
      sources: "Источники",
      monitoringSources: "всего в мониторинге",
      today: "Сегодня",
      tabNews: "Новости",
      tabSettings: "Настройки",
      tabFilters: "Фильтры",
      tabSources: "Источники",
      recentMentions: "Последние упоминания",
      refresh: "Обновить",
      checkNow: "Проверить сейчас",
      csvReport: "CSV-отчет",
      downloadCsv: "Скачать CSV",
      sortNews: "Сортировка",
      sortDate: "Дата",
      sortCountry: "Страна",
      sortKeyword: "Ключ",
      sortSource: "Источник",
      csvPeriod: "Период отчета",
      csvDay: "Предыдущие сутки",
      csvWeek: "Последние 7 дней",
      csvDownloading: "Готовим CSV-отчет...",
      csvDownloaded: "CSV-отчет загружен.",
      filterCountry: "Страна",
      filterDate: "Дата",
      filterKeyword: "Ключ",
      filterSource: "Источник",
      allCountries: "Все страны",
      allDates: "Все даты",
      allKeywords: "Все ключи",
      allSources: "Все источники",
      dateDay: "Последние 24 часа",
      dateWeek: "Последние 7 дней",
      monitorInterval: "Интервал выдачи новостей",
      intervalBusinessHint: "1 минута доступна только на Business. Максимум - раз в сутки.",
      intervalPlanHint: "Ваш тариф позволяет этот диапазон интервалов.",
      language: "Язык",
      region: "Регион мониторинга",
      autoMonitoring: "Автоматический мониторинг",
      fullText: "Полный текст",
      plans: "Тарифы",
      keyword: "Ключевое слово",
      keywordPlaceholder: "например: bitcoin",
      addKeyword: "Добавить ключ",
      stopWord: "Стоп-слово",
      stopPlaceholder: "слово для исключения",
      plusWord: "Обязательное слово",
      plusPlaceholder: "дополнительное условие",
      add: "Добавить",
      addRss: "Добавить RSS",
      rssPlaceholder: "https://example.com или https://example.com/rss.xml",
      addTelegram: "Добавить Telegram",
      addTg: "Добавить TG",
      tgPlaceholder: "@channel или https://t.me/channel",
      tgBlocks: "TG-пакеты",
      sourceOverview: "Обзор источников",
      sourcesFile: "Файл источников",
      sourceSearchPlaceholder: "Поиск источников",
      sourcesMore: "+{count} ещё — воспользуйтесь поиском",
      sourcesNoMatch: "Источники не найдены",
      sourcesFreeNote: "Бесплатный тариф: топ-20 RSS и топ-20 Telegram-каналов из любой выбранной страны. Оформите тариф, чтобы открыть все источники.",
      opening: "Открываем кабинет...",
      openTelegram: "Откройте Mini App через Telegram.",
      loadError: "Не удалось загрузить кабинет.",
      sent: "Действие отправлено боту.",
      typeKeyword: "Введите ключевую фразу.",
      typeStop: "Введите стоп-слово.",
      typePlus: "Введите обязательное слово.",
      typeRss: "Введите URL сайта или RSS.",
      typeTg: "Введите Telegram-канал.",
      noNews: "Пока нет найденных упоминаний",
      noNewsHint: "Запустите проверку или добавьте ключи для выбранного региона.",
      automatic: "Плановые проверки включены",
      manual: "Только ручные проверки",
      fullTextOn: "Поиск по полному тексту включен",
      fullTextDelayWarning: "Если включено, проверка может длиться дольше: бот открывает страницы новостей.",
      fullTextOff: "Быстрый поиск по заголовку и RSS-анонсу",
      fullTextBusinessOnly: "Полный текст доступен только на Business.",
      locked: "Mini App заблокирован",
      active: "активны",
      open: "Открыть",
      remove: "Удалить",
      off: "Выкл.",
      on: "Вкл."
    },
    pl: {
      plan: "Pakiet",
      sources: "Źródła",
      monitoringSources: "łącznie w monitoringu",
      today: "Dzisiaj",
      tabNews: "Wiadomości",
      tabSettings: "Ustawienia",
      tabFilters: "Filtry",
      tabSources: "Źródła",
      recentMentions: "Ostatnie wzmianki",
      refresh: "Odśwież",
      checkNow: "Sprawdź teraz",
      csvReport: "Raport CSV",
      downloadCsv: "Pobierz CSV",
      sortNews: "Sortowanie",
      sortDate: "Data",
      sortCountry: "Kraj",
      sortKeyword: "Słowo",
      sortSource: "Źródło",
      csvPeriod: "Okres raportu",
      csvDay: "Poprzednia doba",
      csvWeek: "Ostatnie 7 dni",
      csvDownloading: "Przygotowujemy raport CSV...",
      csvDownloaded: "Raport CSV pobrany.",
      filterCountry: "Kraj",
      filterDate: "Data",
      filterKeyword: "Słowo",
      filterSource: "Źródło",
      allCountries: "Wszystkie kraje",
      allDates: "Wszystkie daty",
      allKeywords: "Wszystkie słowa",
      allSources: "Wszystkie źródła",
      dateDay: "Ostatnie 24 godziny",
      dateWeek: "Ostatnie 7 dni",
      monitorInterval: "Interwał dostarczania wiadomości",
      intervalBusinessHint: "1 minuta jest dostępna tylko w Business. Maksimum to raz dziennie.",
      intervalPlanHint: "Twój plan pozwala na ten zakres interwałów.",
      language: "Język",
      region: "Region monitoringu",
      autoMonitoring: "Automatyczny monitoring",
      fullText: "Pełny tekst",
      plans: "Plany",
      keyword: "Słowo kluczowe",
      keywordPlaceholder: "na przykład: bitcoin",
      addKeyword: "Dodaj słowo",
      stopWord: "Słowo stop",
      stopPlaceholder: "słowo do wykluczenia",
      plusWord: "Słowo wymagane",
      plusPlaceholder: "dodatkowy warunek",
      add: "Dodaj",
      addRss: "Dodaj RSS",
      rssPlaceholder: "https://example.com lub https://example.com/rss.xml",
      addTelegram: "Dodaj Telegram",
      addTg: "Dodaj TG",
      tgPlaceholder: "@channel lub https://t.me/channel",
      tgBlocks: "Pakiety TG",
      sourceOverview: "Przegląd źródeł",
      sourcesFile: "Plik źródeł",
      sourceSearchPlaceholder: "Szukaj źródeł",
      sourcesMore: "+{count} więcej — użyj wyszukiwania",
      sourcesNoMatch: "Nie znaleziono źródeł",
      sourcesFreeNote: "Plan darmowy: top 20 RSS i top 20 kanałów Telegram z dowolnego wybranego kraju. Ulepsz plan, aby odblokować wszystkie źródła.",
      opening: "Otwieranie panelu...",
      openTelegram: "Otwórz Mini App przez Telegram.",
      loadError: "Nie udało się załadować panelu.",
      sent: "Działanie wysłane do bota.",
      typeKeyword: "Wpisz frazę kluczową.",
      typeStop: "Wpisz słowo stop.",
      typePlus: "Wpisz słowo wymagane.",
      typeRss: "Wpisz URL strony lub RSS.",
      typeTg: "Wpisz kanał Telegram.",
      noNews: "Nie ma jeszcze znalezionych wzmianek",
      noNewsHint: "Uruchom sprawdzenie albo dodaj słowa kluczowe dla regionu.",
      automatic: "Zaplanowane kontrole włączone",
      manual: "Tylko ręczne kontrole",
      fullTextOn: "Wyszukiwanie w pełnym tekście włączone",
      fullTextDelayWarning: "Po włączeniu sprawdzanie może trwać dłużej, bo bot otwiera strony artykułów.",
      fullTextOff: "Szybkie wyszukiwanie po tytule i opisie RSS",
      locked: "Mini App zablokowana",
      active: "aktywne",
      open: "Otwórz",
      remove: "Usuń",
      off: "Wył.",
      on: "Wł."
    },
    de: {
      plan: "Tarif",
      sources: "Quellen",
      monitoringSources: "insgesamt im Monitoring",
      today: "Heute",
      tabNews: "Nachrichten",
      tabSettings: "Einstellungen",
      tabFilters: "Filter",
      tabSources: "Quellen",
      recentMentions: "Letzte Treffer",
      refresh: "Aktualisieren",
      checkNow: "Jetzt prüfen",
      csvReport: "CSV-Bericht",
      downloadCsv: "CSV herunterladen",
      sortNews: "Sortierung",
      sortDate: "Datum",
      sortCountry: "Land",
      sortKeyword: "Keyword",
      sortSource: "Quelle",
      csvPeriod: "Berichtszeitraum",
      csvDay: "Vorheriger Tag",
      csvWeek: "Letzte 7 Tage",
      csvDownloading: "CSV-Bericht wird vorbereitet...",
      csvDownloaded: "CSV-Bericht heruntergeladen.",
      filterCountry: "Land",
      filterDate: "Datum",
      filterKeyword: "Keyword",
      filterSource: "Quelle",
      allCountries: "Alle Länder",
      allDates: "Alle Daten",
      allKeywords: "Alle Keywords",
      allSources: "Alle Quellen",
      dateDay: "Letzte 24 Stunden",
      dateWeek: "Letzte 7 Tage",
      monitorInterval: "Intervall für Nachrichtenzustellung",
      intervalBusinessHint: "1 Minute ist nur im Business-Tarif verfügbar. Maximum ist einmal pro Tag.",
      intervalPlanHint: "Dein Tarif erlaubt diesen Intervallbereich.",
      language: "Sprache",
      region: "Monitoring-Region",
      autoMonitoring: "Automatisches Monitoring",
      fullText: "Volltext",
      plans: "Tarife",
      keyword: "Suchwort",
      keywordPlaceholder: "zum Beispiel: bitcoin",
      addKeyword: "Keyword hinzufügen",
      stopWord: "Stoppwort",
      stopPlaceholder: "auszuschließendes Wort",
      plusWord: "Pflichtwort",
      plusPlaceholder: "zusätzliche Bedingung",
      add: "Hinzufügen",
      addRss: "RSS hinzufügen",
      rssPlaceholder: "https://example.com oder https://example.com/rss.xml",
      addTelegram: "Telegram hinzufügen",
      addTg: "TG hinzufügen",
      tgPlaceholder: "@channel oder https://t.me/channel",
      tgBlocks: "TG-Pakete",
      sourceOverview: "Quellenübersicht",
      sourcesFile: "Quellen-Datei",
      sourceSearchPlaceholder: "Quellen suchen",
      sourcesMore: "+{count} mehr — Suche nutzen",
      sourcesNoMatch: "Keine Quellen gefunden",
      sourcesFreeNote: "Kostenloser Plan: Top 20 RSS und Top 20 Telegram-Kanäle aus jedem gewählten Land. Upgrade für alle Quellen.",
      opening: "Kabinett wird geöffnet...",
      openTelegram: "Öffnen Sie die Mini App über Telegram.",
      loadError: "Kabinett konnte nicht geladen werden.",
      sent: "Aktion an den Bot gesendet.",
      typeKeyword: "Keyword-Phrase eingeben.",
      typeStop: "Stoppwort eingeben.",
      typePlus: "Pflichtwort eingeben.",
      typeRss: "Website-URL oder RSS-URL eingeben.",
      typeTg: "Telegram-Kanal eingeben.",
      noNews: "Noch keine Treffer gefunden",
      noNewsHint: "Starten Sie eine Prüfung oder fügen Sie Keywords für die Region hinzu.",
      automatic: "Geplante Prüfungen aktiviert",
      manual: "Nur manuelle Prüfungen",
      fullTextOn: "Volltextsuche aktiviert",
      fullTextDelayWarning: "Wenn aktiviert, kann die Prüfung länger dauern, da der Bot Artikelseiten öffnet.",
      fullTextOff: "Schnelle Suche nach Titel und RSS-Kurztext",
      locked: "Mini App gesperrt",
      active: "aktiv",
      open: "Öffnen",
      remove: "Entfernen",
      off: "Aus",
      on: "Ein"
    },
    es: {
      plan: "Tarifa",
      sources: "Fuentes",
      monitoringSources: "total en monitoreo",
      today: "Hoy",
      tabNews: "Noticias",
      tabSettings: "Ajustes",
      tabFilters: "Filtros",
      tabSources: "Fuentes",
      recentMentions: "Menciones recientes",
      refresh: "Actualizar",
      checkNow: "Comprobar ahora",
      csvReport: "Informe CSV",
      downloadCsv: "Descargar CSV",
      sortNews: "Ordenar",
      sortDate: "Fecha",
      sortCountry: "País",
      sortKeyword: "Clave",
      sortSource: "Fuente",
      csvPeriod: "Periodo del informe",
      csvDay: "Día anterior",
      csvWeek: "Últimos 7 días",
      csvDownloading: "Preparando informe CSV...",
      csvDownloaded: "Informe CSV descargado.",
      filterCountry: "País",
      filterDate: "Fecha",
      filterKeyword: "Clave",
      filterSource: "Fuente",
      allCountries: "Todos los países",
      allDates: "Todas las fechas",
      allKeywords: "Todas las claves",
      allSources: "Todas las fuentes",
      dateDay: "Últimas 24 horas",
      dateWeek: "Últimos 7 días",
      monitorInterval: "Intervalo de entrega de noticias",
      intervalBusinessHint: "1 minuto solo está disponible en Business. Máximo: una vez al día.",
      intervalPlanHint: "Tu plan permite este rango de intervalos.",
      language: "Idioma",
      region: "Región de monitoreo",
      autoMonitoring: "Monitoreo automático",
      fullText: "Texto completo",
      plans: "Planes",
      keyword: "Palabra clave",
      keywordPlaceholder: "por ejemplo: bitcoin",
      addKeyword: "Añadir clave",
      stopWord: "Palabra excluida",
      stopPlaceholder: "palabra a excluir",
      plusWord: "Palabra obligatoria",
      plusPlaceholder: "condición adicional",
      add: "Añadir",
      addRss: "Añadir RSS",
      rssPlaceholder: "https://example.com o https://example.com/rss.xml",
      addTelegram: "Añadir Telegram",
      addTg: "Añadir TG",
      tgPlaceholder: "@channel o https://t.me/channel",
      tgBlocks: "Paquetes TG",
      sourceOverview: "Resumen de fuentes",
      sourcesFile: "Archivo de fuentes",
      sourceSearchPlaceholder: "Buscar fuentes",
      sourcesMore: "+{count} más — usa la búsqueda",
      sourcesNoMatch: "No se encontraron fuentes",
      sourcesFreeNote: "Plan gratis: top 20 RSS y top 20 canales de Telegram de cualquier país elegido. Mejora el plan para desbloquear todas las fuentes.",
      opening: "Abriendo panel...",
      openTelegram: "Abra Mini App desde Telegram.",
      loadError: "No se pudo cargar el panel.",
      sent: "Acción enviada al bot.",
      typeKeyword: "Introduzca una frase clave.",
      typeStop: "Introduzca una palabra excluida.",
      typePlus: "Introduzca una palabra obligatoria.",
      typeRss: "Introduzca una URL de sitio o RSS.",
      typeTg: "Introduzca un canal de Telegram.",
      noNews: "Aún no hay menciones encontradas",
      noNewsHint: "Ejecute una comprobación o añada claves para la región.",
      automatic: "Comprobaciones programadas activadas",
      manual: "Solo comprobaciones manuales",
      fullTextOn: "Búsqueda de texto completo activada",
      fullTextDelayWarning: "Si está activada, la comprobación puede tardar más porque el bot abre las páginas de noticias.",
      fullTextOff: "Búsqueda rápida por título y resumen RSS",
      locked: "Mini App bloqueada",
      active: "activas",
      open: "Abrir",
      remove: "Eliminar",
      off: "Off",
      on: "On"
    },
    it: {
      plan: "Piano",
      sources: "Fonti",
      monitoringSources: "totale nel monitoraggio",
      today: "Oggi",
      tabNews: "Notizie",
      tabSettings: "Impostazioni",
      tabFilters: "Filtri",
      tabSources: "Fonti",
      recentMentions: "Menzioni recenti",
      refresh: "Aggiorna",
      checkNow: "Controlla ora",
      csvReport: "Report CSV",
      downloadCsv: "Scarica CSV",
      sortNews: "Ordina",
      sortDate: "Data",
      sortCountry: "Paese",
      sortKeyword: "Chiave",
      sortSource: "Fonte",
      csvPeriod: "Periodo del report",
      csvDay: "Giorno precedente",
      csvWeek: "Ultimi 7 giorni",
      csvDownloading: "Preparazione report CSV...",
      csvDownloaded: "Report CSV scaricato.",
      filterCountry: "Paese",
      filterDate: "Data",
      filterKeyword: "Chiave",
      filterSource: "Fonte",
      allCountries: "Tutti i paesi",
      allDates: "Tutte le date",
      allKeywords: "Tutte le chiavi",
      allSources: "Tutte le fonti",
      dateDay: "Ultime 24 ore",
      dateWeek: "Ultimi 7 giorni",
      monitorInterval: "Intervallo di consegna notizie",
      intervalBusinessHint: "1 minuto è disponibile solo in Business. Massimo: una volta al giorno.",
      intervalPlanHint: "Il tuo piano consente questo intervallo.",
      language: "Lingua",
      region: "Regione di monitoraggio",
      autoMonitoring: "Monitoraggio automatico",
      fullText: "Testo completo",
      plans: "Piani",
      keyword: "Parola chiave",
      keywordPlaceholder: "ad esempio: bitcoin",
      addKeyword: "Aggiungi chiave",
      stopWord: "Parola esclusa",
      stopPlaceholder: "parola da escludere",
      plusWord: "Parola richiesta",
      plusPlaceholder: "condizione aggiuntiva",
      add: "Aggiungi",
      addRss: "Aggiungi RSS",
      rssPlaceholder: "https://example.com o https://example.com/rss.xml",
      addTelegram: "Aggiungi Telegram",
      addTg: "Aggiungi TG",
      tgPlaceholder: "@channel o https://t.me/channel",
      tgBlocks: "Pacchetti TG",
      sourceOverview: "Panoramica fonti",
      sourcesFile: "File fonti",
      sourceSearchPlaceholder: "Cerca fonti",
      sourcesMore: "+{count} altri — usa la ricerca",
      sourcesNoMatch: "Nessuna fonte trovata",
      sourcesFreeNote: "Piano gratuito: top 20 RSS e top 20 canali Telegram da qualsiasi paese scelto. Esegui l'upgrade per sbloccare tutte le fonti.",
      opening: "Apertura pannello...",
      openTelegram: "Apri Mini App tramite Telegram.",
      loadError: "Impossibile caricare il pannello.",
      sent: "Azione inviata al bot.",
      typeKeyword: "Inserisci una frase chiave.",
      typeStop: "Inserisci una parola esclusa.",
      typePlus: "Inserisci una parola richiesta.",
      typeRss: "Inserisci URL del sito o RSS.",
      typeTg: "Inserisci un canale Telegram.",
      noNews: "Nessuna menzione trovata",
      noNewsHint: "Avvia un controllo o aggiungi parole chiave per la regione.",
      automatic: "Controlli programmati attivati",
      manual: "Solo controlli manuali",
      fullTextOn: "Ricerca nel testo completo attivata",
      fullTextDelayWarning: "Se attiva, il controllo può richiedere più tempo perché il bot apre le pagine delle notizie.",
      fullTextOff: "Ricerca rapida per titolo e sommario RSS",
      locked: "Mini App bloccata",
      active: "attive",
      open: "Apri",
      remove: "Rimuovi",
      off: "Off",
      on: "On"
    },
    be: {
      plan: "Тарыф",
      sources: "Крыніцы",
      monitoringSources: "усяго ў маніторынгу",
      today: "Сёння",
      tabNews: "Навіны",
      tabSettings: "Налады",
      tabFilters: "Фільтры",
      tabSources: "Крыніцы",
      recentMentions: "Апошнія згадкі",
      refresh: "Абнавіць",
      checkNow: "Праверыць зараз",
      csvReport: "CSV-справаздача",
      downloadCsv: "Спампаваць CSV",
      sortNews: "Сартаванне",
      sortDate: "Дата",
      sortCountry: "Краіна",
      sortKeyword: "Ключ",
      sortSource: "Крыніца",
      csvPeriod: "Перыяд справаздачы",
      csvDay: "Папярэднія суткі",
      csvWeek: "Апошнія 7 дзён",
      csvDownloading: "Рыхтуем CSV-справаздачу...",
      csvDownloaded: "CSV-справаздача спампавана.",
      filterCountry: "Краіна",
      filterDate: "Дата",
      filterKeyword: "Ключ",
      filterSource: "Крыніца",
      allCountries: "Усе краіны",
      allDates: "Усе даты",
      allKeywords: "Усе ключы",
      allSources: "Усе крыніцы",
      dateDay: "Апошнія 24 гадзіны",
      dateWeek: "Апошнія 7 дзён",
      monitorInterval: "Інтэрвал выдачы навін",
      intervalBusinessHint: "1 хвіліна даступна толькі на Business. Максімум - раз на суткі.",
      intervalPlanHint: "Ваш тарыф дазваляе гэты дыяпазон інтэрвалаў.",
      language: "Мова",
      region: "Рэгіён маніторынгу",
      autoMonitoring: "Аўтаматычны маніторынг",
      fullText: "Поўны тэкст",
      plans: "Тарыфы",
      keyword: "Ключавое слова",
      keywordPlaceholder: "напрыклад: bitcoin",
      addKeyword: "Дадаць ключ",
      stopWord: "Стоп-слова",
      stopPlaceholder: "слова для выключэння",
      plusWord: "Абавязковае слова",
      plusPlaceholder: "дадатковая ўмова",
      add: "Дадаць",
      addRss: "Дадаць RSS",
      rssPlaceholder: "https://example.com або https://example.com/rss.xml",
      addTelegram: "Дадаць Telegram",
      addTg: "Дадаць TG",
      tgPlaceholder: "@channel або https://t.me/channel",
      tgBlocks: "TG-пакеты",
      sourceOverview: "Агляд крыніц",
      sourcesFile: "Файл крыніц",
      sourceSearchPlaceholder: "Пошук крыніц",
      sourcesMore: "+{count} яшчэ — скарыстайцеся пошукам",
      sourcesNoMatch: "Крыніц не знойдзена",
      sourcesFreeNote: "Бясплатны тарыф: топ-20 RSS і топ-20 Telegram-каналаў з любой абранай краіны. Абнавіце тарыф, каб адкрыць усе крыніцы.",
      opening: "Адкрываем кабінет...",
      openTelegram: "Адкрыйце Mini App праз Telegram.",
      loadError: "Не ўдалося загрузіць кабінет.",
      sent: "Дзеянне адпраўлена боту.",
      typeKeyword: "Увядзіце ключавую фразу.",
      typeStop: "Увядзіце стоп-слова.",
      typePlus: "Увядзіце абавязковае слова.",
      typeRss: "Увядзіце URL сайта або RSS.",
      typeTg: "Увядзіце Telegram-канал.",
      noNews: "Пакуль няма знойдзеных згадак",
      noNewsHint: "Запусціце праверку або дадайце ключы для выбранага рэгіёна.",
      automatic: "Планавыя праверкі ўключаны",
      manual: "Толькі ручныя праверкі",
      fullTextOn: "Пошук па поўным тэксце ўключаны",
      fullTextDelayWarning: "Калі ўключана, праверка можа доўжыцца даўжэй: бот адкрывае старонкі навін.",
      fullTextOff: "Хуткі пошук па загалоўку і RSS-анонсе",
      locked: "Mini App заблакаваны",
      active: "актыўныя",
      open: "Адкрыць",
      remove: "Выдаліць",
      off: "Выкл.",
      on: "Укл."
    }
  };

  const paymentLabels = {
    en: {
      tabPlans: "Plans",
      plansTitle: "Choose a plan",
      plansHint: "Pay with Telegram Stars or crypto without leaving the cabinet.",
      currentPlan: "Current plan",
      starsPay: "Pay with Stars",
      cryptoPay: "Pay crypto",
      validDays: "{days} days",
      noCrypto: "Crypto unavailable",
      paymentOpening: "Opening payment window...",
      paymentPaid: "Payment received. Refreshing cabinet...",
      paymentPending: "Payment window closed. Refresh the cabinet after payment.",
      checkoutError: "Could not open payment. Try again.",
      paymentMethods: "Payment options",
      freePlanTermsTitle: "Free use terms",
      freePlanTermsText: "Free plan includes 1 keyword, top 20 RSS sources and top 20 Telegram channels from any selected country, 15 mentions per day, and automatic monitoring once per hour. Support is available in paid plans."
    },
    uk: {
      tabPlans: "Тарифи",
      plansTitle: "Оберіть тариф",
      plansHint: "Оплачуйте Telegram Stars або криптою без виходу з Кабінету.",
      currentPlan: "Поточний тариф",
      starsPay: "Оплатити Stars",
      cryptoPay: "Оплатити криптою",
      validDays: "{days} днів",
      noCrypto: "Крипто недоступна",
      paymentOpening: "Відкриваю оплату...",
      paymentPaid: "Оплату отримано. Оновлюю Кабінет...",
      paymentPending: "Вікно оплати закрито. Оновіть Кабінет після оплати.",
      checkoutError: "Не вдалося відкрити оплату. Спробуйте ще раз.",
      paymentMethods: "Варіанти оплати",
      freePlanTermsTitle: "Умови безкоштовного використання",
      freePlanTermsText: "Free включає 1 ключове слово, топ-20 RSS та топ-20 Telegram-каналів з будь-якої обраної країни, 15 згадок на день і автоматичний моніторинг раз на годину. Підтримка доступна у платних тарифах."
    },
    ru: {
      tabPlans: "Тарифы",
      plansTitle: "Выберите тариф",
      plansHint: "Оплачивайте Telegram Stars или криптой без выхода из Кабинета.",
      currentPlan: "Текущий тариф",
      starsPay: "Оплатить Stars",
      cryptoPay: "Оплатить криптой",
      validDays: "{days} дней",
      noCrypto: "Крипто недоступна",
      paymentOpening: "Открываю оплату...",
      paymentPaid: "Оплата получена. Обновляю Кабинет...",
      paymentPending: "Окно оплаты закрыто. Обновите Кабинет после оплаты.",
      checkoutError: "Не удалось открыть оплату. Попробуйте еще раз.",
      paymentMethods: "Варианты оплаты",
      freePlanTermsTitle: "Условия бесплатного использования",
      freePlanTermsText: "Free включает 1 ключевое слово, топ-20 RSS и топ-20 Telegram-каналов из любой выбранной страны, 15 упоминаний в день и автоматический мониторинг раз в час. Поддержка доступна в платных тарифах."
    },
    pl: {
      tabPlans: "Plany",
      plansTitle: "Wybierz plan",
      plansHint: "Płać Telegram Stars albo krypto bez opuszczania panelu.",
      currentPlan: "Aktualny plan",
      starsPay: "Zapłać Stars",
      cryptoPay: "Zapłać krypto",
      validDays: "{days} dni",
      noCrypto: "Krypto niedostępne",
      paymentOpening: "Otwieranie płatności...",
      paymentPaid: "Płatność otrzymana. Odświeżam panel...",
      paymentPending: "Okno płatności zamknięte. Odśwież panel po płatności.",
      checkoutError: "Nie udało się otworzyć płatności. Spróbuj ponownie.",
      paymentMethods: "Opcje płatności",
      freePlanTermsTitle: "Warunki darmowego użycia",
      freePlanTermsText: "Free obejmuje 1 słowo kluczowe, top 20 RSS i top 20 kanałów Telegram z dowolnego wybranego kraju, 15 wzmianek dziennie i monitoring raz na godzinę. Wsparcie jest dostępne w płatnych planach."
    },
    de: {
      tabPlans: "Tarife",
      plansTitle: "Tarif wählen",
      plansHint: "Zahlen Sie mit Telegram Stars oder Krypto, ohne das Kabinett zu verlassen.",
      currentPlan: "Aktueller Tarif",
      starsPay: "Mit Stars zahlen",
      cryptoPay: "Mit Krypto zahlen",
      validDays: "{days} Tage",
      noCrypto: "Krypto nicht verfügbar",
      paymentOpening: "Zahlung wird geöffnet...",
      paymentPaid: "Zahlung erhalten. Kabinett wird aktualisiert...",
      paymentPending: "Zahlungsfenster geschlossen. Aktualisieren Sie das Kabinett nach der Zahlung.",
      checkoutError: "Zahlung konnte nicht geöffnet werden. Versuchen Sie es erneut.",
      paymentMethods: "Zahlungsoptionen",
      freePlanTermsTitle: "Bedingungen der kostenlosen Nutzung",
      freePlanTermsText: "Free enthält 1 Keyword, Top 20 RSS und Top 20 Telegram-Kanäle aus jedem gewählten Land, 15 Erwähnungen pro Tag und Monitoring einmal pro Stunde. Support ist in kostenpflichtigen Tarifen verfügbar."
    },
    es: {
      tabPlans: "Planes",
      plansTitle: "Elija un plan",
      plansHint: "Pague con Telegram Stars o cripto sin salir del panel.",
      currentPlan: "Plan actual",
      starsPay: "Pagar con Stars",
      cryptoPay: "Pagar con cripto",
      validDays: "{days} días",
      noCrypto: "Cripto no disponible",
      paymentOpening: "Abriendo pago...",
      paymentPaid: "Pago recibido. Actualizando panel...",
      paymentPending: "Ventana de pago cerrada. Actualice el panel después del pago.",
      checkoutError: "No se pudo abrir el pago. Inténtelo de nuevo.",
      paymentMethods: "Opciones de pago",
      freePlanTermsTitle: "Condiciones del uso gratuito",
      freePlanTermsText: "Free incluye 1 palabra clave, top 20 RSS y top 20 canales de Telegram de cualquier país elegido, 15 menciones al día y monitoreo una vez por hora. El soporte está disponible en planes de pago."
    },
    it: {
      tabPlans: "Piani",
      plansTitle: "Scegli un piano",
      plansHint: "Paga con Telegram Stars o crypto senza uscire dal pannello.",
      currentPlan: "Piano attuale",
      starsPay: "Paga con Stars",
      cryptoPay: "Paga con crypto",
      validDays: "{days} giorni",
      noCrypto: "Crypto non disponibile",
      paymentOpening: "Apertura pagamento...",
      paymentPaid: "Pagamento ricevuto. Aggiorno il pannello...",
      paymentPending: "Finestra di pagamento chiusa. Aggiorna il pannello dopo il pagamento.",
      checkoutError: "Impossibile aprire il pagamento. Riprova.",
      paymentMethods: "Opzioni di pagamento",
      freePlanTermsTitle: "Condizioni dell'uso gratuito",
      freePlanTermsText: "Free include 1 parola chiave, top 20 RSS e top 20 canali Telegram da qualsiasi paese scelto, 15 menzioni al giorno e monitoraggio ogni ora. Il supporto è disponibile nei piani a pagamento."
    },
    be: {
      tabPlans: "Тарыфы",
      plansTitle: "Выберыце тарыф",
      plansHint: "Аплачвайце Telegram Stars або крыптай без выхаду з Кабінета.",
      currentPlan: "Бягучы тарыф",
      starsPay: "Аплаціць Stars",
      cryptoPay: "Аплаціць крыптай",
      validDays: "{days} дзён",
      noCrypto: "Крыпта недаступная",
      paymentOpening: "Адкрываю аплату...",
      paymentPaid: "Аплата атрымана. Абнаўляю Кабінет...",
      paymentPending: "Акно аплаты закрыта. Абнавіце Кабінет пасля аплаты.",
      checkoutError: "Не ўдалося адкрыць аплату. Паспрабуйце яшчэ раз.",
      paymentMethods: "Варыянты аплаты",
      freePlanTermsTitle: "Умовы бясплатнага выкарыстання",
      freePlanTermsText: "Free уключае 1 ключавое слова, топ-20 RSS і топ-20 Telegram-каналаў з любой абранай краіны, 15 згадак на дзень і аўтаматычны маніторынг раз на гадзіну. Падтрымка даступная ў платных тарыфах."
    }
  };

  const helpLabels = {
    en: {
      tabHelp: "Help",
      helpTitle: "How Monitorio works",
      helpIntro: "Monitorio tracks mentions in online media, RSS feeds, and public Telegram channels.",
      helpQuickTitle: "Quick start",
      helpQuickText: "Choose a region, add keywords in Filters, then run a manual check or enable automatic monitoring.",
      helpRegionTitle: "Region logic",
      helpRegionText: "Each keyword is linked to the monitoring region selected when you add it.",
      helpFiltersTitle: "Filter logic",
      helpFiltersText: "Keywords work as OR logic. Stop words block results. Required words add an extra condition.",
      helpSourcesTitle: "Sources and reports",
      helpSourcesText: "In Sources you can turn channels on or off, search the list, and request a CSV source file.",
      helpCustomTitle: "Add your own sources",
      helpCustomText: "You can add any RSS feed that is not in our base — or just paste a website link, and the bot will try to find its RSS automatically. Telegram channels are added by @username or a t.me link.",
      helpPersonalTitle: "Personal plan",
      helpPersonalText: "If the standard limits are not enough, contact support and we will prepare a personal plan for your task.",
      helpSupportTitle: "Support",
      helpSupportText: "Have a question or a suggestion? Write to our support team and we'll help.",
      helpSupportPaidOnly: "Support is available in paid plans.",
      helpSupportButton: "Contact support"
    },
    uk: {
      tabHelp: "Допомога",
      helpTitle: "Як працює Monitorio",
      helpIntro: "Monitorio відстежує згадки в онлайн-медіа, RSS-стрічках і публічних Telegram-каналах.",
      helpQuickTitle: "Швидкий старт",
      helpQuickText: "Оберіть регіон, додайте ключі у Фільтрах, потім запустіть ручну перевірку або увімкніть автоматичний моніторинг.",
      helpRegionTitle: "Логіка регіонів",
      helpRegionText: "Кожен ключ прив'язується до регіону, який був обраний у момент додавання ключа.",
      helpFiltersTitle: "Логіка фільтрів",
      helpFiltersText: "Ключі працюють за логікою OR. Стоп-слова блокують результат. Обов'язкові слова додають додаткову умову.",
      helpSourcesTitle: "Джерела і звіти",
      helpSourcesText: "У Джерелах можна вмикати й вимикати канали, шукати в списку і замовити CSV-файл джерел.",
      helpCustomTitle: "Додавайте власні джерела",
      helpCustomText: "Можна додати будь-який RSS, якого немає в базі, — або просто вставити посилання на сайт, і бот спробує сам знайти його RSS. Telegram-канали додаються через @username або посилання t.me.",
      helpPersonalTitle: "Персональний тариф",
      helpPersonalText: "Якщо стандартних лімітів недостатньо, зверніться в підтримку — ми підготуємо персональний тариф під вашу задачу.",
      helpSupportTitle: "Підтримка",
      helpSupportText: "Виникло питання чи побажання? Напишіть у підтримку — і ми допоможемо.",
      helpSupportPaidOnly: "Підтримка доступна у платних тарифах.",
      helpSupportButton: "Написати в підтримку"
    },
    ru: {
      tabHelp: "Помощь",
      helpTitle: "Как работает Monitorio",
      helpIntro: "Monitorio отслеживает упоминания в онлайн-медиа, RSS-лентах и публичных Telegram-каналах.",
      helpQuickTitle: "Быстрый старт",
      helpQuickText: "Выберите регион, добавьте ключи в Фильтрах, затем запустите ручную проверку или включите автоматический мониторинг.",
      helpRegionTitle: "Логика регионов",
      helpRegionText: "Каждый ключ привязывается к региону, который был выбран в момент добавления ключа.",
      helpFiltersTitle: "Логика фильтров",
      helpFiltersText: "Ключи работают по логике OR. Стоп-слова блокируют результат. Обязательные слова добавляют дополнительное условие.",
      helpSourcesTitle: "Источники и отчеты",
      helpSourcesText: "В Источниках можно включать и выключать каналы, искать по списку и запросить CSV-файл источников.",
      helpCustomTitle: "Добавляйте свои источники",
      helpCustomText: "Можно добавить любой RSS, которого нет в базе, — или просто вставить ссылку на сайт, и бот попробует сам найти его RSS. Telegram-каналы добавляются через @username или ссылку t.me.",
      helpPersonalTitle: "Персональный тариф",
      helpPersonalText: "Если стандартных лимитов недостаточно, обратитесь в поддержку — мы подготовим персональный тариф под вашу задачу.",
      helpSupportTitle: "Поддержка",
      helpSupportText: "Возник вопрос или пожелание? Напишите в поддержку — и мы поможем.",
      helpSupportPaidOnly: "Поддержка доступна в платных тарифах.",
      helpSupportButton: "Написать в поддержку"
    },
    pl: {
      tabHelp: "Pomoc",
      helpTitle: "Jak działa Monitorio",
      helpIntro: "Monitorio śledzi wzmianki w mediach online, kanałach RSS i publicznych kanałach Telegram.",
      helpQuickTitle: "Szybki start",
      helpQuickText: "Wybierz region, dodaj słowa kluczowe w Filtrach, a potem uruchom ręczne sprawdzenie albo monitoring automatyczny.",
      helpRegionTitle: "Logika regionów",
      helpRegionText: "Każde słowo kluczowe jest powiązane z regionem wybranym w momencie jego dodania.",
      helpFiltersTitle: "Logika filtrów",
      helpFiltersText: "Słowa kluczowe działają w logice OR. Stop words blokują wynik. Wymagane słowa dodają warunek dodatkowy.",
      helpSourcesTitle: "Źródła i raporty",
      helpSourcesText: "W Źródłach możesz włączać i wyłączać kanały, przeszukiwać listę i poprosić o plik CSV źródeł.",
      helpCustomTitle: "Dodaj własne źródła",
      helpCustomText: "Możesz dodać dowolny kanał RSS, którego nie ma w bazie — albo po prostu wkleić link do strony, a bot spróbuje sam znaleźć jej RSS. Kanały Telegram dodajesz przez @username lub link t.me.",
      helpPersonalTitle: "Plan indywidualny",
      helpPersonalText: "Jeśli standardowe limity nie wystarczą, skontaktuj się ze wsparciem, a przygotujemy plan indywidualny.",
      helpSupportTitle: "Wsparcie",
      helpSupportText: "Masz pytanie lub sugestię? Napisz do naszego wsparcia, a pomożemy.",
      helpSupportPaidOnly: "Wsparcie jest dostępne w płatnych planach.",
      helpSupportButton: "Napisz do wsparcia"
    },
    de: {
      tabHelp: "Hilfe",
      helpTitle: "So funktioniert Monitorio",
      helpIntro: "Monitorio verfolgt Erwähnungen in Online-Medien, RSS-Feeds und öffentlichen Telegram-Kanälen.",
      helpQuickTitle: "Schnellstart",
      helpQuickText: "Wählen Sie eine Region, fügen Sie Keywords in Filtern hinzu und starten Sie dann eine manuelle Prüfung oder automatisches Monitoring.",
      helpRegionTitle: "Regionenlogik",
      helpRegionText: "Jedes Keyword wird mit der Monitoring-Region verknüpft, die beim Hinzufügen ausgewählt war.",
      helpFiltersTitle: "Filterlogik",
      helpFiltersText: "Keywords arbeiten mit OR-Logik. Stop-Wörter blockieren Ergebnisse. Pflichtwörter ergänzen eine Zusatzbedingung.",
      helpSourcesTitle: "Quellen und Berichte",
      helpSourcesText: "In Quellen können Sie Kanäle ein- und ausschalten, die Liste durchsuchen und eine CSV-Quelldatei anfordern.",
      helpCustomTitle: "Eigene Quellen hinzufügen",
      helpCustomText: "Sie können jeden RSS-Feed hinzufügen, der nicht in unserer Basis ist — oder einfach einen Website-Link einfügen, und der Bot versucht, den RSS-Feed automatisch zu finden. Telegram-Kanäle werden per @username oder t.me-Link hinzugefügt.",
      helpPersonalTitle: "Individueller Tarif",
      helpPersonalText: "Wenn die Standardlimits nicht ausreichen, kontaktieren Sie den Support. Wir bereiten einen individuellen Tarif vor.",
      helpSupportTitle: "Support",
      helpSupportText: "Frage oder Vorschlag? Schreiben Sie unserem Support, wir helfen gern.",
      helpSupportPaidOnly: "Support ist in kostenpflichtigen Tarifen verfügbar.",
      helpSupportButton: "Support kontaktieren"
    },
    es: {
      tabHelp: "Ayuda",
      helpTitle: "Cómo funciona Monitorio",
      helpIntro: "Monitorio rastrea menciones en medios online, RSS y canales públicos de Telegram.",
      helpQuickTitle: "Inicio rápido",
      helpQuickText: "Elija una región, añada palabras clave en Filtros y luego ejecute una comprobación manual o active el monitoreo automático.",
      helpRegionTitle: "Lógica de regiones",
      helpRegionText: "Cada palabra clave se vincula a la región seleccionada en el momento de añadirla.",
      helpFiltersTitle: "Lógica de filtros",
      helpFiltersText: "Las palabras clave funcionan con lógica OR. Las palabras de bloqueo excluyen resultados. Las palabras obligatorias añaden una condición.",
      helpSourcesTitle: "Fuentes e informes",
      helpSourcesText: "En Fuentes puedes activar o desactivar canales, buscar en la lista y solicitar un CSV de fuentes.",
      helpCustomTitle: "Añade tus propias fuentes",
      helpCustomText: "Puedes añadir cualquier RSS que no esté en nuestra base, o simplemente pegar el enlace de un sitio y el bot intentará encontrar su RSS automáticamente. Los canales de Telegram se añaden con @usuario o un enlace t.me.",
      helpPersonalTitle: "Plan personalizado",
      helpPersonalText: "Si los límites estándar no son suficientes, contacta con soporte y prepararemos un plan personalizado.",
      helpSupportTitle: "Soporte",
      helpSupportText: "¿Tienes una pregunta o sugerencia? Escribe a soporte y te ayudaremos.",
      helpSupportPaidOnly: "El soporte está disponible en los planes de pago.",
      helpSupportButton: "Contactar soporte"
    },
    it: {
      tabHelp: "Aiuto",
      helpTitle: "Come funziona Monitorio",
      helpIntro: "Monitorio monitora menzioni in media online, feed RSS e canali Telegram pubblici.",
      helpQuickTitle: "Avvio rapido",
      helpQuickText: "Scegli una regione, aggiungi parole chiave nei Filtri, poi avvia un controllo manuale o abilita il monitoraggio automatico.",
      helpRegionTitle: "Logica delle regioni",
      helpRegionText: "Ogni parola chiave viene collegata alla regione selezionata al momento dell'aggiunta.",
      helpFiltersTitle: "Logica dei filtri",
      helpFiltersText: "Le parole chiave usano la logica OR. Le stop word bloccano i risultati. Le parole obbligatorie aggiungono una condizione.",
      helpSourcesTitle: "Fonti e report",
      helpSourcesText: "In Fonti puoi attivare o disattivare i canali, cercare nell'elenco e richiedere un file CSV delle fonti.",
      helpCustomTitle: "Aggiungi le tue fonti",
      helpCustomText: "Puoi aggiungere qualsiasi feed RSS non presente nella base — o semplicemente incollare il link di un sito e il bot proverà a trovarne il RSS automaticamente. I canali Telegram si aggiungono con @username o un link t.me.",
      helpPersonalTitle: "Piano personalizzato",
      helpPersonalText: "Se i limiti standard non bastano, contatta il supporto e prepareremo un piano personalizzato.",
      helpSupportTitle: "Supporto",
      helpSupportText: "Hai una domanda o un suggerimento? Scrivi al supporto e ti aiuteremo.",
      helpSupportPaidOnly: "Il supporto è disponibile nei piani a pagamento.",
      helpSupportButton: "Contatta il supporto"
    },
    be: {
      tabHelp: "Дапамога",
      helpTitle: "Як працуе Monitorio",
      helpIntro: "Monitorio адсочвае згадкі ў анлайн-медыя, RSS-стужках і публічных Telegram-каналах.",
      helpQuickTitle: "Хуткі старт",
      helpQuickText: "Выберыце рэгіён, дадайце ключы ў Фільтрах, потым запусціце ручную праверку або аўтаматычны маніторынг.",
      helpRegionTitle: "Логіка рэгіёнаў",
      helpRegionText: "Кожны ключ прывязваецца да рэгіёна, які быў выбраны ў момант дадання ключа.",
      helpFiltersTitle: "Логіка фільтраў",
      helpFiltersText: "Ключы працуюць па логіцы OR. Стоп-словы блакуюць вынік. Абавязковыя словы дадаюць дадатковую ўмову.",
      helpSourcesTitle: "Крыніцы і справаздачы",
      helpSourcesText: "У Крыніцах можна ўключаць і выключаць каналы, шукаць у спісе і запытаць CSV-файл крыніц.",
      helpCustomTitle: "Дадавайце свае крыніцы",
      helpCustomText: "Можна дадаць любы RSS, якога няма ў базе, — або проста ўставіць спасылку на сайт, і бот паспрабуе сам знайсці яго RSS. Telegram-каналы дадаюцца праз @username або спасылку t.me.",
      helpPersonalTitle: "Персанальны тарыф",
      helpPersonalText: "Калі стандартных лімітаў недастаткова, звярніцеся ў падтрымку — мы падрыхтуем персанальны тарыф.",
      helpSupportTitle: "Падтрымка",
      helpSupportText: "Узнікла пытанне ці пажаданне? Напішыце ў падтрымку — і мы дапаможам.",
      helpSupportPaidOnly: "Падтрымка даступная ў платных тарыфах.",
      helpSupportButton: "Напісаць у падтрымку"
    }
  };
  Object.keys(paymentLabels).forEach((language) => {
    labels[language] = Object.assign(labels[language] || {}, paymentLabels[language]);
  });
  Object.keys(helpLabels).forEach((language) => {
    labels[language] = Object.assign(labels[language] || {}, helpLabels[language]);
  });

  const cryptoStatusLabels = {
    en: {
      cryptoStatusTitle: "Crypto payment",
      cryptoStatusWaiting: "Waiting for payment",
      cryptoStatusConfirming: "Payment is confirming",
      cryptoStatusPaid: "Payment received",
      cryptoStatusFailed: "Payment failed or expired",
      cryptoStatusUnknown: "Payment status",
      cryptoOpenInvoice: "Open invoice",
      crypto_unavailable: "Crypto payments are not configured yet.",
      crypto_checkout_failed: "Could not create crypto invoice. Try again later.",
      stars_checkout_failed: "Could not open Telegram Stars payment.",
      unknown_payment_method: "Unknown payment method."
    },
    uk: {
      cryptoStatusTitle: "Crypto-оплата",
      cryptoStatusWaiting: "Очікуємо оплату",
      cryptoStatusConfirming: "Оплата підтверджується",
      cryptoStatusPaid: "Оплату отримано",
      cryptoStatusFailed: "Оплата не пройшла або минув час",
      cryptoStatusUnknown: "Статус оплати",
      cryptoOpenInvoice: "Відкрити рахунок",
      crypto_unavailable: "Crypto-оплата ще не налаштована.",
      crypto_checkout_failed: "Не вдалося створити crypto-рахунок. Спробуйте пізніше.",
      stars_checkout_failed: "Не вдалося відкрити оплату Telegram Stars.",
      unknown_payment_method: "Невідомий спосіб оплати."
    },
    ru: {
      cryptoStatusTitle: "Crypto-оплата",
      cryptoStatusWaiting: "Ожидаем оплату",
      cryptoStatusConfirming: "Оплата подтверждается",
      cryptoStatusPaid: "Оплата получена",
      cryptoStatusFailed: "Оплата не прошла или истекла",
      cryptoStatusUnknown: "Статус оплаты",
      cryptoOpenInvoice: "Открыть счет",
      crypto_unavailable: "Crypto-оплата еще не настроена.",
      crypto_checkout_failed: "Не удалось создать crypto-счет. Попробуйте позже.",
      stars_checkout_failed: "Не удалось открыть оплату Telegram Stars.",
      unknown_payment_method: "Неизвестный способ оплаты."
    }
  };
  Object.keys(cryptoStatusLabels).forEach((language) => {
    labels[language] = Object.assign(labels[language] || {}, cryptoStatusLabels[language]);
  });

  const reportLabels = {
    en: {
      tabReport: "Report",
      reportTitle: "Report",
      reportHint: "Choose a period and download mentions in a convenient format.",
      reportPeriod: "Report period",
      downloadXlsx: "Download Excel",
      downloadPdf: "Download PDF",
      reportPreparing: "Preparing report...",
      reportDownloaded: "{format} report downloaded.",
      reportShared: "{format} report is ready to share."
    },
    uk: {
      tabReport: "Звіт",
      reportTitle: "Звіт",
      reportHint: "Оберіть період і завантажте згадки у зручному форматі.",
      reportPeriod: "Період звіту",
      downloadXlsx: "Завантажити Excel",
      downloadPdf: "Завантажити PDF",
      reportPreparing: "Готуємо звіт...",
      reportDownloaded: "Звіт {format} завантажено.",
      reportShared: "Звіт {format} готовий для поширення."
    },
    ru: {
      tabReport: "Отчет",
      reportTitle: "Отчет",
      reportHint: "Выберите период и скачайте упоминания в удобном формате.",
      reportPeriod: "Период отчета",
      downloadXlsx: "Скачать Excel",
      downloadPdf: "Скачать PDF",
      reportPreparing: "Готовим отчет...",
      reportDownloaded: "Отчет {format} загружен.",
      reportShared: "Отчет {format} готов для отправки."
    },
    pl: {
      tabReport: "Raport",
      reportTitle: "Raport",
      reportHint: "Wybierz okres i pobierz wzmianki w wygodnym formacie.",
      reportPeriod: "Okres raportu",
      downloadXlsx: "Pobierz Excel",
      downloadPdf: "Pobierz PDF",
      reportPreparing: "Przygotowujemy raport...",
      reportDownloaded: "Raport {format} pobrany.",
      reportShared: "Raport {format} jest gotowy do udostępnienia."
    },
    de: {
      tabReport: "Bericht",
      reportTitle: "Bericht",
      reportHint: "Wählen Sie den Zeitraum und laden Sie Erwähnungen im passenden Format herunter.",
      reportPeriod: "Berichtszeitraum",
      downloadXlsx: "Excel herunterladen",
      downloadPdf: "PDF herunterladen",
      reportPreparing: "Bericht wird vorbereitet...",
      reportDownloaded: "{format}-Bericht heruntergeladen.",
      reportShared: "{format}-Bericht ist zum Teilen bereit."
    },
    es: {
      tabReport: "Informe",
      reportTitle: "Informe",
      reportHint: "Elija un periodo y descargue las menciones en un formato cómodo.",
      reportPeriod: "Periodo del informe",
      downloadXlsx: "Descargar Excel",
      downloadPdf: "Descargar PDF",
      reportPreparing: "Preparando informe...",
      reportDownloaded: "Informe {format} descargado.",
      reportShared: "Informe {format} listo para compartir."
    },
    it: {
      tabReport: "Report",
      reportTitle: "Report",
      reportHint: "Scegli un periodo e scarica le menzioni nel formato più comodo.",
      reportPeriod: "Periodo del report",
      downloadXlsx: "Scarica Excel",
      downloadPdf: "Scarica PDF",
      reportPreparing: "Preparazione report...",
      reportDownloaded: "Report {format} scaricato.",
      reportShared: "Report {format} pronto per la condivisione."
    },
    be: {
      tabReport: "Справаздача",
      reportTitle: "Справаздача",
      reportHint: "Выберыце перыяд і спампуйце згадкі ў зручным фармаце.",
      reportPeriod: "Перыяд справаздачы",
      downloadXlsx: "Спампаваць Excel",
      downloadPdf: "Спампаваць PDF",
      reportPreparing: "Рыхтуем справаздачу...",
      reportDownloaded: "Справаздача {format} спампаваная.",
      reportShared: "Справаздача {format} гатовая да адпраўкі."
    }
  };
  Object.keys(reportLabels).forEach((language) => {
    labels[language] = Object.assign(labels[language] || {}, reportLabels[language]);
  });

  const aiDigestLabels = {
    en: {
      aiDigestTitle: "AI digest",
      aiDigestHint: "Test feature. Create a short smart summary from your latest mentions.",
      aiDigestPeriod: "Digest period",
      aiDigestCountry: "Country",
      aiDigestKeyword: "Keyword",
      aiDigestSourceType: "Source type",
      aiDigestFocus: "Focus",
      aiDigestMaxMentions: "Mentions to analyze",
      aiDigestAllCountries: "All countries",
      aiDigestAllKeywords: "All keywords",
      aiDigestAllSources: "All sources",
      aiDigestRssOnly: "RSS only",
      aiDigestTelegramOnly: "Telegram only",
      aiDigestRegistryOnly: "Registries only",
      aiDigestFocusOverview: "General overview",
      aiDigestFocusImportant: "Important mentions",
      aiDigestFocusRisks: "Risks",
      aiDigestFocusSources: "Source activity",
      aiDigestFocusActions: "Next steps",
      aiDigestMethodTitle: "How it is formed",
      aiDigestMethodText: "The digest uses only mentions already found by Monitorio for the selected period and filters.",
      aiDigestLast: "Last saved digest",
      aiDigestCreatedAt: "Created",
      aiDigestFilters: "Filters",
      aiDigest12h: "Last 12 hours",
      aiDigest24h: "Last 24 hours",
      aiDigestWeek: "Last 7 days",
      generateAiDigest: "Generate AI digest",
      aiDigestPreparing: "Preparing AI digest...",
      aiDigestReady: "AI digest is ready.",
      aiDigestEmpty: "No mentions found for this period.",
      ai_digest_disabled: "AI digest is not enabled yet.",
      deepseek_key_missing: "DeepSeek API key is not configured yet.",
      deepseek_insufficient_balance: "DeepSeek balance is insufficient. Top up the account and try again.",
      ai_digest_plan_required: "AI digest is available on Pro and Business plans.",
      ai_digest_failed: "Could not create AI digest. Try again later.",
      aiDigestSummary: "Summary",
      aiDigestTopics: "Key topics",
      aiDigestImportant: "Important mentions",
      aiDigestRisks: "Risks",
      aiDigestSources: "Top sources",
      aiDigestSteps: "Next steps"
    },
    uk: {
      aiDigestTitle: "AI-дайджест",
      aiDigestHint: "Тестова функція. Створіть короткий розумний підсумок останніх згадок.",
      aiDigestPeriod: "Період дайджесту",
      aiDigestCountry: "Країна",
      aiDigestKeyword: "Ключове слово",
      aiDigestSourceType: "Тип джерела",
      aiDigestFocus: "Фокус дайджесту",
      aiDigestMaxMentions: "Згадок для аналізу",
      aiDigestAllCountries: "Усі країни",
      aiDigestAllKeywords: "Усі ключі",
      aiDigestAllSources: "Усі джерела",
      aiDigestRssOnly: "Тільки RSS",
      aiDigestTelegramOnly: "Тільки Telegram",
      aiDigestRegistryOnly: "Тільки реєстри",
      aiDigestFocusOverview: "Загальний огляд",
      aiDigestFocusImportant: "Важливі згадки",
      aiDigestFocusRisks: "Ризики",
      aiDigestFocusSources: "Активність джерел",
      aiDigestFocusActions: "Наступні кроки",
      aiDigestMethodTitle: "Як формується",
      aiDigestMethodText: "Дайджест використовує тільки вже знайдені Monitorio згадки за обраний період і фільтри.",
      aiDigestLast: "Останній збережений дайджест",
      aiDigestCreatedAt: "Створено",
      aiDigestFilters: "Фільтри",
      aiDigest12h: "Останні 12 годин",
      aiDigest24h: "Останні 24 години",
      aiDigestWeek: "Останні 7 днів",
      generateAiDigest: "Створити AI-дайджест",
      aiDigestPreparing: "Готуємо AI-дайджест...",
      aiDigestReady: "AI-дайджест готовий.",
      aiDigestEmpty: "За цей період згадок не знайдено.",
      ai_digest_disabled: "AI-дайджест ще не увімкнено.",
      deepseek_key_missing: "DeepSeek API key ще не налаштований.",
      deepseek_insufficient_balance: "На балансі DeepSeek недостатньо коштів. Поповніть акаунт і спробуйте ще раз.",
      ai_digest_plan_required: "AI-дайджест доступний у тарифах Pro та Business.",
      ai_digest_failed: "Не вдалося створити AI-дайджест. Спробуйте пізніше.",
      aiDigestSummary: "Підсумок",
      aiDigestTopics: "Ключові теми",
      aiDigestImportant: "Важливі згадки",
      aiDigestRisks: "Ризики",
      aiDigestSources: "Топ джерел",
      aiDigestSteps: "Наступні кроки"
    },
    pl: {
      aiDigestTitle: "Digest AI",
      aiDigestHint: "Funkcja testowa. Utwórz krótkie inteligentne podsumowanie najnowszych wzmianek.",
      aiDigestPeriod: "Okres digestu",
      aiDigestCountry: "Kraj",
      aiDigestKeyword: "Słowo kluczowe",
      aiDigestSourceType: "Typ źródła",
      aiDigestFocus: "Fokus digestu",
      aiDigestMaxMentions: "Wzmianki do analizy",
      aiDigestAllCountries: "Wszystkie kraje",
      aiDigestAllKeywords: "Wszystkie słowa kluczowe",
      aiDigestAllSources: "Wszystkie źródła",
      aiDigestRssOnly: "Tylko RSS",
      aiDigestTelegramOnly: "Tylko Telegram",
      aiDigestRegistryOnly: "Tylko rejestry",
      aiDigestFocusOverview: "Ogólny przegląd",
      aiDigestFocusImportant: "Ważne wzmianki",
      aiDigestFocusRisks: "Ryzyka",
      aiDigestFocusSources: "Aktywność źródeł",
      aiDigestFocusActions: "Następne kroki",
      aiDigestMethodTitle: "Jak powstaje",
      aiDigestMethodText: "Digest używa tylko wzmianek już znalezionych przez Monitorio dla wybranego okresu i filtrów.",
      aiDigestLast: "Ostatni zapisany digest",
      aiDigestCreatedAt: "Utworzono",
      aiDigestFilters: "Filtry",
      aiDigest12h: "Ostatnie 12 godzin",
      aiDigest24h: "Ostatnie 24 godziny",
      aiDigestWeek: "Ostatnie 7 dni",
      generateAiDigest: "Utwórz digest AI",
      aiDigestPreparing: "Przygotowujemy digest AI...",
      aiDigestReady: "Digest AI jest gotowy.",
      aiDigestEmpty: "Nie znaleziono wzmianek w tym okresie.",
      ai_digest_disabled: "Digest AI nie jest jeszcze włączony.",
      deepseek_key_missing: "Klucz API DeepSeek nie jest jeszcze skonfigurowany.",
      deepseek_insufficient_balance: "Saldo DeepSeek jest niewystarczające. Doładuj konto i spróbuj ponownie.",
      ai_digest_plan_required: "Digest AI jest dostępny w planach Pro i Business.",
      ai_digest_failed: "Nie udało się utworzyć digestu AI. Spróbuj później.",
      aiDigestSummary: "Podsumowanie",
      aiDigestTopics: "Kluczowe tematy",
      aiDigestImportant: "Ważne wzmianki",
      aiDigestRisks: "Ryzyka",
      aiDigestSources: "Najważniejsze źródła",
      aiDigestSteps: "Następne kroki"
    },
    de: {
      aiDigestTitle: "AI-Digest",
      aiDigestHint: "Testfunktion. Erstellen Sie eine kurze intelligente Zusammenfassung der neuesten Erwähnungen.",
      aiDigestPeriod: "Digest-Zeitraum",
      aiDigestCountry: "Land",
      aiDigestKeyword: "Keyword",
      aiDigestSourceType: "Quellentyp",
      aiDigestFocus: "Digest-Fokus",
      aiDigestMaxMentions: "Erwähnungen zur Analyse",
      aiDigestAllCountries: "Alle Länder",
      aiDigestAllKeywords: "Alle Keywords",
      aiDigestAllSources: "Alle Quellen",
      aiDigestRssOnly: "Nur RSS",
      aiDigestTelegramOnly: "Nur Telegram",
      aiDigestRegistryOnly: "Nur Register",
      aiDigestFocusOverview: "Allgemeiner Überblick",
      aiDigestFocusImportant: "Wichtige Erwähnungen",
      aiDigestFocusRisks: "Risiken",
      aiDigestFocusSources: "Quellenaktivität",
      aiDigestFocusActions: "Nächste Schritte",
      aiDigestMethodTitle: "Wie es erstellt wird",
      aiDigestMethodText: "Der Digest nutzt nur Erwähnungen, die Monitorio für den gewählten Zeitraum und die Filter bereits gefunden hat.",
      aiDigestLast: "Letzter gespeicherter Digest",
      aiDigestCreatedAt: "Erstellt",
      aiDigestFilters: "Filter",
      aiDigest12h: "Letzte 12 Stunden",
      aiDigest24h: "Letzte 24 Stunden",
      aiDigestWeek: "Letzte 7 Tage",
      generateAiDigest: "AI-Digest erstellen",
      aiDigestPreparing: "AI-Digest wird vorbereitet...",
      aiDigestReady: "AI-Digest ist bereit.",
      aiDigestEmpty: "Für diesen Zeitraum wurden keine Erwähnungen gefunden.",
      ai_digest_disabled: "AI-Digest ist noch nicht aktiviert.",
      deepseek_key_missing: "Der DeepSeek-API-Schlüssel ist noch nicht konfiguriert.",
      deepseek_insufficient_balance: "Das DeepSeek-Guthaben reicht nicht aus. Laden Sie das Konto auf und versuchen Sie es erneut.",
      ai_digest_plan_required: "AI-Digest ist in den Tarifen Pro und Business verfügbar.",
      ai_digest_failed: "AI-Digest konnte nicht erstellt werden. Versuchen Sie es später erneut.",
      aiDigestSummary: "Zusammenfassung",
      aiDigestTopics: "Kernthemen",
      aiDigestImportant: "Wichtige Erwähnungen",
      aiDigestRisks: "Risiken",
      aiDigestSources: "Top-Quellen",
      aiDigestSteps: "Nächste Schritte"
    },
    es: {
      aiDigestTitle: "Resumen con IA",
      aiDigestHint: "Función de prueba. Crea un resumen inteligente y breve de tus últimas menciones.",
      aiDigestPeriod: "Periodo del resumen",
      aiDigestCountry: "País",
      aiDigestKeyword: "Palabra clave",
      aiDigestSourceType: "Tipo de fuente",
      aiDigestFocus: "Enfoque del resumen",
      aiDigestMaxMentions: "Menciones a analizar",
      aiDigestAllCountries: "Todos los países",
      aiDigestAllKeywords: "Todas las palabras clave",
      aiDigestAllSources: "Todas las fuentes",
      aiDigestRssOnly: "Solo RSS",
      aiDigestTelegramOnly: "Solo Telegram",
      aiDigestRegistryOnly: "Solo registros",
      aiDigestFocusOverview: "Resumen general",
      aiDigestFocusImportant: "Menciones importantes",
      aiDigestFocusRisks: "Riesgos",
      aiDigestFocusSources: "Actividad de fuentes",
      aiDigestFocusActions: "Próximos pasos",
      aiDigestMethodTitle: "Cómo se forma",
      aiDigestMethodText: "El resumen usa solo menciones ya encontradas por Monitorio para el periodo y los filtros seleccionados.",
      aiDigestLast: "Último resumen guardado",
      aiDigestCreatedAt: "Creado",
      aiDigestFilters: "Filtros",
      aiDigest12h: "Últimas 12 horas",
      aiDigest24h: "Últimas 24 horas",
      aiDigestWeek: "Últimos 7 días",
      generateAiDigest: "Generar resumen con IA",
      aiDigestPreparing: "Preparando el resumen con IA...",
      aiDigestReady: "El resumen con IA está listo.",
      aiDigestEmpty: "No se encontraron menciones en este periodo.",
      ai_digest_disabled: "El resumen con IA aún no está activado.",
      deepseek_key_missing: "La clave API de DeepSeek aún no está configurada.",
      deepseek_insufficient_balance: "El saldo de DeepSeek es insuficiente. Recarga la cuenta e inténtalo de nuevo.",
      ai_digest_plan_required: "El resumen con IA está disponible en los planes Pro y Business.",
      ai_digest_failed: "No se pudo crear el resumen con IA. Inténtalo más tarde.",
      aiDigestSummary: "Resumen",
      aiDigestTopics: "Temas clave",
      aiDigestImportant: "Menciones importantes",
      aiDigestRisks: "Riesgos",
      aiDigestSources: "Fuentes principales",
      aiDigestSteps: "Próximos pasos"
    },
    it: {
      aiDigestTitle: "Digest AI",
      aiDigestHint: "Funzione di test. Crea un breve riepilogo intelligente delle ultime menzioni.",
      aiDigestPeriod: "Periodo del digest",
      aiDigestCountry: "Paese",
      aiDigestKeyword: "Parola chiave",
      aiDigestSourceType: "Tipo di fonte",
      aiDigestFocus: "Focus del digest",
      aiDigestMaxMentions: "Menzioni da analizzare",
      aiDigestAllCountries: "Tutti i paesi",
      aiDigestAllKeywords: "Tutte le parole chiave",
      aiDigestAllSources: "Tutte le fonti",
      aiDigestRssOnly: "Solo RSS",
      aiDigestTelegramOnly: "Solo Telegram",
      aiDigestRegistryOnly: "Solo registri",
      aiDigestFocusOverview: "Panoramica generale",
      aiDigestFocusImportant: "Menzioni importanti",
      aiDigestFocusRisks: "Rischi",
      aiDigestFocusSources: "Attività delle fonti",
      aiDigestFocusActions: "Prossimi passi",
      aiDigestMethodTitle: "Come viene creato",
      aiDigestMethodText: "Il digest usa solo le menzioni già trovate da Monitorio per il periodo e i filtri selezionati.",
      aiDigestLast: "Ultimo digest salvato",
      aiDigestCreatedAt: "Creato",
      aiDigestFilters: "Filtri",
      aiDigest12h: "Ultime 12 ore",
      aiDigest24h: "Ultime 24 ore",
      aiDigestWeek: "Ultimi 7 giorni",
      generateAiDigest: "Genera digest AI",
      aiDigestPreparing: "Preparazione del digest AI...",
      aiDigestReady: "Digest AI pronto.",
      aiDigestEmpty: "Nessuna menzione trovata per questo periodo.",
      ai_digest_disabled: "Il digest AI non è ancora attivo.",
      deepseek_key_missing: "La chiave API DeepSeek non è ancora configurata.",
      deepseek_insufficient_balance: "Il saldo DeepSeek è insufficiente. Ricarica l'account e riprova.",
      ai_digest_plan_required: "Il digest AI è disponibile nei piani Pro e Business.",
      ai_digest_failed: "Impossibile creare il digest AI. Riprova più tardi.",
      aiDigestSummary: "Riepilogo",
      aiDigestTopics: "Temi chiave",
      aiDigestImportant: "Menzioni importanti",
      aiDigestRisks: "Rischi",
      aiDigestSources: "Fonti principali",
      aiDigestSteps: "Prossimi passi"
    },
    be: {
      aiDigestTitle: "AI-дайджэст",
      aiDigestHint: "Тэставая функцыя. Стварыце кароткі разумны падсумак апошніх згадак.",
      aiDigestPeriod: "Перыяд дайджэста",
      aiDigestCountry: "Краіна",
      aiDigestKeyword: "Ключавое слова",
      aiDigestSourceType: "Тып крыніцы",
      aiDigestFocus: "Фокус дайджэста",
      aiDigestMaxMentions: "Згадак для аналізу",
      aiDigestAllCountries: "Усе краіны",
      aiDigestAllKeywords: "Усе ключы",
      aiDigestAllSources: "Усе крыніцы",
      aiDigestRssOnly: "Толькі RSS",
      aiDigestTelegramOnly: "Толькі Telegram",
      aiDigestRegistryOnly: "Толькі рэестры",
      aiDigestFocusOverview: "Агульны агляд",
      aiDigestFocusImportant: "Важныя згадкі",
      aiDigestFocusRisks: "Рызыкі",
      aiDigestFocusSources: "Актыўнасць крыніц",
      aiDigestFocusActions: "Наступныя крокі",
      aiDigestMethodTitle: "Як фарміруецца",
      aiDigestMethodText: "Дайджэст выкарыстоўвае толькі ўжо знойдзеныя Monitorio згадкі за абраны перыяд і фільтры.",
      aiDigestLast: "Апошні захаваны дайджэст",
      aiDigestCreatedAt: "Створана",
      aiDigestFilters: "Фільтры",
      aiDigest12h: "Апошнія 12 гадзін",
      aiDigest24h: "Апошнія 24 гадзіны",
      aiDigestWeek: "Апошнія 7 дзён",
      generateAiDigest: "Стварыць AI-дайджэст",
      aiDigestPreparing: "Рыхтуем AI-дайджэст...",
      aiDigestReady: "AI-дайджэст гатовы.",
      aiDigestEmpty: "За гэты перыяд згадак не знойдзена.",
      ai_digest_disabled: "AI-дайджэст яшчэ не ўключаны.",
      deepseek_key_missing: "Ключ API DeepSeek яшчэ не наладжаны.",
      deepseek_insufficient_balance: "На балансе DeepSeek недастаткова сродкаў. Папоўніце акаўнт і паспрабуйце зноў.",
      ai_digest_plan_required: "AI-дайджэст даступны ў тарыфах Pro і Business.",
      ai_digest_failed: "Не ўдалося стварыць AI-дайджэст. Паспрабуйце пазней.",
      aiDigestSummary: "Падсумак",
      aiDigestTopics: "Ключавыя тэмы",
      aiDigestImportant: "Важныя згадкі",
      aiDigestRisks: "Рызыкі",
      aiDigestSources: "Топ крыніц",
      aiDigestSteps: "Наступныя крокі"
    },
    ru: {
      aiDigestTitle: "AI-дайджест",
      aiDigestHint: "Тестовая функция. Создайте короткую умную сводку последних упоминаний.",
      aiDigestPeriod: "Период дайджеста",
      aiDigestCountry: "Страна",
      aiDigestKeyword: "Ключевое слово",
      aiDigestSourceType: "Тип источника",
      aiDigestFocus: "Фокус дайджеста",
      aiDigestMaxMentions: "Упоминаний для анализа",
      aiDigestAllCountries: "Все страны",
      aiDigestAllKeywords: "Все ключи",
      aiDigestAllSources: "Все источники",
      aiDigestRssOnly: "Только RSS",
      aiDigestTelegramOnly: "Только Telegram",
      aiDigestRegistryOnly: "Только реестры",
      aiDigestFocusOverview: "Общий обзор",
      aiDigestFocusImportant: "Важные упоминания",
      aiDigestFocusRisks: "Риски",
      aiDigestFocusSources: "Активность источников",
      aiDigestFocusActions: "Следующие шаги",
      aiDigestMethodTitle: "Как формируется",
      aiDigestMethodText: "Дайджест использует только уже найденные Monitorio упоминания за выбранный период и фильтры.",
      aiDigestLast: "Последний сохраненный дайджест",
      aiDigestCreatedAt: "Создано",
      aiDigestFilters: "Фильтры",
      aiDigest12h: "Последние 12 часов",
      aiDigest24h: "Последние 24 часа",
      aiDigestWeek: "Последние 7 дней",
      generateAiDigest: "Создать AI-дайджест",
      aiDigestPreparing: "Готовим AI-дайджест...",
      aiDigestReady: "AI-дайджест готов.",
      aiDigestEmpty: "За этот период упоминаний не найдено.",
      ai_digest_disabled: "AI-дайджест еще не включен.",
      deepseek_key_missing: "Ключ API DeepSeek еще не настроен.",
      deepseek_insufficient_balance: "На балансе DeepSeek недостаточно средств. Пополните аккаунт и попробуйте снова.",
      ai_digest_plan_required: "AI-дайджест доступен в тарифах Pro и Business.",
      ai_digest_failed: "Не удалось создать AI-дайджест. Попробуйте позже.",
      aiDigestSummary: "Сводка",
      aiDigestTopics: "Ключевые темы",
      aiDigestImportant: "Важные упоминания",
      aiDigestRisks: "Риски",
      aiDigestSources: "Топ источников",
      aiDigestSteps: "Следующие шаги"
    }
  };
  Object.keys(labels).forEach((language) => {
    labels[language] = Object.assign({}, aiDigestLabels.en, labels[language] || {}, aiDigestLabels[language] || {});
  });

  const importanceLabels = {
    en: {
      importanceRating: "Importance rating",
      importanceOn: "Mention importance is shown in alerts and News.",
      importanceOff: "Optional rating is disabled.",
      importanceHigh: "High importance",
      importanceMedium: "Medium importance",
      importanceLow: "Low importance",
      importanceReasons: "Reasons",
      importanceScore: "Importance",
      importance_rating_unavailable: "Importance rating is available on Pro and Business plans."
    },
    uk: {
      importanceRating: "Рейтинг важливості",
      importanceOn: "Важливість згадок показується в сповіщеннях і Новинах.",
      importanceOff: "Опціональний рейтинг вимкнено.",
      importanceHigh: "Висока важливість",
      importanceMedium: "Середня важливість",
      importanceLow: "Низька важливість",
      importanceReasons: "Причини",
      importanceScore: "Важливість",
      importance_rating_unavailable: "Рейтинг важливості доступний у тарифах Pro та Business."
    },
    ru: {
      importanceRating: "Рейтинг важности",
      importanceOn: "Важность упоминаний показывается в уведомлениях и Новостях.",
      importanceOff: "Опциональный рейтинг выключен.",
      importanceHigh: "Высокая важность",
      importanceMedium: "Средняя важность",
      importanceLow: "Низкая важность",
      importanceReasons: "Причины",
      importanceScore: "Важность",
      importance_rating_unavailable: "Рейтинг важности доступен в тарифах Pro и Business."
    },
    pl: {
      importanceRating: "Ocena ważności",
      importanceOn: "Ważność wzmianek jest pokazywana w alertach i Aktualnościach.",
      importanceOff: "Opcjonalna ocena jest wyłączona.",
      importanceHigh: "Wysoka ważność",
      importanceMedium: "Średnia ważność",
      importanceLow: "Niska ważność",
      importanceReasons: "Powody",
      importanceScore: "Ważność",
      importance_rating_unavailable: "Ocena ważności jest dostępna w planach Pro i Business."
    },
    de: {
      importanceRating: "Wichtigkeitsbewertung",
      importanceOn: "Die Wichtigkeit von Treffern wird in Benachrichtigungen und News angezeigt.",
      importanceOff: "Die optionale Bewertung ist deaktiviert.",
      importanceHigh: "Hohe Wichtigkeit",
      importanceMedium: "Mittlere Wichtigkeit",
      importanceLow: "Niedrige Wichtigkeit",
      importanceReasons: "Gründe",
      importanceScore: "Wichtigkeit",
      importance_rating_unavailable: "Die Wichtigkeitsbewertung ist in den Tarifen Pro und Business verfügbar."
    },
    es: {
      importanceRating: "Nivel de importancia",
      importanceOn: "La importancia de las menciones se muestra en alertas y Noticias.",
      importanceOff: "La calificación opcional está desactivada.",
      importanceHigh: "Importancia alta",
      importanceMedium: "Importancia media",
      importanceLow: "Importancia baja",
      importanceReasons: "Motivos",
      importanceScore: "Importancia",
      importance_rating_unavailable: "El nivel de importancia está disponible en los planes Pro y Business."
    },
    it: {
      importanceRating: "Valutazione importanza",
      importanceOn: "L'importanza delle menzioni viene mostrata negli avvisi e nelle Notizie.",
      importanceOff: "La valutazione opzionale è disattivata.",
      importanceHigh: "Importanza alta",
      importanceMedium: "Importanza media",
      importanceLow: "Importanza bassa",
      importanceReasons: "Motivi",
      importanceScore: "Importanza",
      importance_rating_unavailable: "La valutazione importanza è disponibile nei piani Pro e Business."
    },
    be: {
      importanceRating: "Рэйтынг важнасці",
      importanceOn: "Важнасць згадак паказваецца ў апавяшчэннях і Навінах.",
      importanceOff: "Дадатковы рэйтынг выключаны.",
      importanceHigh: "Высокая важнасць",
      importanceMedium: "Сярэдняя важнасць",
      importanceLow: "Нізкая важнасць",
      importanceReasons: "Прычыны",
      importanceScore: "Важнасць",
      importance_rating_unavailable: "Рэйтынг важнасці даступны ў тарыфах Pro і Business."
    }
  };
  Object.keys(labels).forEach((language) => {
    labels[language] = Object.assign({}, importanceLabels.en, labels[language] || {}, importanceLabels[language] || {});
  });

  const quickStartLabels = {
    en: {
      quickStartTitle: "Start in 3 steps",
      quickStartText: "Add a keyword, choose sources, then run a check. You can change details later.",
      quickStartKeyword: "Add keyword",
      quickStartSources: "Choose sources",
      quickStartCheck: "Check now"
    },
    uk: {
      quickStartTitle: "Швидкий старт",
      quickStartText: "Додайте ключ, оберіть джерела й запустіть перевірку. Деталі можна змінити пізніше.",
      quickStartKeyword: "Додати ключ",
      quickStartSources: "Обрати джерела",
      quickStartCheck: "Перевірити"
    },
    ru: {
      quickStartTitle: "Быстрый старт",
      quickStartText: "Добавьте ключ, выберите источники и запустите проверку. Детали можно изменить позже.",
      quickStartKeyword: "Добавить ключ",
      quickStartSources: "Выбрать источники",
      quickStartCheck: "Проверить"
    },
    pl: {
      quickStartTitle: "Szybki start",
      quickStartText: "Dodaj słowo kluczowe, wybierz źródła i uruchom sprawdzenie. Szczegóły możesz zmienić później.",
      quickStartKeyword: "Dodaj klucz",
      quickStartSources: "Wybierz źródła",
      quickStartCheck: "Sprawdź"
    },
    de: {
      quickStartTitle: "Schnellstart",
      quickStartText: "Fügen Sie ein Stichwort hinzu, wählen Sie Quellen aus und starten Sie die Prüfung. Details können Sie später ändern.",
      quickStartKeyword: "Stichwort",
      quickStartSources: "Quellen",
      quickStartCheck: "Prüfen"
    },
    es: {
      quickStartTitle: "Inicio rápido",
      quickStartText: "Añada una palabra clave, elija fuentes e inicie la revisión. Puede cambiar los detalles después.",
      quickStartKeyword: "Añadir clave",
      quickStartSources: "Elegir fuentes",
      quickStartCheck: "Comprobar"
    },
    it: {
      quickStartTitle: "Avvio rapido",
      quickStartText: "Aggiungi una parola chiave, scegli le fonti e avvia il controllo. Potrai modificare i dettagli più tardi.",
      quickStartKeyword: "Aggiungi chiave",
      quickStartSources: "Scegli fonti",
      quickStartCheck: "Controlla"
    },
    be: {
      quickStartTitle: "Хуткі старт",
      quickStartText: "Дадайце ключ, выберыце крыніцы і запусціце праверку. Дэталі можна змяніць пазней.",
      quickStartKeyword: "Дадаць ключ",
      quickStartSources: "Выбраць крыніцы",
      quickStartCheck: "Праверыць"
    }
  };
  Object.keys(quickStartLabels).forEach((language) => {
    labels[language] = Object.assign(labels[language] || {}, quickStartLabels[language]);
  });

  const sourceSummaryLabels = {
    en: {
      sourcesInMonitoring: "sources in monitoring",
      sourceBreakdownTitle: "Sources by country",
      sourceSummaryHint: "Tap to see countries",
      closeSmall: "Close",
      sourceWord: "sources",
      sourceGroupRegistries: "Registries",
      sourceOtherCountry: "Other",
      noSourceBreakdown: "No active sources yet."
    },
    uk: {
      sourcesInMonitoring: "джерел у моніторингу",
      sourceBreakdownTitle: "Джерела за країнами",
      sourceSummaryHint: "Натисніть, щоб побачити країни",
      closeSmall: "Закрити",
      sourceWord: "джерел",
      sourceGroupRegistries: "Реєстри",
      sourceOtherCountry: "Інше",
      noSourceBreakdown: "Активних джерел ще немає."
    },
    ru: {
      sourcesInMonitoring: "источников в мониторинге",
      sourceBreakdownTitle: "Источники по странам",
      sourceSummaryHint: "Нажмите, чтобы увидеть страны",
      closeSmall: "Закрыть",
      sourceWord: "источников",
      sourceGroupRegistries: "Реестры",
      sourceOtherCountry: "Другое",
      noSourceBreakdown: "Активных источников пока нет."
    },
    pl: {
      sourcesInMonitoring: "źródeł w monitoringu",
      sourceBreakdownTitle: "Źródła według kraju",
      sourceSummaryHint: "Dotknij, aby zobaczyć kraje",
      closeSmall: "Zamknij",
      sourceWord: "źródeł",
      sourceGroupRegistries: "Rejestry",
      sourceOtherCountry: "Inne",
      noSourceBreakdown: "Brak aktywnych źródeł."
    },
    de: {
      sourcesInMonitoring: "Quellen im Monitoring",
      sourceBreakdownTitle: "Quellen nach Land",
      sourceSummaryHint: "Tippen, um Länder zu sehen",
      closeSmall: "Schließen",
      sourceWord: "Quellen",
      sourceGroupRegistries: "Register",
      sourceOtherCountry: "Andere",
      noSourceBreakdown: "Noch keine aktiven Quellen."
    },
    es: {
      sourcesInMonitoring: "fuentes en monitoreo",
      sourceBreakdownTitle: "Fuentes por país",
      sourceSummaryHint: "Toque para ver países",
      closeSmall: "Cerrar",
      sourceWord: "fuentes",
      sourceGroupRegistries: "Registros",
      sourceOtherCountry: "Otro",
      noSourceBreakdown: "Aún no hay fuentes activas."
    },
    it: {
      sourcesInMonitoring: "fonti monitorate",
      sourceBreakdownTitle: "Fonti per paese",
      sourceSummaryHint: "Tocca per vedere i paesi",
      closeSmall: "Chiudi",
      sourceWord: "fonti",
      sourceGroupRegistries: "Registri",
      sourceOtherCountry: "Altro",
      noSourceBreakdown: "Nessuna fonte attiva."
    },
    be: {
      sourcesInMonitoring: "крыніц у маніторынгу",
      sourceBreakdownTitle: "Крыніцы па краінах",
      sourceSummaryHint: "Націсніце, каб убачыць краіны",
      closeSmall: "Закрыць",
      sourceWord: "крыніц",
      sourceGroupRegistries: "Рэестры",
      sourceOtherCountry: "Іншае",
      noSourceBreakdown: "Актыўных крыніц пакуль няма."
    }
  };
  Object.keys(sourceSummaryLabels).forEach((language) => {
    labels[language] = Object.assign(labels[language] || {}, sourceSummaryLabels[language]);
  });

  const sourceBulkLabels = {
    en: {
      standardSourcesOff: "Disable standard",
      standardSourcesOn: "Enable standard",
      standardSourcesDisabled: "Standard sources disabled.",
      standardSourcesEnabled: "Standard sources enabled."
    },
    uk: {
      standardSourcesOff: "Вимкнути стандартні",
      standardSourcesOn: "Увімкнути стандартні",
      standardSourcesDisabled: "Стандартні джерела вимкнено.",
      standardSourcesEnabled: "Стандартні джерела увімкнено."
    },
    ru: {
      standardSourcesOff: "Выключить стандартные",
      standardSourcesOn: "Включить стандартные",
      standardSourcesDisabled: "Стандартные источники выключены.",
      standardSourcesEnabled: "Стандартные источники включены."
    },
    pl: {
      standardSourcesOff: "Wyłącz standardowe",
      standardSourcesOn: "Włącz standardowe",
      standardSourcesDisabled: "Standardowe źródła wyłączone.",
      standardSourcesEnabled: "Standardowe źródła włączone."
    },
    de: {
      standardSourcesOff: "Standard deaktivieren",
      standardSourcesOn: "Standard aktivieren",
      standardSourcesDisabled: "Standardquellen deaktiviert.",
      standardSourcesEnabled: "Standardquellen aktiviert."
    },
    es: {
      standardSourcesOff: "Desactivar estándar",
      standardSourcesOn: "Activar estándar",
      standardSourcesDisabled: "Fuentes estándar desactivadas.",
      standardSourcesEnabled: "Fuentes estándar activadas."
    },
    it: {
      standardSourcesOff: "Disattiva standard",
      standardSourcesOn: "Attiva standard",
      standardSourcesDisabled: "Fonti standard disattivate.",
      standardSourcesEnabled: "Fonti standard attivate."
    },
    be: {
      standardSourcesOff: "Адключыць стандартныя",
      standardSourcesOn: "Уключыць стандартныя",
      standardSourcesDisabled: "Стандартныя крыніцы адключаны.",
      standardSourcesEnabled: "Стандартныя крыніцы ўключаны."
    }
  };
  Object.keys(sourceBulkLabels).forEach((language) => {
    labels[language] = Object.assign(labels[language] || {}, sourceBulkLabels[language]);
  });

  const simplifiedUxLabels = {
    en: {
      tabMonitoring: "Monitoring",
      monitoringTitle: "Monitoring setup",
      monitoringHint: "Add keywords, choose a region, and control how often Monitorio checks sources.",
      setupReadyTitle: "Monitoring is ready",
      setupReadyText: "You have keywords and sources. Run a check or leave automatic monitoring on.",
      setupNoKeywordsTitle: "Add your first keyword",
      setupNoKeywordsText: "A keyword can be a brand, person, company, topic, or domain.",
      setupNoSourcesTitle: "Choose sources",
      setupNoSourcesText: "Turn on RSS or Telegram sources so Monitorio knows where to search.",
      setupManualTitle: "Manual mode is on",
      setupManualText: "Automatic checks are disabled. You can still press Check now in News.",
      keywordsTitle: "Keywords and filters",
      keywordsHint: "Keywords find mentions. Stop words remove noise. Required words make results stricter.",
      stopWordHint: "If this word appears in a result, Monitorio will skip it.",
      plusWordHint: "A result must contain this word together with one of your keywords."
      ,
      helpQuickText: "Choose a region, add keywords in Monitoring, then run a manual check or enable automatic monitoring."
    },
    uk: {
      tabMonitoring: "Моніторинг",
      monitoringTitle: "Налаштування моніторингу",
      monitoringHint: "Додайте ключі, оберіть регіон і задайте частоту перевірки джерел.",
      setupReadyTitle: "Моніторинг налаштовано",
      setupReadyText: "Є ключові слова і джерела. Запустіть перевірку або залиште автоматичний режим.",
      setupNoKeywordsTitle: "Додайте перший ключ",
      setupNoKeywordsText: "Ключем може бути бренд, людина, компанія, тема або домен.",
      setupNoSourcesTitle: "Оберіть джерела",
      setupNoSourcesText: "Увімкніть RSS або Telegram-джерела, щоб Monitorio знав, де шукати.",
      setupManualTitle: "Увімкнено ручний режим",
      setupManualText: "Планові перевірки вимкнені. Ви можете натиснути «Перевірити зараз» у Новинах.",
      keywordsTitle: "Ключі та фільтри",
      keywordsHint: "Ключі шукають згадки. Стоп-слова прибирають шум. Обов’язкові слова роблять результат точнішим.",
      stopWordHint: "Якщо це слово є в результаті, Monitorio пропустить таку згадку.",
      plusWordHint: "Результат має містити це слово разом з одним із ваших ключів."
      ,
      helpQuickText: "Оберіть регіон, додайте ключі в Моніторингу, потім запустіть ручну перевірку або увімкніть автоматичний режим."
    },
    ru: {
      tabMonitoring: "Мониторинг",
      monitoringTitle: "Настройка мониторинга",
      monitoringHint: "Добавьте ключи, выберите регион и настройте частоту проверки источников.",
      setupReadyTitle: "Мониторинг настроен",
      setupReadyText: "Есть ключевые слова и источники. Запустите проверку или оставьте автоматический режим.",
      setupNoKeywordsTitle: "Добавьте первый ключ",
      setupNoKeywordsText: "Ключом может быть бренд, человек, компания, тема или домен.",
      setupNoSourcesTitle: "Выберите источники",
      setupNoSourcesText: "Включите RSS или Telegram-источники, чтобы Monitorio знал, где искать.",
      setupManualTitle: "Включен ручной режим",
      setupManualText: "Плановые проверки выключены. Можно нажать «Проверить сейчас» в Новостях.",
      keywordsTitle: "Ключи и фильтры",
      keywordsHint: "Ключи ищут упоминания. Стоп-слова убирают шум. Обязательные слова делают результат точнее.",
      stopWordHint: "Если это слово есть в результате, Monitorio пропустит такое упоминание.",
      plusWordHint: "Результат должен содержать это слово вместе с одним из ваших ключей."
      ,
      helpQuickText: "Выберите регион, добавьте ключи в Мониторинге, затем запустите ручную проверку или включите автоматический режим."
    }
  };
  ["pl", "de", "es", "it", "be"].forEach((language) => {
    simplifiedUxLabels[language] = Object.assign({}, simplifiedUxLabels.en);
  });
  Object.keys(simplifiedUxLabels).forEach((language) => {
    labels[language] = Object.assign(labels[language] || {}, simplifiedUxLabels[language]);
  });

  const threadsLabels = {
    en: {
      sourceTypeAll: "All",
      sourceTypeRss: "RSS",
      sourceTypeTelegram: "Telegram",
      sourceTypeRegistry: "Registries",
      sourceTypeThreads: "Threads",
      sourceTypeReddit: "Reddit",
      threadsSettings: "Threads search",
      threadsHintBusiness: "Available only on Business.",
      threadsHintUnavailable: "Upgrade to Business to enable Threads search.",
      threadsHours: "Time range",
      threadsResultLimit: "Results",
      threadsMediaFilter: "Media",
      threadsLinkFilter: "Links",
      threadsSearchType: "Priority",
      threadsAny: "Any",
      threadsOnlyMedia: "Only with media",
      threadsWithoutMedia: "Without media",
      threadsOnlyLinks: "Only with link",
      threadsWithoutLinks: "Without link",
      threadsRecent: "Newest",
      threadsTop: "Most popular",
      saveThreadsSettings: "Save Threads settings",
      threadsSaved: "Threads settings saved.",
      threadsUnavailable: "Threads search is available only on Business."
    },
    uk: {
      sourceTypeAll: "Усі",
      sourceTypeRss: "RSS",
      sourceTypeTelegram: "Telegram",
      sourceTypeRegistry: "Реєстри",
      sourceTypeThreads: "Threads",
      sourceTypeReddit: "Reddit",
      threadsSettings: "Пошук у Threads",
      threadsHintBusiness: "Доступно тільки на Business.",
      threadsHintUnavailable: "Оновіть тариф до Business, щоб увімкнути Threads.",
      threadsHours: "Діапазон часу",
      threadsResultLimit: "Результати",
      threadsMediaFilter: "Медіа",
      threadsLinkFilter: "Посилання",
      threadsSearchType: "Пріоритет",
      threadsAny: "Будь-які",
      threadsOnlyMedia: "Тільки з медіа",
      threadsWithoutMedia: "Без медіа",
      threadsOnlyLinks: "Тільки з посиланням",
      threadsWithoutLinks: "Без посилання",
      threadsRecent: "Найновіші",
      threadsTop: "Найпопулярніші",
      saveThreadsSettings: "Зберегти Threads",
      threadsSaved: "Налаштування Threads збережено.",
      threadsUnavailable: "Пошук у Threads доступний тільки на Business."
    },
    ru: {
      sourceTypeAll: "Все",
      sourceTypeRss: "RSS",
      sourceTypeTelegram: "Telegram",
      sourceTypeRegistry: "Реестры",
      sourceTypeThreads: "Threads",
      sourceTypeReddit: "Reddit"
    },
    pl: {
      sourceTypeAll: "Wszystkie",
      sourceTypeRss: "RSS",
      sourceTypeTelegram: "Telegram",
      sourceTypeRegistry: "Rejestry",
      sourceTypeThreads: "Threads",
      sourceTypeReddit: "Reddit"
    },
    de: {
      sourceTypeAll: "Alle",
      sourceTypeRss: "RSS",
      sourceTypeTelegram: "Telegram",
      sourceTypeRegistry: "Register",
      sourceTypeThreads: "Threads",
      sourceTypeReddit: "Reddit"
    },
    es: {
      sourceTypeAll: "Todo",
      sourceTypeRss: "RSS",
      sourceTypeTelegram: "Telegram",
      sourceTypeRegistry: "Registros",
      sourceTypeThreads: "Threads",
      sourceTypeReddit: "Reddit"
    },
    it: {
      sourceTypeAll: "Tutti",
      sourceTypeRss: "RSS",
      sourceTypeTelegram: "Telegram",
      sourceTypeRegistry: "Registri",
      sourceTypeThreads: "Threads",
      sourceTypeReddit: "Reddit"
    },
    be: {
      sourceTypeAll: "Усе",
      sourceTypeRss: "RSS",
      sourceTypeTelegram: "Telegram",
      sourceTypeRegistry: "Рэестры",
      sourceTypeThreads: "Threads",
      sourceTypeReddit: "Reddit"
    }
  };
  Object.keys(threadsLabels).forEach((language) => {
    labels[language] = Object.assign(labels[language] || {}, threadsLabels[language]);
  });

  const usabilityLabelOverrides = {
    en: {
      filterButton: "Filters",
      sourceTypeRss: "Online media",
      stepRegionTitle: "1. Choose monitoring region",
      stepRegionHint: "The keyword will be linked to this country.",
      stepKeywordTitle: "2. Add keyword",
      stepKeywordHint: "Use a brand, person, company, topic, or domain."
    },
    uk: {
      filterButton: "Фільтри",
      sourceTypeRss: "онлайн-ЗМІ",
      stepRegionTitle: "1. Оберіть регіон для моніторингу",
      stepRegionHint: "Ключ буде прив'язаний до цієї країни.",
      stepKeywordTitle: "2. Додайте ключове слово",
      stepKeywordHint: "Це може бути бренд, людина, компанія, тема або домен."
    },
    ru: {
      filterButton: "Фильтры",
      sourceTypeRss: "онлайн-СМИ",
      stepRegionTitle: "1. Выберите регион мониторинга",
      stepRegionHint: "Ключ будет привязан к этой стране.",
      stepKeywordTitle: "2. Добавьте ключевое слово",
      stepKeywordHint: "Это может быть бренд, человек, компания, тема или домен."
    },
    pl: {
      filterButton: "Filtry",
      sourceTypeRss: "Media online",
      stepRegionTitle: "1. Wybierz region monitoringu",
      stepRegionHint: "Słowo kluczowe zostanie przypisane do tego kraju.",
      stepKeywordTitle: "2. Dodaj słowo kluczowe",
      stepKeywordHint: "Może to być marka, osoba, firma, temat albo domena."
    },
    de: {
      filterButton: "Filter",
      sourceTypeRss: "Online-Medien",
      stepRegionTitle: "1. Monitoring-Region wählen",
      stepRegionHint: "Das Keyword wird diesem Land zugeordnet.",
      stepKeywordTitle: "2. Keyword hinzufügen",
      stepKeywordHint: "Nutzen Sie Marke, Person, Firma, Thema oder Domain."
    },
    es: {
      filterButton: "Filtros",
      sourceTypeRss: "Medios online",
      stepRegionTitle: "1. Elige la región de monitoreo",
      stepRegionHint: "La clave quedará vinculada a este país.",
      stepKeywordTitle: "2. Añade una clave",
      stepKeywordHint: "Puede ser una marca, persona, empresa, tema o dominio."
    },
    it: {
      filterButton: "Filtri",
      sourceTypeRss: "Media online",
      stepRegionTitle: "1. Scegli la regione di monitoraggio",
      stepRegionHint: "La parola chiave sarà collegata a questo paese.",
      stepKeywordTitle: "2. Aggiungi una chiave",
      stepKeywordHint: "Può essere un brand, persona, azienda, tema o dominio."
    },
    be: {
      filterButton: "Фільтры",
      sourceTypeRss: "анлайн-СМІ",
      stepRegionTitle: "1. Выберыце рэгіён маніторынгу",
      stepRegionHint: "Ключ будзе прывязаны да гэтай краіны.",
      stepKeywordTitle: "2. Дадайце ключавое слова",
      stepKeywordHint: "Гэта можа быць брэнд, чалавек, кампанія, тэма або дамен."
    }
  };
  Object.keys(usabilityLabelOverrides).forEach((language) => {
    labels[language] = Object.assign(labels[language] || {}, usabilityLabelOverrides[language]);
  });
  const keywordFlagLabels = {
    en: {
      keywordPause: "Pause",
      keywordResume: "Resume",
      keywordSilentOn: "Silent",
      keywordSilentOff: "Sound",
      keywordPausedHint: "Paused keywords do not count toward the plan limit.",
      keywordSilentHint: "Silent keywords are monitored, but alerts arrive without sound."
    },
    uk: {
      keywordPause: "Пауза",
      keywordResume: "Увімк.",
      keywordSilentOn: "🔕",
      keywordSilentOff: "🔔",
      keywordPausedHint: "Ключ на паузі не рахується в ліміт тарифу.",
      keywordSilentHint: "Ключ моніториться, але повідомлення приходять без звуку."
    },
    ru: {
      keywordPause: "Пауза",
      keywordResume: "Вкл.",
      keywordSilentOn: "🔕",
      keywordSilentOff: "🔔",
      keywordPausedHint: "Ключ на паузе не считается в лимит тарифа.",
      keywordSilentHint: "Ключ мониторится, но уведомления приходят без звука."
    },
    pl: {
      keywordPause: "Pauza",
      keywordResume: "Włącz",
      keywordSilentOn: "🔕",
      keywordSilentOff: "🔔",
      keywordPausedHint: "Słowo w pauzie nie liczy się do limitu planu.",
      keywordSilentHint: "Słowo jest monitorowane, ale alerty przychodzą bez dźwięku."
    },
    de: {
      keywordPause: "Pause",
      keywordResume: "Aktiv",
      keywordSilentOn: "🔕",
      keywordSilentOff: "🔔",
      keywordPausedHint: "Pausierte Keywords zählen nicht zum Tariflimit.",
      keywordSilentHint: "Das Keyword wird überwacht, Alerts kommen aber lautlos."
    },
    es: {
      keywordPause: "Pausa",
      keywordResume: "Activar",
      keywordSilentOn: "🔕",
      keywordSilentOff: "🔔",
      keywordPausedHint: "Las claves en pausa no cuentan para el límite del plan.",
      keywordSilentHint: "La clave se monitoriza, pero las alertas llegan sin sonido."
    },
    it: {
      keywordPause: "Pausa",
      keywordResume: "Attiva",
      keywordSilentOn: "🔕",
      keywordSilentOff: "🔔",
      keywordPausedHint: "Le chiavi in pausa non contano nel limite del piano.",
      keywordSilentHint: "La chiave viene monitorata, ma gli avvisi arrivano senza suono."
    },
    be: {
      keywordPause: "Паўза",
      keywordResume: "Укл.",
      keywordSilentOn: "🔕",
      keywordSilentOff: "🔔",
      keywordPausedHint: "Ключ на паўзе не лічыцца ў ліміт тарыфу.",
      keywordSilentHint: "Ключ маніторыцца, але апавяшчэнні прыходзяць без гуку."
    }
  };
  Object.keys(keywordFlagLabels).forEach((language) => {
    labels[language] = Object.assign(labels[language] || {}, keywordFlagLabels[language]);
  });

  const $ = (id) => document.getElementById(id);
  const statusText = $("statusText");

  if (tg) {
    document.body.classList.add("in-telegram");
    syncTelegramInsets();
    tg.ready();
    tg.expand();
    try {
      if (typeof tg.requestFullscreen === "function") {
        tg.requestFullscreen();
      }
    } catch (error) {
      /* requestFullscreen is unsupported on older Telegram clients and throws */
    }
    try {
      if (typeof tg.disableVerticalSwipes === "function") {
        tg.disableVerticalSwipes();
      }
    } catch (error) {
      /* disableVerticalSwipes is unsupported on older Telegram clients and throws */
    }
    if (typeof tg.onEvent === "function") {
      tg.onEvent("safeAreaChanged", syncTelegramInsets);
      tg.onEvent("contentSafeAreaChanged", syncTelegramInsets);
      tg.onEvent("viewportChanged", syncTelegramInsets);
    }
  }

  const LANGUAGE_STORAGE_KEY = "monitorioCabinetLanguage";

  function storedLanguage() {
    try {
      const value = window.localStorage.getItem(LANGUAGE_STORAGE_KEY);
      return value && labels[value] ? value : "";
    } catch (error) {
      return "";
    }
  }

  function rememberLanguage(language) {
    if (!language || !labels[language]) return;
    try {
      window.localStorage.setItem(LANGUAGE_STORAGE_KEY, language);
    } catch (error) {
      /* localStorage may be unavailable in some webviews */
    }
  }

  const savedLanguage = storedLanguage();
  if (savedLanguage) {
    state.language = savedLanguage;
  }

  applyTranslations();
  setLoaderText(t("opening"));

  document.querySelectorAll(".tab").forEach((button) => {
    button.addEventListener("click", () => activateTab(button.dataset.tab));
  });
  updateTabsScrollCue();
  const tabsNav = $("tabsNav");
  if (tabsNav) {
    tabsNav.addEventListener("scroll", updateTabsScrollCue, { passive: true });
  }
  window.addEventListener("resize", updateTabsScrollCue);

  $("closeButton").addEventListener("click", () => {
    if (tg) tg.close();
  });

  const sourceSummaryButton = $("sourceSummaryButton");
  const sourceBreakdownPanel = $("sourceBreakdownPanel");
  if (sourceSummaryButton && sourceBreakdownPanel) {
    sourceSummaryButton.addEventListener("click", () => {
      const expanded = sourceSummaryButton.getAttribute("aria-expanded") === "true";
      sourceSummaryButton.setAttribute("aria-expanded", String(!expanded));
      sourceBreakdownPanel.hidden = expanded;
    });
  }
  const sourceBreakdownClose = $("sourceBreakdownClose");
  if (sourceBreakdownClose && sourceBreakdownPanel && sourceSummaryButton) {
    sourceBreakdownClose.addEventListener("click", () => {
      sourceBreakdownPanel.hidden = true;
      sourceSummaryButton.setAttribute("aria-expanded", "false");
    });
  }

  const newsFiltersButton = $("newsFiltersButton");
  const newsControls = $("newsControls");
  if (newsFiltersButton && newsControls) {
    newsFiltersButton.addEventListener("click", () => {
      const nextHidden = !newsControls.hidden;
      newsControls.hidden = nextHidden;
      newsFiltersButton.setAttribute("aria-expanded", String(!nextHidden));
      newsFiltersButton.classList.toggle("is-active", !nextHidden);
    });
  }
  $("checkButton").addEventListener("click", () => sendToChat({ action: "check" }));
  document.querySelectorAll("[data-quick-action]").forEach((button) => {
    button.addEventListener("click", () => {
      const action = button.dataset.quickAction;
      if (action === "keyword") {
        activateTab("monitoring");
        setTimeout(() => $("keywordInput")?.focus(), 80);
        return;
      }
      if (action === "sources") {
        activateTab("sources");
        setTimeout(() => $("sourceSearch")?.focus(), 80);
        return;
      }
      if (action === "check") {
        sendToChat({ action: "check" });
      }
    });
  });
  ["reportCsvButton", "reportXlsxButton", "reportPdfButton"].forEach((id) => {
    const button = $(id);
    if (button) {
      button.addEventListener("click", () => downloadReport(button.dataset.format || "csv"));
    }
  });
  const aiDigestButton = $("aiDigestButton");
  if (aiDigestButton) {
    aiDigestButton.addEventListener("click", generateAiDigest);
  }
  ["newsCountryFilter", "newsDateFilter", "newsKeywordFilter", "newsSourceFilter"].forEach((id) => {
    $(id).addEventListener("change", () => {
      state.newsFilters = {
        country: $("newsCountryFilter").value,
        date: $("newsDateFilter").value,
        keyword: $("newsKeywordFilter").value,
        source: $("newsSourceFilter").value,
        source_type: state.newsFilters.source_type || ""
      };
      reloadRecentForNewsFilters();
    });
  });
  ["reportCountryFilter", "reportKeywordFilter", "reportSourceFilter", "reportSourceTypeFilter"].forEach((id) => {
    const select = $(id);
    if (!select) return;
    select.addEventListener("change", () => {
      state.reportFilters = currentReportFilters();
    });
  });
  document.querySelectorAll(".source-type-tab").forEach((button) => {
    button.addEventListener("click", () => {
      state.newsFilters.source_type = button.dataset.sourceType || "";
      renderSourceTypeTabs();
      reloadRecentForNewsFilters();
    });
  });
  $("intervalRange").addEventListener("change", () => {
    send({ action: "monitor_interval", minutes: Number($("intervalRange").value) || 0 });
  });
  $("intervalRange").addEventListener("input", () => {
    $("intervalValue").textContent = intervalLabel(Number($("intervalRange").value) || 0);
  });
  const plansButton = $("plansButton");
  if (plansButton) {
    plansButton.addEventListener("click", () => activateTab("plans"));
  }
  $("plansRefreshButton").addEventListener("click", loadAll);
  const sourcesFileButton = $("sourcesFileButton");
  if (sourcesFileButton) {
    sourcesFileButton.addEventListener("click", () => sendToChat({ action: "sources_file" }));
  }
  const standardSourcesToggleButton = $("standardSourcesToggleButton");
  if (standardSourcesToggleButton) {
    standardSourcesToggleButton.addEventListener("click", () => {
      const summary = standardSourceSummary(state.data && state.data.sources);
      const enabled = summary.total > 0 && summary.active === 0;
      send({ action: "standard_sources_toggle", enabled });
      showStatus(enabled ? t("standardSourcesEnabled") : t("standardSourcesDisabled"));
      setTimeout(loadAll, 800);
    });
  }

  $("sourceSearch").addEventListener("input", (event) => {
    state.sourceQuery = event.target.value || "";
    state.sourcePage = {};
    if (state.data && state.data.sources) renderSourceOverview(state.data.sources);
  });

  const supportLink = $("supportLink");
  if (supportLink) {
    supportLink.addEventListener("click", (event) => {
      event.preventDefault();
      const url = supportLink.getAttribute("href");
      if (tg && typeof tg.openTelegramLink === "function") {
        tg.openTelegramLink(url);
      } else {
        openLink(url);
      }
    });
  }

  $("languageSelect").addEventListener("change", (event) => {
    const language = event.target.value;
    state.language = language;
    state.pendingLanguage = language;
    rememberLanguage(language);
    applyTranslations();
    if (state.data) {
      renderState();
      renderNewsFilters();
      renderReportFilters();
      renderNews();
    }
    send({ action: "set_language", language });
  });

  $("countrySelect").addEventListener("change", (event) => {
    send({ action: "set_country", country: event.target.value });
  });

  $("autoToggle").addEventListener("click", () => {
    const enabled = !Boolean(state.data && state.data.monitoring.auto);
    send({ action: "auto_monitoring", enabled });
    if (state.data) {
      state.data.monitoring.auto = enabled;
      renderState();
    }
  });

  $("fullTextToggle").addEventListener("click", () => {
    if (!state.data || !state.data.plan || !state.data.plan.full_text) {
      return setStatus(t("fullTextBusinessOnly"));
    }
    const enabled = !Boolean(state.data && state.data.monitoring.full_text);
    send({ action: "fulltext", enabled });
    if (state.data) {
      state.data.monitoring.full_text = enabled;
      renderState();
    }
  });

  const importanceToggleCard = $("importanceToggleCard");
  if (importanceToggleCard) {
    importanceToggleCard.addEventListener("click", () => {
      if (!state.data || !state.data.features || !state.data.features.importance_rating) {
        return setStatus(t("importance_rating_unavailable"));
      }
      const enabled = !Boolean(state.data.monitoring && state.data.monitoring.importance_rating);
      send({ action: "importance_rating", enabled });
      state.data.monitoring.importance_rating = enabled;
      renderState();
    });
  }

  $("threadsToggle").addEventListener("click", () => {
    if (!state.data || !state.data.threads || !state.data.threads.available) {
      return setStatus(t("threadsUnavailable"));
    }
    state.data.threads.enabled = !Boolean(state.data.threads.enabled);
    renderThreadsSettings(state.data.threads);
  });
  $("threadsHoursRange").addEventListener("input", () => {
    $("threadsHoursValue").textContent = threadsHoursLabel(Number($("threadsHoursRange").value) || 24);
  });
  $("threadsSaveButton").addEventListener("click", () => {
    if (!state.data || !state.data.threads || !state.data.threads.available) {
      return setStatus(t("threadsUnavailable"));
    }
    const limit = Math.max(1, Math.min(100, Number($("threadsResultLimit").value) || 15));
    send({
      action: "threads_settings",
      enabled: Boolean(state.data.threads.enabled),
      hours: Number($("threadsHoursRange").value) || 24,
      media_filter: $("threadsMediaFilter").value,
      link_filter: $("threadsLinkFilter").value,
      result_limit: limit,
      search_type: $("threadsSearchType").value
    });
    setStatus(t("threadsSaved"));
    setTimeout(loadAll, 800);
  });

  $("addKeywordButton").addEventListener("click", () => {
    const value = valueOf("keywordInput");
    if (!value) return setStatus(t("typeKeyword"));
    send({ action: "add_keyword", value });
    $("keywordInput").value = "";
    setTimeout(loadAll, 800);
  });

  $("addStopButton").addEventListener("click", () => {
    const value = valueOf("stopInput");
    if (!value) return setStatus(t("typeStop"));
    send({ action: "add_stop_word", value });
    $("stopInput").value = "";
    setTimeout(loadAll, 800);
  });

  $("addPlusButton").addEventListener("click", () => {
    const value = valueOf("plusInput");
    if (!value) return setStatus(t("typePlus"));
    send({ action: "add_plus_word", value });
    $("plusInput").value = "";
    setTimeout(loadAll, 800);
  });

  $("addRssButton").addEventListener("click", () => {
    const value = valueOf("rssInput");
    if (!value) return setStatus(t("typeRss"));
    send({ action: "add_rss", value });
    $("rssInput").value = "";
    setTimeout(loadAll, 800);
  });

  $("addTgButton").addEventListener("click", () => {
    const value = valueOf("tgInput");
    if (!value) return setStatus(t("typeTg"));
    send({ action: "add_tg", value });
    $("tgInput").value = "";
    setTimeout(loadAll, 800);
  });

  start();

  async function start() {
    await waitForTelegramAuth();
    loadAll();
  }

  function activateTab(name) {
    document.querySelectorAll(".tab").forEach((button) => {
      button.classList.toggle("is-active", button.dataset.tab === name);
      if (button.dataset.tab === name) {
        button.scrollIntoView({ behavior: "smooth", block: "nearest", inline: "center" });
      }
    });
    document.querySelectorAll(".tab-panel").forEach((panel) => {
      panel.classList.toggle("is-active", panel.dataset.panel === name);
    });
    if (name === "report") {
      renderReportFilters();
    }
    window.setTimeout(updateTabsScrollCue, 180);
  }

  function updateTabsScrollCue() {
    const shell = $("tabsShell");
    const nav = $("tabsNav");
    if (!shell || !nav) return;
    const hasOverflow = nav.scrollWidth > nav.clientWidth + 4;
    const hasHiddenRight = nav.scrollLeft + nav.clientWidth < nav.scrollWidth - 8;
    shell.classList.toggle("has-more-tabs", hasOverflow && hasHiddenRight);
  }

  async function loadAll() {
    try {
      setLoaderText(t("opening"));
      if (tg && !tg.initData) {
        throw new Error("missing_telegram_init_data");
      }
      const [statePayload, recentPayload] = await Promise.all([
        apiGet("/api/state"),
        apiGet("/api/recent")
      ]);
      state.data = statePayload;
      state.recent = recentPayload.items || [];
      state.language = state.pendingLanguage || (statePayload.language && statePayload.language.code) || state.language || "en";
      rememberLanguage(state.language);
      applyTranslations();
      renderState();
      renderNewsFilters();
      renderNews();
      setStatus("");
      hideLoader();
    } catch (error) {
      console.error(error);
      renderDemo();
      setStatus(t("loadError") + " " + t("openTelegram"));
      hideLoader();
    }
  }

  async function reloadRecentForNewsFilters() {
    const requestId = ++recentRequestId;
    try {
      const params = new URLSearchParams();
      Object.entries(state.newsFilters || {}).forEach(([key, value]) => {
        if (value) params.set(key, value);
      });
      const payload = await apiGet("/api/recent" + (params.toString() ? "?" + params.toString() : ""));
      if (requestId !== recentRequestId) return;
      state.recent = payload.items || [];
      renderNews();
    } catch (error) {
      console.error(error);
      renderNews();
      setStatus(t("loadError"));
    }
  }

  function waitForTelegramAuth() {
    if (!tg || tg.initData) return Promise.resolve();
    return new Promise((resolve) => {
      const startedAt = Date.now();
      const timer = setInterval(() => {
        if (tg.initData || Date.now() - startedAt > 1800) {
          clearInterval(timer);
          resolve();
        }
      }, 100);
    });
  }

  function syncTelegramInsets() {
    if (!tg) return;
    const safeTop = Number(tg.safeAreaInset && tg.safeAreaInset.top) || 0;
    const contentTop = Number(tg.contentSafeAreaInset && tg.contentSafeAreaInset.top) || 0;
    const top = Math.max(82, safeTop, contentTop);
    document.documentElement.style.setProperty("--tg-safe-top", top + "px");
  }

  async function apiGet(path) {
    const response = await fetch(apiUrl(path), {
      headers: {
        "X-Telegram-Init-Data": tg && tg.initData || ""
      }
    });
    if (!response.ok) {
      throw new Error(path + " " + response.status);
    }
    return response.json();
  }

  async function apiBlob(path) {
    const response = await fetch(apiUrl(path), {
      headers: {
        "X-Telegram-Init-Data": tg && tg.initData || ""
      }
    });
    if (!response.ok) {
      throw new Error(path + " " + response.status);
    }
    return {
      blob: await response.blob(),
      filename: filenameFromDisposition(response.headers.get("Content-Disposition"))
    };
  }

  async function apiPost(path, payload) {
    const response = await fetch(apiUrl(path), {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "X-Telegram-Init-Data": tg && tg.initData || ""
      },
      body: JSON.stringify(payload || {})
    });
    if (!response.ok) {
      throw new Error(path + " " + response.status);
    }
    return response.json();
  }

  function configuredApiBase() {
    const params = new URLSearchParams(window.location.search);
    return normalizeApiBase(params.get("api") || window.MONITORIO_API_BASE || "");
  }

  function normalizeApiBase(value) {
    return String(value || "").trim().replace(/\/+$/, "");
  }

  function apiUrl(path) {
    return apiBase ? apiBase + path : path;
  }

  function renderState() {
    const data = state.data;
    if (!data) return;
    const languageCode = activeLanguageCode(data);
    $("profileLine").textContent = data.country.label + " - " + languageNameFor(languageCode, data);
    $("planName").textContent = data.plan.name;
    $("planMeta").textContent = data.locked ? t("locked") : t("plan") + " " + data.plan.name;
    renderTopSourceSummary(data);
    $("sentToday").textContent = data.monitoring.sent_today + "/" + data.plan.alerts_per_day;
    const sourceCountry = $("sourceOverviewCountry");
    if (sourceCountry) {
      sourceCountry.textContent = data.country && data.country.name ? "- " + data.country.name : "";
    }

    fillSelect($("languageSelect"), data.languages, languageCode);
    fillSelect($("countrySelect"), data.countries, data.country.code);

    setToggle($("autoToggle"), data.monitoring.auto);
    $("autoToggleText").textContent = data.monitoring.auto ? t("automatic") : t("manual");
    setToggle($("fullTextToggle"), data.monitoring.full_text);
    $("fullTextToggle").disabled = !data.plan.full_text;
    $("fullTextToggleText").textContent = !data.plan.full_text
      ? t("fullTextBusinessOnly")
      : (data.monitoring.full_text ? `${t("fullTextOn")}. ${t("fullTextDelayWarning")}` : t("fullTextOff"));
    renderImportanceRating(data);
    renderIntervalControl(data.monitoring);
    renderThreadsSettings(data.threads || {});
    renderSetupStatus(data);

    renderKeywords(data.monitoring.keywords || []);
    renderTermChips("stopChips", data.monitoring.stop_words || [], "remove_stop_word");
    renderTermChips("plusChips", data.monitoring.plus_words || [], "remove_plus_word");
    renderSources(data.sources);
    renderPlans(data.payments);
    renderSupportAccess(data.plan);
    renderAiDigestAvailability(data.features || {}, data.ai_digest || {});
  }

  function renderAiDigestAvailability(features, digestState) {
    const card = $("aiDigestCard");
    if (!card) return;
    const available = Boolean(features.ai_digest);
    card.hidden = !available;
    if (!available) {
      const resultBox = $("aiDigestResult");
      if (resultBox) {
        resultBox.hidden = true;
        resultBox.innerHTML = "";
      }
      return;
    }
    renderAiDigestControls();
    if (digestState && digestState.last) {
      renderAiDigest(digestState.last, { persisted: true });
    }
  }

  function renderAiDigestControls() {
    const data = state.data;
    if (!data) return;
    const countrySelect = $("aiDigestCountrySelect");
    if (countrySelect) {
      const countries = [{ code: "all", label: t("aiDigestAllCountries") }].concat(data.countries || []);
      fillSelect(countrySelect, countries, "all");
    }
    const keywordSelect = $("aiDigestKeywordSelect");
    if (keywordSelect) {
      keywordSelect.innerHTML = "";
      const allOption = document.createElement("option");
      allOption.value = "";
      allOption.textContent = t("aiDigestAllKeywords");
      keywordSelect.appendChild(allOption);
      const seen = new Set();
      (data.monitoring && data.monitoring.keywords || []).forEach((keyword) => {
        const phrase = String(keyword.phrase || "").trim();
        if (!phrase || seen.has(phrase)) return;
        seen.add(phrase);
        const option = document.createElement("option");
        option.value = phrase;
        option.textContent = phrase + (keyword.country ? " - " + keyword.country : "");
        keywordSelect.appendChild(option);
      });
    }
  }

  function renderImportanceRating(data) {
    const card = $("importanceToggleCard");
    const text = $("importanceToggleText");
    if (!card || !text) return;
    const available = Boolean(data.features && data.features.importance_rating);
    card.hidden = !available;
    if (!available) return;
    const enabled = Boolean(data.monitoring && data.monitoring.importance_rating);
    setToggle(card, enabled);
    text.textContent = enabled ? t("importanceOn") : t("importanceOff");
  }

  function renderTopSourceSummary(data) {
    const activeSources = Number(data.monitoring.active_sources || 0);
    $("activeSources").textContent = activeSources;
    $("sourcesMeta").textContent = t("sourcesInMonitoring");
    const button = $("sourceSummaryButton");
    if (button) {
      button.title = t("sourceSummaryHint");
      button.setAttribute("aria-label", activeSources + " " + t("sourcesInMonitoring") + ". " + t("sourceSummaryHint"));
    }
    renderSourceBreakdown(data.monitoring && data.monitoring.source_breakdown);
  }

  function renderSetupStatus(data) {
    const card = $("setupStatusCard");
    const title = $("setupStatusTitle");
    const text = $("setupStatusText");
    if (!card || !title || !text) return;
    const keywords = Number(data.monitoring && data.monitoring.active_keywords || 0);
    const sources = Number(data.monitoring && data.monitoring.active_sources || 0);
    const auto = Boolean(data.monitoring && data.monitoring.auto);
    let stateClass = "is-ready";
    let titleKey = "setupReadyTitle";
    let textKey = "setupReadyText";
    if (!keywords) {
      stateClass = "is-warning";
      titleKey = "setupNoKeywordsTitle";
      textKey = "setupNoKeywordsText";
    } else if (!sources) {
      stateClass = "is-warning";
      titleKey = "setupNoSourcesTitle";
      textKey = "setupNoSourcesText";
    } else if (!auto) {
      stateClass = "is-neutral";
      titleKey = "setupManualTitle";
      textKey = "setupManualText";
    }
    card.className = "setup-status-card " + stateClass;
    title.textContent = t(titleKey);
    text.textContent = t(textKey);
  }

  function renderSourceBreakdown(rows) {
    const root = $("sourceBreakdownList");
    if (!root) return;
    root.innerHTML = "";
    const normalizedRows = Array.isArray(rows) ? rows : [];
    if (!normalizedRows.length) {
      const empty = document.createElement("p");
      empty.className = "muted-line";
      empty.textContent = t("noSourceBreakdown");
      root.appendChild(empty);
      return;
    }
    normalizedRows.forEach((row) => {
      const item = document.createElement("div");
      item.className = "country-source-pill";
      const country = String(row.country || row.country_code || "").trim() || t("sourceOtherCountry");
      const count = Number(row.count || 0);
      item.innerHTML = [
        "<strong>" + escapeHtml(country) + "</strong>",
        "<small>" + escapeHtml(count + " " + t("sourceWord")) + "</small>"
      ].join("");
      root.appendChild(item);
    });
  }

  function renderIntervalControl(monitoring) {
    const range = $("intervalRange");
    const min = Number(monitoring.interval_min || 60);
    const max = Number(monitoring.interval_max || 1440);
    const value = Number(monitoring.interval_minutes || min);
    range.min = String(min);
    range.max = String(max);
    range.step = String(monitoring.interval_step || 5);
    range.value = String(Math.max(min, Math.min(max, value)));
    $("intervalValue").textContent = intervalLabel(Number(range.value));
    $("intervalHint").textContent = state.data && state.data.plan && state.data.plan.id === "business"
      ? t("intervalBusinessHint")
      : t("intervalPlanHint");
  }

  function renderThreadsSettings(threads) {
    const card = document.querySelector(".threads-card");
    if (!threadsUiEnabled) {
      if (card) {
        card.hidden = true;
      }
      return;
    }
    if (card) {
      card.hidden = false;
    }
    const available = Boolean(threads.available);
    $("threadsHint").textContent = available ? t("threadsHintBusiness") : t("threadsHintUnavailable");
    $("threadsToggle").disabled = !available;
    $("threadsSaveButton").disabled = !available;
    $("threadsToggle").textContent = threads.enabled ? t("on") : t("off");
    $("threadsToggle").classList.toggle("is-active", Boolean(threads.enabled));
    const hours = Math.max(1, Math.min(24, Number(threads.hours || 24)));
    $("threadsHoursRange").value = String(hours);
    $("threadsHoursValue").textContent = threadsHoursLabel(hours);
    $("threadsResultLimit").value = String(Math.max(1, Math.min(100, Number(threads.result_limit || 15))));
    $("threadsMediaFilter").value = threads.media_filter || "any";
    $("threadsLinkFilter").value = threads.link_filter || "any";
    $("threadsSearchType").value = threads.search_type || "RECENT";
    ["threadsHoursRange", "threadsResultLimit", "threadsMediaFilter", "threadsLinkFilter", "threadsSearchType"].forEach((id) => {
      $(id).disabled = !available;
    });
  }

  function renderNews() {
    const list = $("newsList");
    const empty = $("emptyNews");
    renderSourceTypeTabs();
    list.innerHTML = "";
    const rows = filteredRecent();
    empty.style.display = rows.length ? "none" : "block";
    if (!rows.length) {
      empty.querySelector("strong").textContent = t("noNews");
      empty.querySelector("span").textContent = t("noNewsHint");
      return;
    }
    rows.forEach((item) => {
      const card = document.createElement("article");
      card.className = "news-card";
      card.innerHTML = [
        '<div class="news-meta">',
        '<span class="badge">' + escapeHtml(item.keyword || "") + "</span>",
        '<span class="badge">' + escapeHtml(displaySourceName(item.source || "")) + "</span>",
        item.source_country ? '<span class="badge">' + escapeHtml(item.source_country) + "</span>" : "",
        '<span class="badge">' + escapeHtml(formatDate(item.sent_at || item.published_at)) + "</span>",
        importanceBadgeHtml(item.importance),
        "</div>",
        "<h3>" + escapeHtml(item.title || "") + "</h3>",
        item.summary ? "<p>" + escapeHtml(item.summary) + "</p>" : "",
        importanceDetailsHtml(item.importance),
        '<a href="' + escapeAttr(item.url || "#") + '" data-url="' + escapeAttr(item.url || "") + '">' + t("open") + "</a>"
      ].join("");
      const link = card.querySelector("a");
      link.addEventListener("click", (event) => {
        event.preventDefault();
        openLink(link.dataset.url);
      });
      list.appendChild(card);
    });
  }

  function importanceBadgeHtml(importance) {
    if (!importance) return "";
    const level = String(importance.level || "low");
    const score = Math.max(0, Math.min(100, Number(importance.score || 0)));
    return '<span class="badge importance-badge importance-' + escapeAttr(level) + '">' +
      escapeHtml(importanceLevelLabel(level) + " " + score + "/100") +
      "</span>";
  }

  function importanceDetailsHtml(importance) {
    if (!importance || !Array.isArray(importance.reasons) || !importance.reasons.length) return "";
    return '<p class="importance-reasons"><strong>' + escapeHtml(t("importanceReasons")) + ':</strong> ' +
      escapeHtml(importance.reasons.map(importanceReasonLabel).join(", ")) +
      "</p>";
  }

  function importanceLevelLabel(level) {
    if (level === "high") return t("importanceHigh");
    if (level === "medium") return t("importanceMedium");
    return t("importanceLow");
  }

  function importanceReasonLabel(reason) {
    return String(reason || "").replace(/_/g, " ");
  }

  function renderSourceTypeTabs() {
    document.querySelectorAll(".source-type-tab").forEach((button) => {
      button.classList.toggle("is-active", (button.dataset.sourceType || "") === (state.newsFilters.source_type || ""));
    });
  }

  function renderNewsFilters() {
    const rows = visibleRecentRows(state.recent);
    fillFilterSelect(
      $("newsCountryFilter"),
      t("allCountries"),
      uniqueOptions(rows, (item) => ({
        value: String(item.source_country_code || item.source_country || ""),
        label: item.source_country || item.source_country_code || ""
      })),
      state.newsFilters.country
    );
    fillFilterSelect(
      $("newsKeywordFilter"),
      t("allKeywords"),
      userKeywordOptions(),
      state.newsFilters.keyword
    );
    fillFilterSelect(
      $("newsSourceFilter"),
      t("allSources"),
      uniqueOptions(rows, (item) => ({ value: item.source || "", label: displaySourceName(item.source || "") })),
      state.newsFilters.source
    );
    $("newsDateFilter").value = state.newsFilters.date || "";
  }

  function renderReportFilters() {
    const rows = visibleRecentRows(state.recent);
    fillReportFilterSelect(
      $("reportCountryFilter"),
      t("allCountries"),
      uniqueOptions(rows, (item) => ({
        value: String(item.source_country_code || item.source_country || ""),
        label: item.source_country || item.source_country_code || ""
      })),
      state.reportFilters.country
    );
    fillReportFilterSelect(
      $("reportKeywordFilter"),
      t("allKeywords"),
      userKeywordOptions(),
      state.reportFilters.keyword
    );
    fillReportFilterSelect(
      $("reportSourceFilter"),
      t("allSources"),
      uniqueOptions(rows, (item) => ({ value: item.source || "", label: displaySourceName(item.source || "") })),
      state.reportFilters.source
    );
    fillReportFilterSelect(
      $("reportSourceTypeFilter"),
      t("sourceTypeAll"),
      [
        { value: "rss", label: t("sourceTypeRss") },
        { value: "telegram", label: t("sourceTypeTelegram") },
        { value: "prozorro", label: t("sourceTypeRegistry") }
      ],
      state.reportFilters.source_type
    );
  }

  function uniqueOptions(rows, mapper) {
    const seen = new Set();
    return rows
      .map(mapper)
      .filter((item) => {
        if (!item.value || seen.has(item.value)) return false;
        seen.add(item.value);
        return true;
      })
      .sort((a, b) => String(a.label).localeCompare(String(b.label), state.language || undefined));
  }

  function fillFilterSelect(select, allLabel, options, selected) {
    select.innerHTML = "";
    const all = document.createElement("option");
    all.value = "";
    all.textContent = allLabel;
    select.appendChild(all);
    options.forEach((item) => {
      const option = document.createElement("option");
      option.value = item.value;
      option.textContent = item.label;
      select.appendChild(option);
    });
    select.value = options.some((item) => item.value === selected) ? selected : "";
    state.newsFilters[filterKeyFromSelect(select.id)] = select.value;
  }

  function fillReportFilterSelect(select, allLabel, options, selected) {
    if (!select) return;
    select.innerHTML = "";
    const all = document.createElement("option");
    all.value = "";
    all.textContent = allLabel;
    select.appendChild(all);
    options.forEach((item) => {
      const option = document.createElement("option");
      option.value = item.value;
      option.textContent = item.label;
      select.appendChild(option);
    });
    select.value = options.some((item) => item.value === selected) ? selected : "";
    state.reportFilters[reportFilterKeyFromSelect(select.id)] = select.value;
  }

  function userKeywordOptions() {
    const rows = state.data && state.data.monitoring && state.data.monitoring.keywords || [];
    return uniqueOptions(rows, (item) => ({
      value: item.phrase || "",
      label: item.country ? item.phrase + " - " + item.country : item.phrase || ""
    }));
  }

  function filterKeyFromSelect(id) {
    return {
      newsCountryFilter: "country",
      newsKeywordFilter: "keyword",
      newsSourceFilter: "source"
    }[id] || "";
  }

  function reportFilterKeyFromSelect(id) {
    return {
      reportCountryFilter: "country",
      reportKeywordFilter: "keyword",
      reportSourceFilter: "source",
      reportSourceTypeFilter: "source_type"
    }[id] || "";
  }

  function sortedRecent() {
    const rows = visibleRecentRows(state.recent);
    const collator = new Intl.Collator(state.language || undefined, { sensitivity: "base" });
    const text = (value) => String(value || "");
    if (state.newsSort === "country") {
      return rows.sort((a, b) => collator.compare(text(a.source_country), text(b.source_country)) || compareDatesDesc(a, b));
    }
    if (state.newsSort === "keyword") {
      return rows.sort((a, b) => collator.compare(text(a.keyword), text(b.keyword)) || compareDatesDesc(a, b));
    }
    if (state.newsSort === "source") {
      return rows.sort((a, b) => collator.compare(text(a.source), text(b.source)) || compareDatesDesc(a, b));
    }
    return rows.sort(compareDatesDesc);
  }

  function filteredRecent() {
    const filters = state.newsFilters || {};
    const now = Date.now();
    return sortedRecent().filter((item) => {
      if (filters.country && String(item.source_country_code || item.source_country || "") !== filters.country) return false;
      if (filters.keyword && String(item.keyword || "") !== filters.keyword) return false;
      if (filters.source && String(item.source || "") !== filters.source) return false;
      if (filters.source_type && sourceTypeOf(item) !== filters.source_type) return false;
      if (filters.date) {
        const age = now - dateValue(item.sent_at || item.published_at);
        if (filters.date === "day" && age > 24 * 60 * 60 * 1000) return false;
        if (filters.date === "week" && age > 7 * 24 * 60 * 60 * 1000) return false;
      }
      return true;
    });
  }

  function visibleRecentRows(rows) {
    return [...rows].filter((item) => !hiddenMentionSourceTypes.has(sourceTypeOf(item)));
  }

  function sourceTypeOf(item) {
    const explicit = normalizeSourceType(item.source_type || "");
    if (explicit) return explicit;
    const source = String(item.source || "").toLowerCase();
    const url = String(item.url || "").toLowerCase();
    if (source.startsWith("threads") || url.includes("threads.net")) return "threads";
    if (source.startsWith("reddit") || url.includes("reddit.com/")) return "reddit";
    if (url.includes("t.me/") || source.includes("telegram")) return "telegram";
    return "rss";
  }

  function compareDatesDesc(a, b) {
    return dateValue(b.sent_at || b.published_at) - dateValue(a.sent_at || a.published_at);
  }

  function dateValue(value) {
    const time = new Date(value || 0).getTime();
    return Number.isFinite(time) ? time : 0;
  }

  function renderKeywords(values) {
    const root = $("keywordChips");
    root.innerHTML = "";
    values.forEach((item) => {
      root.appendChild(keywordChip(item));
    });
  }

  function keywordChip(item) {
    const chipItem = document.createElement("span");
    chipItem.className = "chip keyword-chip";
    if (item.paused) chipItem.classList.add("is-paused");
    if (item.silent) chipItem.classList.add("is-silent");

    const label = document.createElement("span");
    label.className = "keyword-chip-label";
    label.textContent = item.phrase + " - " + item.country;
    chipItem.appendChild(label);

    const pauseButton = document.createElement("button");
    pauseButton.type = "button";
    pauseButton.className = "keyword-chip-action icon";
    const pauseLabel = item.paused ? t("keywordResume") : t("keywordPause");
    pauseButton.textContent = item.paused ? "\u25B6" : "\u2161";
    pauseButton.title = pauseLabel;
    pauseButton.setAttribute("aria-label", pauseLabel);
    pauseButton.addEventListener("click", () => {
      send({
        action: "keyword_pause",
        value: item.phrase,
        country_code: item.country_code,
        enabled: !item.paused
      });
      setTimeout(loadAll, 800);
    });
    chipItem.appendChild(pauseButton);

    const silentButton = document.createElement("button");
    silentButton.type = "button";
    silentButton.className = "keyword-chip-action icon";
    silentButton.textContent = item.silent ? t("keywordSilentOn") : t("keywordSilentOff");
    silentButton.title = t("keywordSilentHint");
    silentButton.setAttribute("aria-label", t("keywordSilentHint"));
    silentButton.addEventListener("click", () => {
      send({
        action: "keyword_silent",
        value: item.phrase,
        country_code: item.country_code,
        enabled: !item.silent
      });
      setTimeout(loadAll, 800);
    });
    chipItem.appendChild(silentButton);

    const removeButton = document.createElement("button");
    removeButton.type = "button";
    removeButton.className = "keyword-chip-remove";
    removeButton.textContent = "\uD83D\uDDD1\uFE0F";
    removeButton.setAttribute("aria-label", t("remove"));
    removeButton.addEventListener("click", () => {
      send({ action: "remove_keyword", value: item.phrase, country_code: item.country_code });
      setTimeout(loadAll, 800);
    });
    chipItem.appendChild(removeButton);
    return chipItem;
  }

  function renderTermChips(id, values, action) {
    const root = $(id);
    root.innerHTML = "";
    values.forEach((value) => {
      root.appendChild(chip(value, () => {
        send({ action, value });
        setTimeout(loadAll, 800);
      }));
    });
  }

  function renderSources(sources) {
    if (!sources) return;
    $("standardSources").textContent = sources.standard.active + "/" + sources.standard.total;
    const registryCounter = $("registrySources");
    if (registryCounter) {
      const registry = sources.registry || { active: 0, total: 0 };
      registryCounter.textContent = registry.active + "/" + registry.total;
    }
    $("paidSources").textContent = sources.paid_telegram.active + "/" + sources.paid_telegram.total;
    $("customSources").textContent = sources.custom.active + "/" + sources.custom.total;
    renderSourceOverview(sources);
  }

  function renderPlans(payments) {
    const root = $("plansGrid");
    if (!root) return;
    root.innerHTML = "";
    const plans = payments && payments.plans || [];
    renderCryptoStatus(root, payments && payments.crypto_status);
    renderFreePlanTerms(root);
    if (!plans.length) {
      const empty = document.createElement("div");
      empty.className = "empty-state";
      empty.style.display = "block";
      empty.innerHTML = "<strong>" + escapeHtml(t("plansTitle")) + "</strong><span>-</span>";
      root.appendChild(empty);
      return;
    }
    plans.forEach((plan) => {
      const card = document.createElement("article");
      card.className = "plan-card" + (state.data && state.data.plan && state.data.plan.id === plan.id ? " is-current" : "");
      const cryptoAvailable = Boolean(plan.crypto_amount);
      card.innerHTML = [
        "<header>",
        "<h3>" + escapeHtml(plan.name) + "</h3>",
        state.data && state.data.plan && state.data.plan.id === plan.id
          ? '<small class="badge">' + escapeHtml(t("currentPlan")) + "</small>"
          : '<small>' + escapeHtml(formatTemplate(t("validDays"), { days: plan.days })) + "</small>",
        "</header>",
        '<div class="plan-price-row">',
        '<div class="plan-price"><span>Telegram Stars</span><strong>' + escapeHtml(plan.stars) + " ⭐</strong></div>",
        '<div class="plan-price"><span>USDT</span><strong>' + (cryptoAvailable ? escapeHtml(plan.crypto_amount + " " + (payments.currency || "USD")) : escapeHtml(t("noCrypto"))) + "</strong></div>",
        "</div>",
        "<p>" + escapeHtml(plan.description || "") + "</p>",
        '<div class="plan-actions">',
        '<button class="primary-button" type="button" data-method="stars">' + escapeHtml(t("starsPay")) + "</button>",
        '<button class="secondary-button" type="button" data-method="crypto"' + (cryptoAvailable ? "" : " disabled") + ">" + escapeHtml(t("cryptoPay")) + "</button>",
        "</div>"
      ].join("");
      card.querySelectorAll("button[data-method]").forEach((button) => {
        button.addEventListener("click", () => startCheckout(plan.id, button.dataset.method));
      });
      root.appendChild(card);
    });
  }

  function renderFreePlanTerms(root) {
    const card = document.createElement("article");
    card.className = "free-plan-terms";
    card.innerHTML = [
      "<strong>" + escapeHtml(t("freePlanTermsTitle")) + "</strong>",
      "<p>" + escapeHtml(t("freePlanTermsText")) + "</p>"
    ].join("");
    root.appendChild(card);
  }

  function renderSupportAccess(plan) {
    const link = $("supportLink");
    if (!link) return;
    const paid = Boolean(plan && plan.id && plan.id !== "free");
    const card = link.closest(".help-card");
    const text = card && card.querySelector("p");
    if (text) text.textContent = paid ? t("helpSupportText") : t("helpSupportPaidOnly");
    link.style.display = paid ? "inline-flex" : "none";
  }

  function renderCryptoStatus(root, status) {
    if (!status) return;
    const card = document.createElement("article");
    card.className = "crypto-status-card";
    const normalized = String(status.status || "").toLowerCase();
    const paid = Boolean(status.paid_at) || ["confirmed", "finished"].includes(normalized);
    const failed = ["failed", "expired", "refunded"].includes(normalized);
    const confirming = ["confirming", "confirmed", "sending"].includes(normalized);
    const label = paid
      ? t("cryptoStatusPaid")
      : failed
        ? t("cryptoStatusFailed")
        : confirming
          ? t("cryptoStatusConfirming")
          : normalized
            ? t("cryptoStatusWaiting")
            : t("cryptoStatusUnknown");
    card.innerHTML = [
      "<div>",
      "<strong>" + escapeHtml(t("cryptoStatusTitle")) + "</strong>",
      "<p>" + escapeHtml(label) + " · " + escapeHtml(status.amount || "") + " " + escapeHtml(status.currency || "") + "</p>",
      "</div>",
      status.invoice_url && !paid && !failed
        ? '<button class="compact-button" type="button">' + escapeHtml(t("cryptoOpenInvoice")) + "</button>"
        : ""
    ].join("");
    const button = card.querySelector("button");
    if (button) {
      button.addEventListener("click", () => openLink(status.invoice_url));
    }
    root.appendChild(card);
  }

  function renderSourceOverview(sources) {
    const root = $("sourceList");
    root.innerHTML = "";
    renderStandardSourcesToggle(sources);
    if (state.data && state.data.plan && state.data.plan.id === "free") {
      const note = document.createElement("p");
      note.className = "source-free-note";
      note.textContent = t("sourcesFreeNote");
      root.appendChild(note);
    }
    const query = (state.sourceQuery || "").trim().toLowerCase();
    const PAGE_SIZE = 20;
    const groups = [
      ["RSS", sources.standard_items || [], false],
      [t("sourceGroupRegistries"), sources.registry_items || [], false],
      ["TG", sources.paid_telegram_items || [], false],
      ["Custom", sources.custom_items || [], true]
    ];
    let anyShown = false;
    groups.forEach(([title, items, isCustom]) => {
      const matched = query
        ? items.filter((item) => ((item.name || "") + " " + (item.url || "") + " " + (item.country || "")).toLowerCase().includes(query))
        : items;
      if (!matched.length) return;
      anyShown = true;
      const pages = Math.max(1, Math.ceil(matched.length / PAGE_SIZE));
      let page = state.sourcePage[title] || 0;
      if (page > pages - 1) page = pages - 1;
      state.sourcePage[title] = page;
      const shown = matched.slice(page * PAGE_SIZE, page * PAGE_SIZE + PAGE_SIZE);
      const section = document.createElement("section");
      section.className = "source-section";
      const heading = document.createElement("h3");
      heading.textContent = title + " (" + matched.length + ")";
      section.appendChild(heading);
      shown.forEach((item) => {
        const row = document.createElement("div");
        row.className = "source-row";
        row.innerHTML = [
          "<span>",
          "<strong>" + escapeHtml(displaySourceTitle(item)) + "</strong>",
          "<small>" + escapeHtml(sourceMeta(item)) + "</small>",
          "</span>",
          '<div class="source-actions">',
          '<b class="' + (item.active ? "dot is-active" : "dot") + '"></b>',
          '<button class="compact-button" type="button" data-action="toggle">' + escapeHtml(item.active ? t("off") : t("on")) + "</button>",
          isCustom ? '<button class="compact-button danger-button" type="button" data-action="remove">' + escapeHtml(t("remove")) + "</button>" : "",
          "</div>"
        ].join("");
        const toggleButton = row.querySelector('button[data-action="toggle"]');
        toggleButton.addEventListener("click", () => {
          send({ action: "source_toggle", url: item.url, enabled: !item.active });
          setTimeout(loadAll, 800);
        });
        const removeButton = row.querySelector('button[data-action="remove"]');
        if (removeButton) {
          removeButton.addEventListener("click", () => {
            send({ action: "remove_source", url: item.url });
            setTimeout(loadAll, 800);
          });
        }
        section.appendChild(row);
      });
      if (pages > 1) {
        const pager = document.createElement("div");
        pager.className = "source-pager";
        const prev = document.createElement("button");
        prev.type = "button";
        prev.className = "compact-button";
        prev.textContent = "‹";
        prev.disabled = page <= 0;
        prev.addEventListener("click", () => {
          state.sourcePage[title] = page - 1;
          renderSourceOverview(state.data.sources);
        });
        const info = document.createElement("span");
        info.className = "source-pager-info";
        info.textContent = (page + 1) + " / " + pages;
        const next = document.createElement("button");
        next.type = "button";
        next.className = "compact-button";
        next.textContent = "›";
        next.disabled = page >= pages - 1;
        next.addEventListener("click", () => {
          state.sourcePage[title] = page + 1;
          renderSourceOverview(state.data.sources);
        });
        pager.append(prev, info, next);
        section.appendChild(pager);
      }
      root.appendChild(section);
    });
    if (!anyShown) {
      const empty = document.createElement("p");
      empty.className = "muted-line";
      empty.textContent = query ? t("sourcesNoMatch") : "-";
      root.appendChild(empty);
    }
  }

  function standardSourceSummary(sources) {
    if (!sources) return { active: 0, total: 0 };
    const items = [
      ...(sources.standard_items || []),
      ...(sources.registry_items || []),
      ...(sources.paid_telegram_items || [])
    ];
    return {
      active: items.filter((item) => item && item.active).length,
      total: items.length
    };
  }

  function renderStandardSourcesToggle(sources) {
    const button = $("standardSourcesToggleButton");
    if (!button) return;
    const summary = standardSourceSummary(sources);
    button.hidden = summary.total === 0;
    button.disabled = summary.total === 0;
    button.textContent = summary.active > 0 ? t("standardSourcesOff") : t("standardSourcesOn");
    button.classList.toggle("danger-button", summary.active > 0);
  }

  function renderDemo() {
    applyTranslations();
    $("profileLine").textContent = "Monitorio";
    $("planName").textContent = "-";
    $("planMeta").textContent = "Telegram";
    $("activeSources").textContent = "-";
    $("sourcesMeta").textContent = t("sourcesInMonitoring");
    const sourceSummaryButton = $("sourceSummaryButton");
    const sourceBreakdownPanel = $("sourceBreakdownPanel");
    if (sourceSummaryButton) {
      sourceSummaryButton.title = t("sourceSummaryHint");
      sourceSummaryButton.setAttribute("aria-expanded", "false");
    }
    if (sourceBreakdownPanel) sourceBreakdownPanel.hidden = true;
    renderSourceBreakdown(null);
    renderSetupStatus({
      monitoring: {
        keywords: [],
        active_sources: 0,
        auto: false
      }
    });
    $("sentToday").textContent = "-";
    const sourceCountry = $("sourceOverviewCountry");
    if (sourceCountry) sourceCountry.textContent = "";
    $("newsList").innerHTML = "";
    $("emptyNews").style.display = "block";
    $("emptyNews").querySelector("strong").textContent = t("noNews");
    $("emptyNews").querySelector("span").textContent = t("openTelegram");
    renderSupportAccess({ id: "free" });
  }

  function fillSelect(select, rows, selected) {
    select.innerHTML = "";
    rows.forEach((row) => {
      const option = document.createElement("option");
      option.value = row.code;
      option.textContent = row.label || row.name || row.code;
      option.selected = row.code === selected;
      select.appendChild(option);
    });
  }

  function chip(text, onRemove) {
    const item = document.createElement("span");
    item.className = "chip";
    item.innerHTML = '<span></span><button type="button"></button>';
    item.querySelector("span").textContent = text;
    const button = item.querySelector("button");
    button.textContent = "x";
    button.setAttribute("aria-label", t("remove"));
    button.addEventListener("click", onRemove);
    return item;
  }

  function setToggle(element, enabled) {
    element.classList.toggle("is-on", Boolean(enabled));
  }

  async function send(payload) {
    if (tg && tg.initData) {
      try {
        const result = await apiPost("/api/action", payload);
        if (result.state) {
          state.data = result.state;
          if (payload.action === "set_language") {
            const serverLanguage = result.state.language && result.state.language.code;
            state.language = payload.language || serverLanguage || state.language;
            if (!serverLanguage || serverLanguage === state.language) {
              state.pendingLanguage = "";
            }
            applyTranslations();
          }
          renderState();
        }
        setStatus(result.ok === false ? (result.error || t("loadError")) : t("sent"));
        return;
      } catch (error) {
        console.error(error);
      }
    }
    sendToChat(payload);
  }

  async function startCheckout(planId, method) {
    if (!tg || !tg.initData) {
      setStatus(t("openTelegram"));
      return;
    }
    try {
      setStatus(t("paymentOpening"));
      const result = await apiPost("/api/checkout", { plan_id: planId, method });
      if (!result.ok || !result.url) {
        setStatus(t(result.error || "checkoutError"));
        return;
      }
      if (result.open_with === "invoice" && tg && typeof tg.openInvoice === "function") {
        tg.openInvoice(result.url, (status) => {
          if (status === "paid") {
            setStatus(t("paymentPaid"));
            setTimeout(loadAll, 1200);
          } else {
            setStatus(t("paymentPending"));
            setTimeout(loadAll, 1200);
          }
        });
      } else {
        openLink(result.url);
        setStatus(t("paymentPending"));
        setTimeout(loadAll, 1500);
      }
    } catch (error) {
      console.error(error);
      setStatus(t("checkoutError"));
    }
  }

  async function downloadReport(format) {
    if (!tg || !tg.initData) {
      setStatus(t("openTelegram"));
      return;
    }
    const safeFormat = ["csv", "xlsx", "pdf"].includes(format) ? format : "csv";
    const days = $("reportPeriodSelect").value === "7" ? "7" : "1";
    try {
      setStatus(t("reportPreparing"));
      const params = new URLSearchParams({ days });
      const filters = currentReportFilters();
      Object.keys(filters).forEach((key) => {
        if (filters[key]) params.set(key, filters[key]);
      });
      const result = await apiBlob("/api/report." + safeFormat + "?" + params.toString());
      const filename = result.filename || ("monitorio-report-" + days + "d." + safeFormat);
      const shared = await shareReportFile(result.blob, filename, safeFormat);
      if (shared) {
        setStatus(formatTemplate(t("reportShared"), { format: safeFormat.toUpperCase() }));
      } else {
        downloadBlob(result.blob, filename);
        setStatus(formatTemplate(t("reportDownloaded"), { format: safeFormat.toUpperCase() }));
      }
    } catch (error) {
      console.error(error);
      setStatus(t("loadError"));
    }
  }

  function currentReportFilters() {
    return {
      country: $("reportCountryFilter") ? $("reportCountryFilter").value : "",
      keyword: $("reportKeywordFilter") ? $("reportKeywordFilter").value : "",
      source: $("reportSourceFilter") ? $("reportSourceFilter").value : "",
      source_type: $("reportSourceTypeFilter") ? $("reportSourceTypeFilter").value : ""
    };
  }

  async function generateAiDigest() {
    if (!tg || !tg.initData) {
      setStatus(t("openTelegram"));
      return;
    }
    const resultBox = $("aiDigestResult");
    if (resultBox) {
      resultBox.hidden = true;
      resultBox.innerHTML = "";
    }
    const period = $("aiDigestPeriodSelect").value || "24";
    const payload = {
      period,
      country: $("aiDigestCountrySelect") ? $("aiDigestCountrySelect").value : "all",
      keyword: $("aiDigestKeywordSelect") ? $("aiDigestKeywordSelect").value : "",
      source_type: $("aiDigestSourceTypeSelect") ? $("aiDigestSourceTypeSelect").value : "",
      focus: $("aiDigestFocusSelect") ? $("aiDigestFocusSelect").value : "overview",
      max_mentions: $("aiDigestMaxMentionsSelect") ? Number($("aiDigestMaxMentionsSelect").value) || 80 : 80
    };
    try {
      setStatus(t("aiDigestPreparing"));
      const result = await apiPost("/api/digest", payload);
      if (!result.ok) {
        setStatus(t(result.error || "ai_digest_failed"));
        return;
      }
      if (state.data) {
        state.data.ai_digest = { last: result.digest || {} };
      }
      renderAiDigest(result.digest || {});
      setStatus(t("aiDigestReady"));
    } catch (error) {
      console.error(error);
      setStatus(t("ai_digest_failed"));
    }
  }

  function renderAiDigest(digest, options) {
    const root = $("aiDigestResult");
    if (!root) return;
    root.innerHTML = "";
    root.hidden = false;
    appendDigestMeta(root, digest, options || {});
    const total = Number(digest.mentions_total || 0);
    if (!total) {
      const empty = document.createElement("p");
      empty.textContent = t("aiDigestEmpty");
      root.appendChild(empty);
      return;
    }
    appendDigestSection(root, t("aiDigestSummary"), digest.summary ? [digest.summary] : []);
    appendDigestSection(root, t("aiDigestTopics"), digest.key_topics || []);
    appendImportantMentions(root, digest.important_mentions || []);
    appendDigestSection(root, t("aiDigestRisks"), digest.risks || []);
    appendTopSources(root, digest.top_sources || []);
    appendDigestSection(root, t("aiDigestSteps"), digest.next_steps || []);
  }

  function appendDigestMeta(root, digest, options) {
    const params = digest && digest.params || {};
    const values = [];
    if (digest && digest.created_at) {
      values.push(t("aiDigestCreatedAt") + ": " + formatDate(digest.created_at));
    }
    if (options.persisted) {
      values.unshift(t("aiDigestLast"));
    }
    const filters = [
      params.period_label || digest.period || "",
      digestCountryLabel(params.country),
      params.keyword || t("aiDigestAllKeywords"),
      digestSourceTypeLabel(params.source_type),
      digestFocusLabel(params.focus),
      params.max_mentions ? String(params.max_mentions) : ""
    ].filter(Boolean);
    if (filters.length) {
      values.push(t("aiDigestFilters") + ": " + filters.join(" / "));
    }
    if (!values.length) return;
    const meta = document.createElement("div");
    meta.className = "ai-digest-meta";
    values.forEach((value) => {
      const item = document.createElement("span");
      item.textContent = value;
      meta.appendChild(item);
    });
    root.appendChild(meta);
  }

  function digestCountryLabel(code) {
    const value = String(code || "").trim();
    if (!value || value === "all") return t("aiDigestAllCountries");
    const match = state.data && (state.data.countries || []).find((country) => country.code === value);
    return match ? (match.name || match.label || value) : value.toUpperCase();
  }

  function digestSourceTypeLabel(value) {
    if (value === "rss") return t("aiDigestRssOnly");
    if (value === "telegram") return t("aiDigestTelegramOnly");
    if (value === "prozorro") return t("aiDigestRegistryOnly");
    return t("aiDigestAllSources");
  }

  function digestFocusLabel(value) {
    if (value === "important") return t("aiDigestFocusImportant");
    if (value === "risks") return t("aiDigestFocusRisks");
    if (value === "sources") return t("aiDigestFocusSources");
    if (value === "actions") return t("aiDigestFocusActions");
    return t("aiDigestFocusOverview");
  }

  function appendDigestSection(root, title, items) {
    const values = (Array.isArray(items) ? items : []).map((item) => String(item || "").trim()).filter(Boolean);
    if (!values.length) return;
    const heading = document.createElement("h3");
    heading.textContent = title;
    root.appendChild(heading);
    if (values.length === 1) {
      const paragraph = document.createElement("p");
      paragraph.textContent = values[0];
      root.appendChild(paragraph);
      return;
    }
    const list = document.createElement("ul");
    values.forEach((value) => {
      const item = document.createElement("li");
      item.textContent = value;
      list.appendChild(item);
    });
    root.appendChild(list);
  }

  function appendImportantMentions(root, mentions) {
    const values = Array.isArray(mentions) ? mentions.filter(Boolean) : [];
    if (!values.length) return;
    const heading = document.createElement("h3");
    heading.textContent = t("aiDigestImportant");
    root.appendChild(heading);
    const list = document.createElement("ul");
    values.forEach((mention) => {
      const item = document.createElement("li");
      const title = String(mention.title || "").trim();
      const source = String(mention.source || "").trim();
      const why = String(mention.why_important || "").trim();
      const url = String(mention.url || "").trim();
      const text = [title, source ? "(" + source + ")" : "", why ? "- " + why : ""].filter(Boolean).join(" ");
      if (url) {
        const link = document.createElement("a");
        link.href = url;
        link.target = "_blank";
        link.rel = "noopener";
        link.textContent = text || url;
        item.appendChild(link);
      } else {
        item.textContent = text;
      }
      list.appendChild(item);
    });
    root.appendChild(list);
  }

  function appendTopSources(root, sources) {
    const values = Array.isArray(sources) ? sources.filter((item) => item && item.source) : [];
    if (!values.length) return;
    const heading = document.createElement("h3");
    heading.textContent = t("aiDigestSources");
    root.appendChild(heading);
    const list = document.createElement("ul");
    values.forEach((source) => {
      const item = document.createElement("li");
      item.textContent = String(source.source || "") + (source.count ? " - " + source.count : "");
      list.appendChild(item);
    });
    root.appendChild(list);
  }

  async function shareReportFile(blob, filename, format) {
    if (!window.File || !navigator.share || !navigator.canShare) return false;
    const file = new File([blob], filename, { type: reportMimeType(format, blob.type) });
    const payload = {
      title: filename,
      text: "Monitorio report",
      files: [file]
    };
    if (!navigator.canShare(payload)) return false;
    try {
      await navigator.share(payload);
      return true;
    } catch (error) {
      if (error && error.name === "AbortError") return true;
      console.warn("Report share failed", error);
      return false;
    }
  }

  function downloadBlob(blob, filename) {
    const url = URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.href = url;
    link.download = filename;
    document.body.appendChild(link);
    link.click();
    link.remove();
    setTimeout(() => URL.revokeObjectURL(url), 1500);
  }

  function reportMimeType(format, fallback) {
    if (format === "csv") return "text/csv";
    if (format === "xlsx") return "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet";
    if (format === "pdf") return "application/pdf";
    return fallback || "application/octet-stream";
  }

  function sendToChat(payload) {
    if (!tg || !tg.sendData) {
      setStatus(t("openTelegram"));
      return;
    }
    tg.sendData(JSON.stringify(payload));
    setStatus(t("sent"));
  }

  function valueOf(id) {
    return $(id).value.trim();
  }

  function setStatus(text) {
    statusText.textContent = text || "";
  }

  function setLoaderText(text) {
    const loaderText = $("appLoaderText");
    if (loaderText && text) {
      loaderText.textContent = text;
    }
  }

  function hideLoader() {
    if (loaderHidden) return;
    loaderHidden = true;
    const loader = $("appLoader");
    if (!loader) return;
    loader.classList.add("is-hidden");
    window.setTimeout(() => {
      if (loader.parentNode) {
        loader.parentNode.removeChild(loader);
      }
    }, 320);
  }

  function formatTemplate(template, values) {
    return String(template || "").replace(/\{(\w+)\}/g, (_, key) => values[key] == null ? "" : String(values[key]));
  }

  function filenameFromDisposition(value) {
    const match = String(value || "").match(/filename="([^"]+)"/i);
    return match ? match[1] : "";
  }

  function intervalLabel(minutes) {
    const safeMinutes = Number(minutes) || 0;
    if (safeMinutes >= 1440) return "24 h";
    if (safeMinutes >= 60 && safeMinutes % 60 === 0) return (safeMinutes / 60) + " h";
    return safeMinutes + " min";
  }

  function threadsHoursLabel(hours) {
    const safeHours = Math.max(1, Math.min(24, Number(hours) || 24));
    return safeHours + " h";
  }

  function sourceMeta(item) {
    const parts = [];
    if (item.country) parts.push(item.country);
    if (item.rank) parts.push("#" + item.rank);
    if (item.subscribers) parts.push(formatNumber(item.subscribers));
    if (item.type) parts.push(displaySourceType(item.type));
    return parts.join(" - ") || item.url || "";
  }

  function displaySourceTitle(item) {
    const name = displaySourceName(item && (item.name || item.url) || "");
    if ((name.toLowerCase() === "t.me" || name.toLowerCase() === "telegram.me") && item && item.url) {
      const username = telegramUsernameFromUrl(item.url);
      if (username) return "Telegram @" + username;
    }
    return name;
  }

  function displaySourceType(value) {
    const type = String(value || "");
    if (type === "telegram_paid") return "telegram";
    if (["registry", "prozorro", "prozorro_plan", "prozorro_sale", "rada_bills"].includes(type)) return t("sourceTypeRegistry");
    return type;
  }

  function normalizeSourceType(value) {
    const type = String(value || "").toLowerCase();
    if (type === "telegram_paid") return "telegram";
    if (["registry", "prozorro", "prozorro_plan", "prozorro_sale", "rada_bills"].includes(type)) return "prozorro";
    if (["rss", "telegram", "threads", "reddit"].includes(type)) return type;
    return "";
  }

  function displaySourceName(value) {
    const cleaned = String(value || "").replace(/\s+via\s+Google\s+News\s*$/i, "").trim();
    const username = telegramUsernameFromUrl(cleaned);
    if (username) return "Telegram @" + username;
    return cleaned || String(value || "");
  }

  function telegramUsernameFromUrl(value) {
    try {
      const parsed = new URL(String(value || ""), window.location.href);
      const host = parsed.hostname.replace(/^www\./, "");
      if (host !== "t.me" && host !== "telegram.me") return "";
      const parts = parsed.pathname.split("/").filter(Boolean);
      if (!parts.length) return "";
      if (parts[0] === "s" && parts[1]) return parts[1];
      return parts[0];
    } catch {
      return "";
    }
  }

  function formatNumber(value) {
    const number = Number(value);
    if (!Number.isFinite(number)) return "";
    return number.toLocaleString();
  }

  function applyTranslations() {
    document.documentElement.lang = state.language;
    document.querySelectorAll("[data-i18n]").forEach((node) => {
      node.textContent = t(node.dataset.i18n);
    });
    document.querySelectorAll("[data-i18n-placeholder]").forEach((node) => {
      node.setAttribute("placeholder", t(node.dataset.i18nPlaceholder));
    });
  }

  function activeLanguageCode(data) {
    const languages = data.languages || [];
    const preferred = state.pendingLanguage || state.language || (data.language && data.language.code) || "en";
    if (languages.some((row) => row.code === preferred)) return preferred;
    return data.language && data.language.code || "en";
  }

  function languageNameFor(code, data) {
    const row = (data.languages || []).find((item) => item.code === code);
    return row && (row.label || row.name) || code;
  }

  function t(key) {
    const lang = labels[state.language] || labels.en;
    return lang[key] || labels.en[key] || key;
  }

  function openLink(url) {
    if (!url) return;
    if (tg && tg.openLink) {
      tg.openLink(url);
    } else {
      window.open(url, "_blank", "noopener");
    }
  }

  function formatDate(value) {
    if (!value) return "";
    const date = new Date(value);
    if (Number.isNaN(date.getTime())) return value;
    return date.toLocaleString();
  }

  function escapeHtml(value) {
    return String(value || "")
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;");
  }

  function escapeAttr(value) {
    return escapeHtml(value).replace(/'/g, "&#39;");
  }
})();
