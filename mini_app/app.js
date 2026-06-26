(function () {
  const tg = window.Telegram && window.Telegram.WebApp;
  const apiBase = configuredApiBase();
  const state = {
    data: null,
    recent: [],
    language: "en"
  };

  const labels = {
    en: {
      plan: "Pakiet",
      sources: "Sources",
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
      keyword: "Suchwort",
      keywordPlaceholder: "for example: bitcoin",
      addKeyword: "Add keyword",
      stopWord: "Stop word",
      stopPlaceholder: "word to exclude",
      plusWord: "Required word",
      plusPlaceholder: "extra condition",
      add: "Add",
      addRss: "Add RSS",
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
      typeRss: "Enter an RSS URL.",
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
      typeRss: "Введіть URL RSS.",
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
      typeRss: "Введите URL RSS.",
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
      plan: "Tarifa",
      sources: "Źródła",
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
      typeRss: "Wpisz URL RSS.",
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
      keyword: "Keyword",
      keywordPlaceholder: "zum Beispiel: bitcoin",
      addKeyword: "Keyword hinzufügen",
      stopWord: "Stoppwort",
      stopPlaceholder: "auszuschließendes Wort",
      plusWord: "Pflichtwort",
      plusPlaceholder: "zusätzliche Bedingung",
      add: "Hinzufügen",
      addRss: "RSS hinzufügen",
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
      typeRss: "RSS-URL eingeben.",
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
      plan: "Plan",
      sources: "Fuentes",
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
      typeRss: "Introduzca una URL RSS.",
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
      typeRss: "Inserisci un URL RSS.",
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
      typeRss: "Увядзіце URL RSS.",
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

  const $ = (id) => document.getElementById(id);
  const statusText = $("statusText");

  if (tg) {
    tg.ready();
    tg.expand();
    if (typeof tg.requestFullscreen === "function") {
      tg.requestFullscreen();
    }
    if (typeof tg.disableVerticalSwipes === "function") {
      tg.disableVerticalSwipes();
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
  $("plansButton").addEventListener("click", () => sendToChat({ action: "plans" }));
  $("sourcesFileButton").addEventListener("click", () => sendToChat({ action: "sources_file" }));

  $("languageSelect").addEventListener("change", (event) => {
    state.language = event.target.value;
    applyTranslations();
    if (state.data) renderState();
    send({ action: "set_language", language: event.target.value });
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

  loadAll();

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
      const [statePayload, recentPayload] = await Promise.all([
        apiGet("/api/state"),
        apiGet("/api/recent")
      ]);
      state.data = statePayload;
      state.recent = recentPayload.items || [];
      state.language = statePayload.language && statePayload.language.code || "en";
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
    $("profileLine").textContent = data.country.label + " - " + data.language.name;
    $("planName").textContent = data.plan.name;
    $("planMeta").textContent = data.locked ? t("locked") : data.plan.id;
    $("activeSources").textContent = data.monitoring.active_sources;
    $("sentToday").textContent = data.monitoring.sent_today + "/" + data.plan.alerts_per_day;

    fillSelect($("languageSelect"), data.languages, data.language.code);
    fillSelect($("countrySelect"), data.countries, data.country.code);

    setToggle($("autoToggle"), data.monitoring.auto);
    $("autoToggleText").textContent = data.monitoring.auto ? t("automatic") : t("manual");
    setToggle($("fullTextToggle"), data.monitoring.full_text);
    $("fullTextToggleText").textContent = data.monitoring.full_text ? t("fullTextOn") : t("fullTextOff");

    renderKeywords(data.monitoring.keywords || []);
    renderTermChips("stopChips", data.monitoring.stop_words || [], "remove_stop_word");
    renderTermChips("plusChips", data.monitoring.plus_words || [], "remove_plus_word");
    renderSources(data.sources);
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
        '<span class="badge">' + escapeHtml(item.source || "") + "</span>",
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

  function renderSourceOverview(sources) {
    const root = $("sourceList");
    root.innerHTML = "";
    const groups = [
      ["RSS", sources.standard_items || []],
      ["TG", sources.paid_telegram_items || []],
      ["Custom", sources.custom_items || []]
    ];
    groups.forEach(([title, items]) => {
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
          "<strong>" + escapeHtml(item.name || item.url || "") + "</strong>",
          "<small>" + escapeHtml(sourceMeta(item)) + "</small>",
          "</span>",
          '<b class="' + (item.active ? "dot is-active" : "dot") + '"></b>'
        ].join("");
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

  function sourceMeta(item) {
    const parts = [];
    if (item.rank) parts.push("#" + item.rank);
    if (item.subscribers) parts.push(formatNumber(item.subscribers));
    if (item.type) parts.push(item.type);
    return parts.join(" · ") || item.url || "";
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
