# Monitorio multi-product repository

This branch keeps three related products in one Git repository:

- **Monitorio** — the media monitoring bot and Mini App in the repository root.
- **MonitorioTicket** — the travel and ticket monitoring service in `MonitorioTicket/`.
- **MonitorioRent** — the rental monitoring product in `MonitorioRent/`.

Each product has its own dependencies, configuration examples, and startup
instructions. Real tokens, `.env` files, databases, logs, and virtual
environments must stay outside Git.

The shared integration branch is `monitorio_mult`.

