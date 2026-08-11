# TicketPing MVP

Telegram bot and operator cabinet for monitoring cheap flight tickets, date alternatives, nearby airports, and future tour deals.

## Important security note

Never commit a Telegram bot token. Put the real token in `.env` only.

If a token was pasted into chat or logs, revoke it in BotFather and generate a new one.

## Quick start

```powershell
Copy-Item .env.example .env
.\run.ps1
```

Open:

```text
http://127.0.0.1:8017
```

Run the Telegram bot polling process separately:

```powershell
.\run_bot.ps1
```

Run the Ukrzaliznytsia monitor loop separately:

```powershell
.\run_rail_monitor.ps1
```

Or start the cabinet and bot launcher together:

```powershell
.\run_all.ps1
```

If `TELEGRAM_BOT_TOKEN` is empty, `run_all.ps1` starts only the cabinet.
If `RUN_RAIL_MONITOR=true`, the web process starts the UZ monitor loop on startup.

Set a new BotFather token without manually editing `.env`:

```powershell
.\set_bot_token.ps1 "1234567890:NEW_TOKEN_FROM_BOTFATHER"
```

## MVP scope

- Cabinet dashboard with users, searches, alerts, data sources, and tariff plans.
- SQLite storage for the first local MVP.
- Telegram bot entrypoint with a single `Кабінет` button that opens the Mini App.
- Telegram Mini App flow for flight search and Ukrzaliznytsia ticket watch requests.
- UZ watch storage for route/date/seat type/train number and Telegram alerts when matching seats appear.
- Multi-source flight search: Travelpayouts/Aviasales first, Kiwi/Tequila when `KIWI_TEQUILA_API_KEY` is set.
- Admin actions for source enable/disable, search pause/resume, and user plan changes.
- Source architecture prepared for Travelpayouts/Aviasales, Skyscanner, Kiwi/Tequila, and tour partners.

## Telegram Mini App

The Mini App is served at:

```text
/miniapp
```

Telegram requires a public HTTPS URL for WebApp buttons. Set it in `.env`:

```text
MINI_APP_URL=https://your-domain.example/miniapp
```

Without `MINI_APP_URL`, the bot shows only the `Кабінет` button but cannot open the Mini App from a phone.

## First product decision

The cabinet should exist from day one, but it should be operational, not bloated:

- see new Telegram users;
- see active searches;
- inspect latest alerts;
- disable broken sources;
- see source health;
- manage basic tariff limits.

User search creation should stay inside Telegram first. The web cabinet is for the operator/admin in MVP.
