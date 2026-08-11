const tg = window.Telegram?.WebApp;
if (tg) {
  tg.ready();
  tg.expand();
}

const state = {
  data: null,
  telegramId: tg?.initDataUnsafe?.user?.id || null,
  lastResults: [],
  lastSearchLink: null,
  railWatches: [],
};

const $ = (selector) => document.querySelector(selector);
const $$ = (selector) => Array.from(document.querySelectorAll(selector));
const escapeHtml = (value) =>
  String(value ?? "")
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;");

function currentTelegramId() {
  return state.telegramId || 0;
}

function activateTab(tabName) {
  $$(".tabs button").forEach((item) => item.classList.toggle("active", item.dataset.tab === tabName));
  $$(".tab-panel").forEach((item) => item.classList.toggle("active", item.id === tabName));
}

function activateTransport(type) {
  $$(".transport-toggle button").forEach((item) => item.classList.toggle("active", item.dataset.transport === type));
  $$("[data-transport-panel]").forEach((item) => item.classList.toggle("hidden", item.dataset.transportPanel !== type));
  $("#search-status").textContent = "";
  $("#rail-status").textContent = "";
}

$$(".tabs button").forEach((button) => {
  button.addEventListener("click", () => activateTab(button.dataset.tab));
});

$$(".transport-toggle button").forEach((button) => {
  button.addEventListener("click", () => activateTransport(button.dataset.transport));
});

$("#settings-button").addEventListener("click", () => $("#settings-dialog").showModal());

$$('input[name="search_type"]').forEach((input) => {
  input.addEventListener("change", () => {
    const anywhere = input.value === "anywhere" && input.checked;
    $("#destination-field").style.display = anywhere ? "none" : "grid";
    document.querySelector('[name="destination"]').required = !anywhere;
  });
});

async function loadState() {
  const query = state.telegramId ? `?telegram_id=${state.telegramId}` : "";
  const response = await fetch(`/api/miniapp/state${query}`);
  state.data = await response.json();
  state.lastResults = state.data.finds || [];
  state.railWatches = state.data.rail_watches || [];
  renderAll();
}

async function postForm(url, fields = {}) {
  const form = new FormData();
  Object.entries(fields).forEach(([key, value]) => {
    if (value !== undefined && value !== null && value !== "") form.append(key, value);
  });
  const response = await fetch(url, { method: "POST", body: form });
  const payload = await response.json();
  if (!response.ok) {
    throw new Error(payload.detail || payload.status || "Запит не виконано");
  }
  return payload;
}

function normalizeAirportValue(value) {
  const match = String(value || "").match(/\b[A-Z]{3}\b/);
  return match ? match[0] : value;
}

async function bindAirportSuggestions(input) {
  const name = input.name;
  const box = document.querySelector(`[data-suggestions-for="${name}"]`);
  input.addEventListener("input", async () => {
    const q = input.value.trim();
    if (!q) {
      box.classList.remove("open");
      box.innerHTML = "";
      return;
    }
    const response = await fetch(`/api/miniapp/airports?q=${encodeURIComponent(q)}`);
    const data = await response.json();
    if (!data.items.length) {
      box.classList.remove("open");
      box.innerHTML = "";
      return;
    }
    box.innerHTML = data.items
      .map(
        (item) =>
          `<button type="button" data-code="${escapeHtml(item.code)}">${escapeHtml(item.city)}, ${escapeHtml(item.country)}, ${escapeHtml(item.code)}</button>`,
      )
      .join("");
    box.classList.add("open");
    box.querySelectorAll("button").forEach((button) => {
      button.addEventListener("click", () => {
        input.value = button.textContent;
        input.dataset.code = button.dataset.code;
        box.classList.remove("open");
      });
    });
  });
}

async function bindRailStationSuggestions(input) {
  const name = input.name;
  const box = document.querySelector(`[data-rail-suggestions-for="${name}"]`);
  input.addEventListener("input", async () => {
    const q = input.value.trim();
    if (!q) {
      box.classList.remove("open");
      box.innerHTML = "";
      return;
    }
    const response = await fetch(`/api/miniapp/rail/stations?q=${encodeURIComponent(q)}`);
    const data = await response.json();
    if (!data.items.length) {
      box.classList.remove("open");
      box.innerHTML = "";
      return;
    }
    box.innerHTML = data.items
      .map(
        (item) =>
          `<button type="button" data-name="${escapeHtml(item.name)}">${escapeHtml(item.name)} <span>${escapeHtml(item.city)}</span></button>`,
      )
      .join("");
    box.classList.add("open");
    box.querySelectorAll("button").forEach((button) => {
      button.addEventListener("click", () => {
        input.value = button.dataset.name;
        box.classList.remove("open");
      });
    });
  });
}

$$("[data-airport-input]").forEach(bindAirportSuggestions);
$$("[data-rail-station-input]").forEach(bindRailStationSuggestions);

$("#search-form").addEventListener("submit", async (event) => {
  event.preventDefault();
  const form = event.currentTarget;
  const formData = new FormData(form);
  const searchType = formData.get("search_type");
  const originInput = form.querySelector('[name="origin"]');
  const destinationInput = form.querySelector('[name="destination"]');
  const fields = {
    telegram_id: currentTelegramId(),
    search_type: searchType,
    origin: originInput.dataset.code || normalizeAirportValue(formData.get("origin")),
    destination: searchType === "anywhere" ? "" : destinationInput.dataset.code || normalizeAirportValue(formData.get("destination")),
    departure_date: formData.get("departure_date"),
    return_date: formData.get("return_date"),
    passengers: formData.get("passengers"),
    direct_only: formData.get("direct_only") ? "true" : "",
    baggage_required: formData.get("baggage_required") ? "true" : "",
    max_price: formData.get("max_price"),
    currency: formData.get("currency"),
  };
  $("#search-status").textContent = "Шукаю доступні варіанти...";
  const result = await postForm("/api/miniapp/search", fields);
  state.lastResults = result.results || [];
  state.lastSearchLink = result.search_link || null;
  $("#search-status").textContent = state.lastResults.length
    ? `Знайдено: ${state.lastResults.length}`
    : "У кеші немає готової ціни. Можна відкрити пошук на Aviasales.";
  await loadState();
  state.lastResults = result.results || state.lastResults;
  renderFinds(state.lastResults);
  activateTab("finds");
});

$("#rail-watch-form").addEventListener("submit", async (event) => {
  event.preventDefault();
  const formData = new FormData(event.currentTarget);
  $("#rail-status").textContent = "Зберігаю відстеження...";
  const result = await postForm("/api/miniapp/rail/watch", {
    telegram_id: currentTelegramId(),
    origin_station: formData.get("origin_station"),
    destination_station: formData.get("destination_station"),
    travel_date: formData.get("travel_date"),
    seat_type: formData.get("seat_type"),
    train_number: formData.get("train_number"),
  });
  state.railWatches = [result.watch, ...state.railWatches];
  $("#rail-status").textContent = "Відстеження додано. Бот перевірятиме появу потрібного квитка.";
  event.currentTarget.reset();
  await loadState();
  renderRailWatches(state.railWatches);
});

function renderAll() {
  renderFinds(state.lastResults);
  renderHistory(state.data.history || []);
  renderFavorites(state.data.favorites || []);
  renderRailWatches(state.railWatches || []);
}

function ticketCard(result, options = {}) {
  const stops = result.stops === 0 ? "Прямий рейс" : `${result.stops} пересадка`;
  const returnLine = result.return_departure_at
    ? `<div class="meta">Повернення: ${escapeHtml(result.return_departure_at)}</div>`
    : "";
  const source = result.source || "affiliate search";
  const saveButton = options.favorite
    ? ""
    : `<button type="button" class="secondary-button ok" data-save="${result.id}">Зберегти</button>`;
  return `
    <article class="ticket-card">
      <div class="ticket-top">
        <div>
          <div class="route">${escapeHtml(result.origin)} → ${escapeHtml(result.destination)}</div>
          <div class="meta">Виліт: ${escapeHtml(result.departure_at || "-")}</div>
          ${returnLine}
        </div>
        <div class="price">${escapeHtml(result.price)} ${escapeHtml(result.currency)}</div>
      </div>
      <div class="ticket-middle">
        <span class="tag">${escapeHtml(stops)}</span>
        <span class="meta">${escapeHtml(result.airline || "-")} · ${escapeHtml(result.baggage || "багаж невідомий")}</span>
      </div>
      <div class="meta">Джерело: ${escapeHtml(source)}</div>
      <div class="meta">Ціна з кешу. Фінальну наявність і суму перевіряйте на сайті продавця.</div>
      <div class="ticket-actions">
        <a href="${escapeHtml(result.booking_url)}" target="_blank" rel="noopener" data-open-ticket="${result.id}">Відкрити квиток</a>
        ${saveButton}
        <button type="button" class="secondary-button accent" data-watch="${result.id}">Стежити за ціною</button>
      </div>
    </article>
  `;
}

function attachTicketActions(container) {
  container.querySelectorAll("[data-save]").forEach((button) => {
    button.addEventListener("click", async () => {
      await postForm("/api/miniapp/favorites", {
        telegram_id: currentTelegramId(),
        flight_result_id: button.dataset.save,
      });
      button.textContent = "Збережено";
      button.disabled = true;
      await loadState();
    });
  });
  container.querySelectorAll("[data-watch]").forEach((button) => {
    button.addEventListener("click", async () => {
      await postForm("/api/miniapp/watch", {
        telegram_id: currentTelegramId(),
        flight_result_id: button.dataset.watch,
      });
      button.textContent = "$10: очікує оплати";
      button.disabled = true;
    });
  });
  container.querySelectorAll("[data-open-ticket]").forEach((link) => {
    link.addEventListener("click", () => {
      postForm("/api/miniapp/click", {
        telegram_id: currentTelegramId(),
        flight_result_id: link.dataset.openTicket,
        url: link.href,
      });
    });
  });
}

function renderFinds(results) {
  const target = $("#find-list");
  if (!results.length) {
    target.innerHTML = `
      <article class="ticket-card">
        <div class="route">Готової ціни не знайдено</div>
        <div class="meta">Travelpayouts Data API працює з кешем. Якщо в кеші немає ціни, відкрийте пошук на Aviasales і перевірте актуальні варіанти.</div>
        ${
          state.lastSearchLink
            ? `<div class="ticket-actions"><a href="${escapeHtml(state.lastSearchLink)}" target="_blank" rel="noopener">Відкрити пошук</a></div>`
            : ""
        }
      </article>
    `;
    return;
  }
  const cards = results.map((result, index) => {
    const ad =
      index === 2
        ? `<article class="ad-card"><strong>Партнерська пропозиція</strong><span class="meta">Добірка дешевих напрямків з вашого міста. Реклама не впливає на порядок результатів.</span></article>`
        : "";
    return ticketCard(result) + ad;
  });
  target.innerHTML = cards.join("");
  attachTicketActions(target);
}

function renderHistory(items) {
  const target = $("#history-list");
  if (!items.length) {
    target.innerHTML = `<div class="empty">Історія пошуку поки порожня.</div>`;
    return;
  }
  target.innerHTML = items
    .map(
      (item) => `
        <article class="history-card">
          <div class="history-top">
            <div>
              <div class="route">${escapeHtml(item.origin)} → ${escapeHtml(item.destination || "будь-куди")}</div>
              <div class="meta">${escapeHtml(item.departure_date || "дата не задана")} · ${escapeHtml(item.search_type)}</div>
            </div>
            <span class="tag">${escapeHtml(item.result_count || 0)} вар.</span>
          </div>
          <div class="meta">Найнижча ціна: ${escapeHtml(item.best_price || "-")} ${escapeHtml(item.currency)}</div>
          <button type="button" class="secondary-button" data-repeat="${item.id}">Повторити пошук</button>
        </article>
      `,
    )
    .join("");
}

function renderFavorites(items) {
  const target = $("#favorite-list");
  if (!items.length) {
    target.innerHTML = `<div class="empty">Збережених квитків ще немає.</div>`;
    return;
  }
  target.innerHTML = items.map((result) => ticketCard(result, { favorite: true })).join("");
  attachTicketActions(target);
}

function railSeatLabel(seatType) {
  return {
    any: "будь-яке",
    coupe: "купе",
    platzkart: "плацкарт",
    lux: "люкс",
    sitting: "сидячий",
    intercity: "Інтерсіті",
  }[seatType] || "будь-яке";
}

function railStatusClass(watch) {
  if (!watch.active) return "paused";
  if (watch.last_available) return "available";
  return "";
}

function railStatusLabel(watch) {
  if (!watch.active) return "Пауза";
  if (watch.last_available) return "Квиток є";
  return "Активно";
}

function renderRailWatches(items) {
  const target = $("#rail-watch-list");
  if (!items.length) {
    target.innerHTML = `<div class="empty">Відстежень УЗ ще немає.</div>`;
    return;
  }
  target.innerHTML = items
    .map(
      (watch) => `
        <article class="rail-watch-card">
          <div class="rail-watch-top">
            <div>
              <div class="route">${escapeHtml(watch.origin_station)} → ${escapeHtml(watch.destination_station)}</div>
              <div class="meta">${escapeHtml(watch.travel_date)} · ${escapeHtml(railSeatLabel(watch.seat_type))}${watch.train_number ? ` · ${escapeHtml(watch.train_number)}` : ""}</div>
            </div>
            <span class="rail-status ${railStatusClass(watch)}">${railStatusLabel(watch)}</span>
          </div>
          <div class="meta">${escapeHtml(watch.last_status || "Перевірка ще не виконувалась.")}</div>
          ${watch.last_error ? `<div class="meta">Статус джерела: ${escapeHtml(watch.last_error)}</div>` : ""}
          <div class="ticket-actions">
            <button type="button" class="secondary-button" data-rail-check="${watch.id}">Перевірити зараз</button>
            <button type="button" class="secondary-button ${watch.active ? "danger" : "ok"}" data-rail-toggle="${watch.id}" data-active="${watch.active ? "0" : "1"}">${watch.active ? "Пауза" : "Відновити"}</button>
            <a href="https://booking.uz.gov.ua/" target="_blank" rel="noopener">Відкрити УЗ</a>
          </div>
        </article>
      `,
    )
    .join("");
  attachRailActions(target);
}

function attachRailActions(container) {
  container.querySelectorAll("[data-rail-check]").forEach((button) => {
    button.addEventListener("click", async () => {
      button.disabled = true;
      button.textContent = "Перевіряю...";
      const result = await postForm(`/api/miniapp/rail/watches/${button.dataset.railCheck}/check`);
      $("#rail-status").textContent = result.result?.status || "Перевірку виконано.";
      await loadState();
    });
  });
  container.querySelectorAll("[data-rail-toggle]").forEach((button) => {
    button.addEventListener("click", async () => {
      await postForm(`/api/miniapp/rail/watches/${button.dataset.railToggle}/toggle`, {
        active: button.dataset.active === "1" ? "true" : "false",
      });
      await loadState();
    });
  });
}

loadState().catch(() => {
  document.body.innerHTML = '<main class="app-shell"><div class="ticket-card">Не вдалося завантажити кабінет.</div></main>';
});
