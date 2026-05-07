# Platform architecture

This document describes the **target production architecture** for **Nexudo Mail** / **MailOS**: a modern, self-hosted, production-grade SaaS-style platform with a microservice-inspired layout, a contemporary full-stack ecosystem, and containerized deployment.

For the full product concept (roles, SMTP/API platform, deliverability, DNS automation, backups, and deployment targets), see **[NEXUDO_MAIL_CONCEPT.md](./NEXUDO_MAIL_CONCEPT.md)**.

---

## Vision: unified developer-first platform

The application combines a highly interactive frontend, an async Python backend, scalable infrastructure, secure authentication, background job processing, and containerized deployment into a unified developer-first platform.

### Frontend

The frontend is built with **Next.js App Router** and **TypeScript**, using **Tailwind CSS** for a fast, responsive, and modern user experience. The interface supports **dark mode**, responsive layouts, **role-based dashboards**, dynamic forms, and real-time interactions. **Zustand** manages lightweight client-side state such as authentication and UI preferences, while **TanStack Query** handles API communication, caching, mutations, and synchronization with the backend. The UI layer is designed to align with **ShadCN UI** patterns (accessible, composable components on Tailwind + Radix-style primitives) wherever new surfaces are built or refactored. The frontend is optimized for production deployment with standalone builds, modular components, reusable UI patterns, and a scalable routing architecture.

### Backend

The backend is powered by **FastAPI** on **Python 3.12** using a **fully asynchronous** architecture for high performance and scalability. **SQLAlchemy 2.0** with **asyncpg** provides an async ORM layer connected to **PostgreSQL**, while **Alembic** manages database migrations and schema versioning. The API follows a **layered architecture** with routers, services, schemas, dependencies, and database models clearly separated for maintainability and extensibility. Authentication uses **JWT access and refresh tokens** with **bcrypt** password hashing, session tracking, **role-based authorization**, and secure token refresh workflows.

### Data, cache, and background work

**Redis** (or a Redis-compatible broker such as Valkey) acts as a high-speed cache and message broker for asynchronous processing. **Celery** workers handle long-running or background operations such as email delivery, scheduled tasks, cleanup jobs, notifications, analytics processing, report generation, and system maintenance workflows. A **Celery Beat** scheduler coordinates periodic jobs. The infrastructure is designed to scale horizontally by separating API services from workers and background schedulers.

### Edge routing and containers

**Traefik** serves as the reverse proxy and intelligent routing layer. It discovers Docker services through labels, routes frontend and backend traffic dynamically, and supports HTTPS-ready deployment (for example via ACME / Let’s Encrypt). **Docker** and **Docker Compose** orchestrate the environment: reproducible deployments, isolated networking, persistent volumes, health checks, restart policies, and simplified operations on VPS or cloud servers.

### Product and operations

The platform is a **multi-role** system supporting administrative and end-user workflows: secure account management, dashboards, API-driven operations, modular business logic, background automation, audit logging, analytics, and extensible integrations. Every layer aims for production readiness: secure authentication, rate limiting, async processing, validation, structured API responses, scalable infrastructure, and maintainable code organization.

The stack is **self-hosted** and independent of third-party platform lock-in: authentication, API services, job processing, data persistence, and frontend delivery run on infrastructure you control—scalability, security, deployment, customization, and cost remain yours to decide.

### Engineering principles

- Async-first backend architecture  
- Containerized infrastructure  
- Service-oriented code organization  
- Reusable frontend component system  
- Centralized API communication layer  
- Role-based access control  
- Production-grade security practices  
- Scalable queue-based processing  
- Automated deployment readiness  
- Infrastructure abstraction through Docker and Traefik  

Overall, the application is not only a website or dashboard: it is a **complete production-ready platform** capable of evolving into a large-scale SaaS ecosystem with modular services, extensible APIs, advanced automation, and enterprise-level deployment patterns.

---

## How this maps to **this** repository

| Area | In this repo |
|------|----------------|
| Next.js App Router, TypeScript, Tailwind | `frontend/` |
| Zustand, TanStack Query | Declared in `frontend/package.json` |
| ShadCN UI | Optional adoption path; current UI uses Tailwind + custom/shared components—new work can standardize on ShadCN |
| FastAPI, Python 3.12 | `backend/`, `backend/Dockerfile` |
| SQLAlchemy 2 async, asyncpg, Alembic | `backend/`, migrations under `backend/alembic` |
| PostgreSQL | `postgres` service in `docker-compose.yml` |
| Redis / broker | `redis` service (Valkey image) in `docker-compose.yml` |
| Celery worker + Beat | `worker` and `beat` services in `docker-compose.yml` |
| Traefik, TLS routing | `traefik/` + service labels in `docker-compose.yml` |
| JWT, bcrypt, RBAC | `backend/api`, `backend/core`, domain/super-admin routes |
| Mail transport | **aiosmtpd** (inbound :25, submission :587), **aiosmtplib** (outbound to recipients’ MX :25), **IMAP** (:993), Maildir storage, per-domain DKIM in DB, **SpamAssassin** + **ClamAV** services |

---

## Current feature set (this repository)

Grouped by area; aligns UI (`frontend/app`), API routers under `backend/api/routers/`, and `backend/tasks/`.

### Mail infrastructure

- Inbound SMTP (MTA) and authenticated submission on **587** (STARTTLS); **IMAP** for mailbox sync.
- Messages stored as **Maildir**; outbound delivery via **direct MX** (port 25) with DKIM when keys exist for the From domain.
- Integration with **SpamAssassin** and **ClamAV** for content/spam scanning on delivery paths that use them.

### Authentication and security

- **JWT** access tokens, **refresh** tokens, **bcrypt** passwords.
- **TOTP / 2FA** (setup, enable, disable, verify), **sessions** list and revoke.
- **Password reset** (request + confirm), **domain invite** acceptance.
- **Login activity** history; **rate limiting** (SlowAPI / client IP).
- **Audit logging** middleware for API actions; encrypted secrets for sensitive fields (e.g. Cloudflare, API key material).

### Super Admin

- **Domains**: create, update, delete, suspend / unsuspend, assign domain admin (welcome mail path).
- **DNS**: verification and copy/paste guides; DKIM/SPF-style guidance via domain records.
- **Platform backup** jobs (full backup), list and audit exposure.
- **SMTP test** from Settings (submission to this host).
- **Audit logs** (super-admin scope).

### Domain Admin

- **Mailboxes** CRUD, password reset, per-mailbox activity.
- **Aliases** CRUD.
- **DNS**: status, manual verify, **Cloudflare auto-DNS** when token configured.
- **Backup / restore** at domain level; backup job download.
- **Whitelabel** and **retention** policies.
- **eDiscovery** admin routes (search/export scaffolding and export downloads).
- **Audit logs** for the domain.
- **Stats** and onboarding helpers.

### End-user mail and productivity

- **Folders** (system + labels), **threads** and messages by folder, **mail search**.
- **Labels**, **rules**, **templates**, **autoresponder** (settings).
- **Contacts**, **calendar**, **tasks**, **notes**.
- **Mail compose** / read UI under `mail/`.
- **PGP** key generate, own key, lookup by email.
- **Spam reporting** API.
- **Shared mailboxes** and **delegation** (grant/revoke).

### Campaigns, webhooks, API, tracking

- **Campaigns**: list/create/update/delete, **send**, **analytics** endpoint.
- **Webhooks**: CRUD and **test** hook.
- **API keys**: create with **scopes** and **per-hour rate limit**; hashed storage.
- **HTTP send queue**: `POST /api/v1/send` enqueues **Celery** `deliver_email` (retries with backoff). *Harden this route with API-key or mutual-auth before exposing publicly.*
- **Open / click tracking** via `/api/track` pixel and redirect routes (when tracking enabled).

### AI (optional)

- **Priority inbox**, **summarize**, **smart reply**, **suggest labels** when `ANTHROPIC_API_KEY` (or related config) is set.

### Background jobs (Celery)

Queues include **default**, **email**, **backup**, **ai** (see `docker-compose.yml` worker command). Task modules cover **delivery**, **campaigns**, **backups**, **retention**, **storage alerts**, **scheduled email**, **AI**, **cleanup**, etc.

### Frontend surfaces (App Router)

- Auth: login, forgot/reset password, invite.
- Mail: inbox, folder views, message view, offline page, unsubscribe landing.
- Settings: profile/security, labels, rules, templates, autoresponder, webhooks, API keys.
- Domain admin: dashboard, mailboxes, aliases, DNS, backup, whitelabel, retention, eDiscovery, shared mailboxes, audit.
- Super admin: dashboard, domains, settings (mail test), audit logs.
- Calendar, tasks, notes.

---

When documentation and code diverge, use this section together with the code as the source of truth; the **[NEXUDO_MAIL_CONCEPT.md](./NEXUDO_MAIL_CONCEPT.md)** doc describes the **full product vision** (including mail daemons like Postfix/Dovecot where the repo still uses the Python mail stack). Track incremental refactors in issues or `DEPLOY.md`.
