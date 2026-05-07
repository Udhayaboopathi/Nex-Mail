# MailOS — Self-Hosted Email Platform

**Product vision:** **[Nexudo Mail](docs/NEXUDO_MAIL_CONCEPT.md)** — multi-tenant email hosting, developer SMTP/API, and real-time infrastructure management (full concept and advanced specification).

Run `cp .env.example .env`, fill values, then `make build && make migrate && make seed`.

## Architecture

The technical stack and engineering principles for this repository (Next.js, FastAPI, PostgreSQL, Redis/Celery, Traefik, Docker, RBAC, async-first backend) are in **[docs/ARCHITECTURE.md](docs/ARCHITECTURE.md)**.


