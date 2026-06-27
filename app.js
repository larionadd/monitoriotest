(function () {
  const tg = window.Telegram && window.Telegram.WebApp;
  const apiBase = configuredApiBase();
  const state = {
    data: null,
    recent: [],
    language: "en",
    pendingLanguage: ""
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
      fullTextOff: "Fast title and RSS-summary search",
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
      fullTextOff: "Швидкий пошук за заголовком і RSS-анонсом",
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
      fullTextOff: "Быстрый поиск по заголовку и RSS-анонсу",
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
      paymentMethods: "Payment options"
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
      paymentMethods: "Варіанти оплати"
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
      paymentMethods: "Варианты оплаты"
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
      paymentMethods: "Opcje płatności"
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
      paymentMethods: "Zahlungsoptionen"
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
      paymentMethods: "Opciones de pago"
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
      paymentMethods: "Opzioni di pagamento"
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
      paymentMethods: "Варыянты аплаты"
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
      helpSourcesText: "In Sources you can add RSS or Telegram channels, manage TG packages, and request a CSV source file."
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
      helpSourcesText: "У Джерелах можна додавати RSS або Telegram-канали, керувати TG-пакетами і замовити CSV-файл джерел."
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
      helpSourcesText: "В Источниках можно добавлять RSS или Telegram-каналы, управлять TG-пакетами и запросить CSV-файл источников."
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
      helpSourcesText: "W Źródłach możesz dodawać RSS lub kanały Telegram, zarządzać pakietami TG i poprosić o plik CSV źródeł."
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
      helpSourcesText: "In Quellen können Sie RSS oder Telegram-Kanäle hinzufügen, TG-Pakete verwalten und eine CSV-Quelldatei anfordern."
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
      helpSourcesText: "En Fuentes puede añadir RSS o canales de Telegram, gestionar paquetes TG y solicitar un CSV de fuentes."
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
      helpSourcesText: "In Fonti puoi aggiungere RSS o canali Telegram, gestire pacchetti TG e richiedere un file CSV delle fonti."
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
      helpSourcesText: "У Крыніцах можна дадаваць RSS або Telegram-каналы, кіраваць TG-пакетамі і запытаць CSV-файл крыніц."
    }
  };
  Object.keys(paymentLabels).forEach((language) => {
    labels[language] = Object.assign(labels[language] || {}, paymentLabels[language]);
  });
  Object.keys(helpLabels).forEach((language) => {
    labels[language] = Object.assign(labels[language] || {}, helpLabels[language]);
  });

  const $ = (id) => document.getElementById(id);
  const statusText = $("statusText");

  if (tg) {
    document.body.classList.add("in-telegram");
    syncTelegramInsets();
    tg.ready();
    tg.expand();
    if (typeof tg.requestFullscreen === "function") {
      tg.requestFullscreen();
    }
    if (typeof tg.disableVerticalSwipes === "function") {
      tg.disableVerticalSwipes();
    }
    if (typeof tg.onEvent === "function") {
      tg.onEvent("safeAreaChanged", syncTelegramInsets);
      tg.onEvent("contentSafeAreaChanged", syncTelegramInsets);
      tg.onEvent("viewportChanged", syncTelegramInsets);
    }
  }

  applyTranslations();

  document.querySelectorAll(".tab").forEach((button) => {
    button.addEventListener("click", () => activateTab(button.dataset.tab));
  });

  $("closeButton").addEventListener("click", () => {
    if (tg) tg.close();
  });

  $("refreshButton").addEventListener("click", loadAll);
  $("checkButton").addEventListener("click", () => sendToChat({ action: "check" }));
  $("reportButton").addEventListener("click", () => sendToChat({ action: "report" }));
  $("plansButton").addEventListener("click", () => activateTab("plans"));
  $("plansRefreshButton").addEventListener("click", loadAll);
  $("sourcesFileButton").addEventListener("click", () => sendToChat({ action: "sources_file" }));

  $("languageSelect").addEventListener("change", (event) => {
    const language = event.target.value;
    state.language = language;
    state.pendingLanguage = language;
    applyTranslations();
    if (state.data) renderState();
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
    const enabled = !Boolean(state.data && state.data.monitoring.full_text);
    send({ action: "fulltext", enabled });
    if (state.data) {
      state.data.monitoring.full_text = enabled;
      renderState();
    }
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
    });
    document.querySelectorAll(".tab-panel").forEach((panel) => {
      panel.classList.toggle("is-active", panel.dataset.panel === name);
    });
  }

  async function loadAll() {
    try {
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
      applyTranslations();
      renderState();
      renderNews();
      setStatus("");
    } catch (error) {
      console.error(error);
      renderDemo();
      setStatus(t("loadError") + " " + t("openTelegram"));
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
    const activeSources = Number(data.monitoring.active_sources || 0);
    const monitoringSources = Number(data.monitoring.monitoring_sources || activeSources);
    $("activeSources").textContent = activeSources;
    $("sourcesMeta").textContent = monitoringSources > activeSources
      ? t("sources") + " / " + monitoringSources + " " + t("monitoringSources")
      : t("sources");
    $("sentToday").textContent = data.monitoring.sent_today + "/" + data.plan.alerts_per_day;

    fillSelect($("languageSelect"), data.languages, languageCode);
    fillSelect($("countrySelect"), data.countries, data.country.code);

    setToggle($("autoToggle"), data.monitoring.auto);
    $("autoToggleText").textContent = data.monitoring.auto ? t("automatic") : t("manual");
    setToggle($("fullTextToggle"), data.monitoring.full_text);
    $("fullTextToggleText").textContent = data.monitoring.full_text ? t("fullTextOn") : t("fullTextOff");

    renderKeywords(data.monitoring.keywords || []);
    renderTermChips("stopChips", data.monitoring.stop_words || [], "remove_stop_word");
    renderTermChips("plusChips", data.monitoring.plus_words || [], "remove_plus_word");
    renderSources(data.sources);
    renderPlans(data.payments);
  }

  function renderNews() {
    const list = $("newsList");
    const empty = $("emptyNews");
    list.innerHTML = "";
    empty.style.display = state.recent.length ? "none" : "block";
    if (!state.recent.length) {
      empty.querySelector("strong").textContent = t("noNews");
      empty.querySelector("span").textContent = t("noNewsHint");
      return;
    }
    state.recent.forEach((item) => {
      const card = document.createElement("article");
      card.className = "news-card";
      card.innerHTML = [
        '<div class="news-meta">',
        '<span class="badge">' + escapeHtml(item.keyword || "") + "</span>",
        '<span class="badge">' + escapeHtml(displaySourceName(item.source || "")) + "</span>",
        '<span class="badge">' + escapeHtml(formatDate(item.sent_at || item.published_at)) + "</span>",
        "</div>",
        "<h3>" + escapeHtml(item.title || "") + "</h3>",
        item.summary ? "<p>" + escapeHtml(item.summary) + "</p>" : "",
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

  function renderKeywords(values) {
    const root = $("keywordChips");
    root.innerHTML = "";
    values.forEach((item) => {
      root.appendChild(chip(item.phrase + " - " + item.country, () => {
        send({ action: "remove_keyword", value: item.phrase });
        setTimeout(loadAll, 800);
      }));
    });
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
    $("paidSources").textContent = sources.paid_telegram.active + "/" + sources.paid_telegram.total;
    $("customSources").textContent = sources.custom.active + "/" + sources.custom.total;
    renderSourceOverview(sources);

    const root = $("tgBlocks");
    root.innerHTML = "";
    (sources.tg_blocks || []).forEach((block) => {
      const row = document.createElement("div");
      row.className = "block-row";
      row.innerHTML = [
        "<span><strong>Top " + escapeHtml(block.label) + "</strong><small>" + block.active + "/" + block.total + " " + t("active") + "</small></span>",
        '<button class="compact-button" type="button" data-enabled="false">' + t("off") + "</button>",
        '<button class="compact-button" type="button" data-enabled="true">' + t("on") + "</button>"
      ].join("");
      row.querySelectorAll("button").forEach((button) => {
        button.addEventListener("click", () => {
          send({
            action: "tg_block",
            block: block.number,
            enabled: button.dataset.enabled === "true"
          });
          setTimeout(loadAll, 800);
        });
      });
      root.appendChild(row);
    });
  }

  function renderPlans(payments) {
    const root = $("plansGrid");
    if (!root) return;
    root.innerHTML = "";
    const plans = payments && payments.plans || [];
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

  function renderSourceOverview(sources) {
    const root = $("sourceList");
    root.innerHTML = "";
    const groups = [
      ["RSS", sources.standard_items || [], false],
      ["TG", sources.paid_telegram_items || [], false],
      ["Custom", sources.custom_items || [], true]
    ];
    groups.forEach(([title, items, isCustom]) => {
      const section = document.createElement("section");
      section.className = "source-section";
      const heading = document.createElement("h3");
      heading.textContent = title;
      section.appendChild(heading);
      if (!items.length) {
        const empty = document.createElement("p");
        empty.className = "muted-line";
        empty.textContent = "-";
        section.appendChild(empty);
      }
      items.slice(0, 12).forEach((item) => {
        const row = document.createElement("div");
        row.className = "source-row";
        row.innerHTML = [
          "<span>",
          "<strong>" + escapeHtml(displaySourceName(item.name || item.url || "")) + "</strong>",
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
      root.appendChild(section);
    });
  }

  function renderDemo() {
    applyTranslations();
    $("profileLine").textContent = "Monitorio";
    $("planName").textContent = "-";
    $("planMeta").textContent = "Telegram";
    $("activeSources").textContent = "-";
    $("sourcesMeta").textContent = t("sources");
    $("sentToday").textContent = "-";
    $("newsList").innerHTML = "";
    $("emptyNews").style.display = "block";
    $("emptyNews").querySelector("strong").textContent = t("noNews");
    $("emptyNews").querySelector("span").textContent = t("openTelegram");
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
        setStatus(result.error || t("checkoutError"));
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

  function formatTemplate(template, values) {
    return String(template || "").replace(/\{(\w+)\}/g, (_, key) => values[key] == null ? "" : String(values[key]));
  }

  function sourceMeta(item) {
    const parts = [];
    if (item.rank) parts.push("#" + item.rank);
    if (item.subscribers) parts.push(formatNumber(item.subscribers));
    if (item.type) parts.push(item.type);
    return parts.join(" · ") || item.url || "";
  }

  function displaySourceName(value) {
    const cleaned = String(value || "").replace(/\s+via\s+Google\s+News\s*$/i, "").trim();
    return cleaned || String(value || "");
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
