(function () {
  const tg = window.Telegram && window.Telegram.WebApp;
  const statusText = document.getElementById("statusText");

  if (tg) {
    tg.ready();
    tg.expand();
  }

  function setStatus(text) {
    statusText.textContent = text;
  }

  function send(payload, message) {
    if (!tg || !tg.sendData) {
      setStatus("Відкрийте цей кабінет через Telegram.");
      return;
    }
    tg.sendData(JSON.stringify(payload));
    setStatus(message || "Дію надіслано боту.");
  }

  function valueOf(id) {
    return document.getElementById(id).value.trim();
  }

  document.getElementById("closeButton").addEventListener("click", function () {
    if (tg) tg.close();
  });

  document.getElementById("addKeywordButton").addEventListener("click", function () {
    const value = valueOf("keywordInput");
    if (!value) {
      setStatus("Введіть ключову фразу.");
      return;
    }
    send({ action: "add_keyword", value }, "Ключ надіслано боту.");
  });

  document.getElementById("removeKeywordButton").addEventListener("click", function () {
    const value = valueOf("removeKeywordInput");
    if (!value) {
      setStatus("Введіть ключ для видалення.");
      return;
    }
    send({ action: "remove_keyword", value }, "Запит на видалення надіслано.");
  });

  document.querySelectorAll("[data-country]").forEach(function (button) {
    button.addEventListener("click", function () {
      send(
        { action: "set_country", country: button.dataset.country },
        "Країну моніторингу надіслано боту."
      );
    });
  });

  document.getElementById("fulltextOnButton").addEventListener("click", function () {
    send({ action: "fulltext", enabled: true }, "Увімкнення повного тексту надіслано.");
  });

  document.getElementById("fulltextOffButton").addEventListener("click", function () {
    send({ action: "fulltext", enabled: false }, "Вимкнення повного тексту надіслано.");
  });

  document.querySelectorAll("[data-block]").forEach(function (button) {
    button.addEventListener("click", function () {
      send(
        {
          action: "tg_block",
          block: Number(button.dataset.block),
          enabled: button.dataset.enabled === "true"
        },
        "Запит на зміну TG-пакета надіслано."
      );
    });
  });

  document.getElementById("sourcesFileButton").addEventListener("click", function () {
    send({ action: "sources_file" }, "Бот надішле файл джерел у чат.");
  });

  document.getElementById("checkButton").addEventListener("click", function () {
    send({ action: "check" }, "Перевірку запущено в боті.");
  });

  document.getElementById("plansButton").addEventListener("click", function () {
    send({ action: "plans" }, "Бот надішле тарифи в чат.");
  });
})();
