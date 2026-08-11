(function () {
  "use strict";

  const tg = window.Telegram && window.Telegram.WebApp;
  const $ = (selector, root = document) => root.querySelector(selector);
  const $$ = (selector, root = document) => Array.from(root.querySelectorAll(selector));
  const state = {
    userId: resolveUserId(),
    profile: null,
    searches: [],
    myListings: [],
    feed: [],
    listingStep: 1,
    toastTimer: null
  };

  const roleScreen = $("#roleScreen");
  const appShell = $("#appShell");
  const loader = $("#appLoader");
  const searchForm = $("#searchForm");
  const listingForm = $("#listingForm");
  const listingDraftKey = `monitorio-rent-listing-draft:${state.userId}`;

  if (tg) {
    tg.ready();
    tg.expand();
  }

  bindEvents();
  restoreListingDraft();
  loadState();

  function resolveUserId() {
    const telegramUser = tg && tg.initDataUnsafe && tg.initDataUnsafe.user;
    if (telegramUser && telegramUser.id) return String(telegramUser.id);
    let demoId = localStorage.getItem("monitorio-rent-demo-user");
    if (!demoId) {
      demoId = `demo-${crypto.randomUUID ? crypto.randomUUID() : Date.now()}`;
      localStorage.setItem("monitorio-rent-demo-user", demoId);
    }
    return demoId;
  }

  function bindEvents() {
    $$("[data-role]").forEach((button) => button.addEventListener("click", () => chooseRole(button.dataset.role)));
    $("#changeRoleButton").addEventListener("click", showRoleScreen);
    $$("[data-tab]").forEach((button) => button.addEventListener("click", () => openPanel(button.dataset.tab)));
    $$("[data-go]").forEach((button) => button.addEventListener("click", () => openPanel(button.dataset.go)));
    $("#welcomeAction").addEventListener("click", () => openPanel(state.profile && state.profile.role === "landlord" ? "place" : "search"));
    searchForm.addEventListener("submit", saveSearch);
    listingForm.addEventListener("input", () => {
      saveListingDraft();
      if (state.listingStep === 3) updateListingPreview();
    });
    listingForm.addEventListener("change", () => {
      saveListingDraft();
      if (state.listingStep === 3) updateListingPreview();
    });
    listingForm.addEventListener("submit", submitListing);
    $("#nextStep").addEventListener("click", nextListingStep);
    $("#previousStep").addEventListener("click", previousListingStep);
    $("#photoInput").addEventListener("change", renderPhotoPreview);
  }

  async function loadState() {
    try {
      const data = await api(`/api/state?user_id=${encodeURIComponent(state.userId)}`);
      applyState(data);
      if (state.profile) showApp();
      else showRoleScreen();
    } catch (error) {
      showRoleScreen();
      toast(error.message || "Не вдалося завантажити кабінет");
    } finally {
      hideLoader();
    }
  }

  function applyState(data) {
    state.profile = data.profile || null;
    state.searches = data.searches || [];
    state.myListings = data.my_listings || [];
    state.feed = data.feed || [];
    renderDashboard();
  }

  async function refreshState() {
    const data = await api(`/api/state?user_id=${encodeURIComponent(state.userId)}`);
    applyState(data);
  }

  async function chooseRole(role) {
    const buttons = $$("[data-role]");
    buttons.forEach((button) => { button.disabled = true; });
    try {
      const data = await api("/api/profile", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ user_id: state.userId, role })
      });
      state.profile = data.profile;
      showApp();
      renderDashboard();
      openPanel(role === "landlord" ? "place" : "search");
      toast(role === "landlord" ? "Режим «Здаю» увімкнено" : "Режим «Орендую» увімкнено");
    } catch (error) {
      toast(error.message || "Не вдалося зберегти вибір");
    } finally {
      buttons.forEach((button) => { button.disabled = false; });
    }
  }

  function showRoleScreen() {
    roleScreen.hidden = false;
    appShell.hidden = true;
    $("[data-role='renter']").focus();
  }

  function showApp() {
    roleScreen.hidden = true;
    appShell.hidden = false;
    renderDashboard();
  }

  function openPanel(name) {
    $$(".panel").forEach((panel) => panel.classList.toggle("is-active", panel.dataset.panel === name));
    $$(".nav-item").forEach((button) => button.classList.toggle("is-active", button.dataset.tab === name));
    const panel = $(`.panel[data-panel='${name}']`);
    if (panel) {
      panel.focus({ preventScroll: true });
      window.scrollTo({ top: 0, behavior: "smooth" });
    }
  }

  function renderDashboard() {
    const role = state.profile ? state.profile.role : "renter";
    const isLandlord = role === "landlord";
    $("#searchCount").textContent = String(state.searches.length);
    $("#listingCount").textContent = String(state.myListings.length);
    $("#roleLabel").textContent = isLandlord ? "Здаю" : "Орендую";
    $("#headerTitle").textContent = isLandlord ? "Кабінет власника" : "Кабінет орендаря";
    $("#welcomeEyebrow").textContent = isLandlord ? "Ваше оголошення" : "Ваш пошук";
    $("#welcomeTitle").textContent = isLandlord
      ? "Розмістіть квартиру й отримуйте звернення орендарів"
      : "Знайдіть квартиру без щоденного ручного пошуку";
    $("#welcomeText").textContent = isLandlord
      ? "Заповніть дані квартири. Перед появою в пошуку оголошення пройде перевірку."
      : "Збережіть умови — нові відповідні квартири з’являтимуться тут.";
    $("#welcomeAction").textContent = isLandlord ? "Розмістити квартиру" : "Створити пошук";
    renderFeed();
    renderSearches();
    renderMyListings();
  }

  async function saveSearch(event) {
    event.preventDefault();
    setMessage("searchMessage", "");
    if (!searchForm.reportValidity()) return;
    const values = Object.fromEntries(new FormData(searchForm).entries());
    const payload = {
      user_id: state.userId,
      city: values.city,
      district: values.district || "",
      price_min: Number(values.price_min || 0),
      price_max: Number(values.price_max),
      rooms_min: Number(values.rooms_min || 1),
      rooms_max: Number(values.rooms_max || 1),
      pets_allowed: Boolean(values.pets_allowed),
      no_commission: Boolean(values.no_commission),
      owner_only: Boolean(values.owner_only)
    };
    const submitButton = $("button[type='submit']", searchForm);
    submitButton.disabled = true;
    submitButton.textContent = "Зберігаємо…";
    try {
      await api("/api/searches", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload)
      });
      await refreshState();
      const query = new URLSearchParams({
        city: payload.city,
        district: payload.district,
        price_min: String(payload.price_min),
        price_max: String(payload.price_max),
        rooms_min: String(payload.rooms_min),
        rooms_max: String(payload.rooms_max),
        pets_allowed: String(payload.pets_allowed),
        no_commission: String(payload.no_commission),
        owner_only: String(payload.owner_only),
        limit: "100"
      });
      const matches = await api(`/api/listings?${query.toString()}`);
      state.feed = matches.listings || [];
      renderFeed();
      searchForm.reset();
      openPanel("home");
      setMessage("searchMessage", "Пошук збережено. Сповіщення будуть надходити для нових збігів.", "success");
      toast("Пошук збережено");
    } catch (error) {
      setMessage("searchMessage", error.message || "Не вдалося зберегти пошук", "error");
    } finally {
      submitButton.disabled = false;
      submitButton.textContent = "Зберегти пошук";
    }
  }

  function nextListingStep() {
    const step = $(`.form-step[data-step='${state.listingStep}']`);
    const fields = $$('input, select, textarea', step).filter((field) => field.type !== "file");
    for (const field of fields) {
      if (!field.checkValidity()) {
        field.reportValidity();
        field.focus();
        return;
      }
    }
    if (state.listingStep === 1 && !validateFloors()) return;
    state.listingStep = Math.min(3, state.listingStep + 1);
    updateListingStep();
  }

  function previousListingStep() {
    state.listingStep = Math.max(1, state.listingStep - 1);
    updateListingStep();
  }

  function validateFloors() {
    const floor = Number(listingForm.elements.floor.value || 0);
    const total = Number(listingForm.elements.total_floors.value || 0);
    if (floor && total && floor > total) {
      listingForm.elements.floor.setCustomValidity("Поверх не може бути вищим за поверховість будинку");
      listingForm.elements.floor.reportValidity();
      listingForm.elements.floor.setCustomValidity("");
      return false;
    }
    return true;
  }

  function updateListingStep() {
    $$(".form-step").forEach((step) => step.classList.toggle("is-active", Number(step.dataset.step) === state.listingStep));
    const names = ["Квартира", "Умови та фото", "Контакт і перевірка"];
    $("#stepLabel").textContent = `Крок ${state.listingStep} із 3`;
    $("#stepName").textContent = names[state.listingStep - 1];
    $("#progressBar").style.width = `${state.listingStep * 33.333}%`;
    $("#previousStep").hidden = state.listingStep === 1;
    $("#nextStep").hidden = state.listingStep === 3;
    $("#submitListing").hidden = state.listingStep !== 3;
    if (state.listingStep === 3) updateListingPreview();
    const heading = $(".step-heading h3", $(`.form-step[data-step='${state.listingStep}']`));
    if (heading) heading.focus({ preventScroll: true });
    window.scrollTo({ top: 0, behavior: "smooth" });
  }

  function updateListingPreview() {
    const values = Object.fromEntries(new FormData(listingForm).entries());
    const preview = $("#listingPreview");
    preview.replaceChildren();
    const title = document.createElement("h4");
    title.textContent = `${values.rooms || "—"}-кімнатна квартира`;
    const location = document.createElement("p");
    location.textContent = [values.city, values.district, values.address].filter(Boolean).join(", ") || "Локацію ще не вказано";
    const price = document.createElement("p");
    price.className = "preview-price";
    price.textContent = values.price_uah ? `${formatNumber(values.price_uah)} грн/місяць` : "Ціну ще не вказано";
    const details = document.createElement("p");
    const floor = values.floor ? `, ${values.floor}/${values.total_floors || "—"} поверх` : "";
    details.textContent = `${values.area_sqm || "—"} м²${floor}`;
    const conditions = document.createElement("p");
    conditions.textContent = `${values.pets_allowed ? "Можна з тваринами" : "Тварини — за домовленістю"} · Комісія ${values.commission_pct || 0}%`;
    preview.append(title, location, price, details, conditions);
  }

  async function submitListing(event) {
    event.preventDefault();
    setMessage("listingMessage", "");
    if (!listingForm.reportValidity() || !validateFloors()) return;
    const files = Array.from($("#photoInput").files || []);
    if (files.length > 8) {
      setMessage("listingMessage", "Можна додати не більше 8 фотографій.", "error");
      return;
    }
    const formData = new FormData(listingForm);
    formData.set("user_id", state.userId);
    formData.delete("confirmed");
    ["floor", "total_floors"].forEach((name) => {
      if (!formData.get(name)) formData.delete(name);
    });
    if (!formData.has("pets_allowed")) formData.set("pets_allowed", "false");
    const submitButton = $("#submitListing");
    submitButton.disabled = true;
    submitButton.textContent = "Надсилаємо…";
    try {
      const data = await api("/api/listings", { method: "POST", body: formData });
      localStorage.removeItem(listingDraftKey);
      listingForm.reset();
      state.listingStep = 1;
      updateListingStep();
      renderPhotoPreview();
      await refreshState();
      setMessage("listingMessage", data.message || "Оголошення надіслано на перевірку", "success");
      toast("Оголошення надіслано на перевірку");
      openPanel("mine");
    } catch (error) {
      setMessage("listingMessage", error.message || "Не вдалося надіслати оголошення", "error");
    } finally {
      submitButton.disabled = false;
      submitButton.textContent = "Надіслати на перевірку";
    }
  }

  function saveListingDraft() {
    const draft = {};
    new FormData(listingForm).forEach((value, key) => {
      if (!(value instanceof File)) draft[key] = value;
    });
    $$("input[type='checkbox']", listingForm).forEach((input) => { draft[input.name] = input.checked; });
    localStorage.setItem(listingDraftKey, JSON.stringify(draft));
  }

  function restoreListingDraft() {
    try {
      const draft = JSON.parse(localStorage.getItem(listingDraftKey) || "null");
      if (!draft) return;
      Object.entries(draft).forEach(([name, value]) => {
        const field = listingForm.elements[name];
        if (!field || name === "confirmed") return;
        if (field.type === "checkbox") field.checked = Boolean(value);
        else field.value = String(value);
      });
    } catch (_) {
      localStorage.removeItem(listingDraftKey);
    }
  }

  function renderPhotoPreview() {
    const container = $("#photoPreview");
    container.replaceChildren();
    const files = Array.from($("#photoInput").files || []).slice(0, 8);
    files.forEach((file) => {
      const image = document.createElement("img");
      image.alt = `Попередній перегляд: ${file.name}`;
      const url = URL.createObjectURL(file);
      image.src = url;
      image.addEventListener("load", () => URL.revokeObjectURL(url), { once: true });
      container.appendChild(image);
    });
    if ($("#photoInput").files && $("#photoInput").files.length > 8) {
      setMessage("listingMessage", "Буде використано лише перші 8 фото.", "error");
    }
  }

  function renderFeed() {
    const container = $("#feedList");
    container.replaceChildren();
    state.feed.forEach((listing) => container.appendChild(listingCard(listing)));
    $("#feedEmpty").hidden = state.feed.length > 0;
  }

  function listingCard(listing) {
    const card = document.createElement("article");
    card.className = "listing-card";
    if (listing.photos && listing.photos[0]) {
      const image = document.createElement("img");
      image.className = "listing-image";
      image.src = listing.photos[0];
      image.alt = `Квартира: ${listing.city}, ${listing.address}`;
      image.loading = "lazy";
      card.appendChild(image);
    } else {
      const placeholder = document.createElement("div");
      placeholder.className = "listing-placeholder";
      placeholder.textContent = "Фото ще не додано";
      card.appendChild(placeholder);
    }
    const body = document.createElement("div");
    body.className = "listing-body";
    const title = document.createElement("h3");
    const details = [];
    if (Number(listing.rooms) > 0) details.push(`${listing.rooms}-кімнатна`);
    if (Number(listing.area_sqm) > 0) details.push(`${listing.area_sqm} м²`);
    title.textContent = details.join(" · ") || "Квартира в оренду";
    const location = document.createElement("p");
    location.textContent = [listing.city, listing.district].filter(Boolean).join(", ");
    const price = document.createElement("p");
    price.className = "price";
    price.textContent = Number(listing.price_uah) > 0
      ? `${formatNumber(listing.price_uah)} грн/місяць`
      : (listing.price_original || "Ціну дивіться в оголошенні");
    const badge = document.createElement("span");
    badge.className = `status-badge ${listing.status === "active" ? "active" : ""}`;
    badge.textContent = statusLabel(listing.status);
    body.append(title, location, price, badge);
    if (listing.source_url) {
      const source = document.createElement("a");
      source.className = "source-link";
      source.href = listing.source_url;
      source.target = "_blank";
      source.rel = "noopener noreferrer";
      source.textContent = `Telegram · ${listing.source_title || "джерело"}`;
      body.appendChild(source);
    }
    card.appendChild(body);
    return card;
  }

  function renderSearches() {
    const container = $("#savedSearches");
    container.replaceChildren();
    state.searches.forEach((search) => {
      const item = document.createElement("div");
      item.className = "stack-item";
      const text = document.createElement("div");
      const title = document.createElement("strong");
      title.textContent = `${search.city}${search.district ? `, ${search.district}` : ""}`;
      const meta = document.createElement("small");
      meta.textContent = `до ${formatNumber(search.price_max)} грн · ${roomRange(search.rooms_min, search.rooms_max)}`;
      text.append(title, meta);
      const show = document.createElement("button");
      show.type = "button";
      show.className = "text-button";
      show.textContent = "Показати";
      show.addEventListener("click", () => showSearchResults(search));
      const remove = document.createElement("button");
      remove.type = "button";
      remove.className = "remove-button";
      remove.textContent = "Видалити";
      remove.setAttribute("aria-label", `Видалити пошук ${title.textContent}`);
      remove.addEventListener("click", () => removeSearch(search.id));
      item.append(text, show, remove);
      container.appendChild(item);
    });
    $("#searchesEmpty").hidden = state.searches.length > 0;
  }

  async function showSearchResults(search) {
    const query = new URLSearchParams({
      city: search.city,
      district: search.district || "",
      price_min: String(search.price_min || 0),
      price_max: String(search.price_max),
      rooms_min: String(search.rooms_min),
      rooms_max: String(search.rooms_max),
      pets_allowed: String(Boolean(search.pets_allowed)),
      no_commission: String(Boolean(search.no_commission)),
      owner_only: String(Boolean(search.owner_only)),
      limit: "100"
    });
    try {
      const matches = await api(`/api/listings?${query.toString()}`);
      state.feed = matches.listings || [];
      renderFeed();
      openPanel("home");
      toast(`Знайдено оголошень: ${state.feed.length}`);
    } catch (error) {
      toast(error.message || "Не вдалося завантажити результати");
    }
  }

  async function removeSearch(id) {
    try {
      await api(`/api/searches/${encodeURIComponent(id)}?user_id=${encodeURIComponent(state.userId)}`, { method: "DELETE" });
      await refreshState();
      toast("Пошук видалено");
    } catch (error) {
      toast(error.message || "Не вдалося видалити пошук");
    }
  }

  function renderMyListings() {
    const container = $("#myListings");
    container.replaceChildren();
    state.myListings.forEach((listing) => {
      const item = document.createElement("div");
      item.className = "stack-item";
      const text = document.createElement("div");
      const title = document.createElement("strong");
      title.textContent = `${listing.city}, ${listing.address}`;
      const meta = document.createElement("small");
      meta.textContent = `${formatNumber(listing.price_uah)} грн · ${statusLabel(listing.status)}`;
      text.append(title, meta);
      const badge = document.createElement("span");
      badge.className = `status-badge ${listing.status === "active" ? "active" : ""}`;
      badge.textContent = statusLabel(listing.status);
      item.append(text, badge);
      container.appendChild(item);
    });
    $("#listingsEmpty").hidden = state.myListings.length > 0;
  }

  function statusLabel(status) {
    return ({ pending: "На перевірці", active: "Опубліковано", rejected: "Відхилено", archived: "В архіві", draft: "Чернетка" })[status] || status;
  }

  function roomRange(min, max) {
    if (min === max) return `${min} кімн.`;
    if (max >= 10) return `${min}+ кімн.`;
    return `${min}–${max} кімн.`;
  }

  function formatNumber(value) {
    return new Intl.NumberFormat("uk-UA").format(Number(value || 0));
  }

  function setMessage(id, text, kind = "") {
    const element = $(`#${id}`);
    element.textContent = text;
    element.classList.toggle("is-error", kind === "error");
    element.classList.toggle("is-success", kind === "success");
  }

  function toast(message) {
    const element = $("#toast");
    element.textContent = message;
    element.hidden = false;
    clearTimeout(state.toastTimer);
    state.toastTimer = setTimeout(() => { element.hidden = true; }, 4000);
  }

  function hideLoader() {
    loader.classList.add("is-hidden");
    setTimeout(() => { loader.hidden = true; }, 220);
  }

  async function api(url, options = {}) {
    const response = await fetch(url, options);
    let payload = {};
    try { payload = await response.json(); } catch (_) { payload = {}; }
    if (!response.ok) {
      const detail = payload.detail;
      if (Array.isArray(detail)) {
        throw new Error(detail.map((item) => item.msg).join(". "));
      }
      throw new Error(typeof detail === "string" ? detail : "Сталася помилка. Спробуйте ще раз.");
    }
    return payload;
  }
})();
