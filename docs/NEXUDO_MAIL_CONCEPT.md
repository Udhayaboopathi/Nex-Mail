# Nexudo Mail — Application concept

**Nexudo Mail** is the product vision for this project: a production-grade, multi-tenant email infrastructure and communication platform for organizations, developers, and businesses that want full control over their email ecosystem **without** relying on third-party SMTP providers such as Gmail, AWS SES, Brevo, SendGrid, or Mailgun.

> **This repository:** The codebase evolves toward this vision. Today’s implementation uses a Python-centric mail stack (e.g. async SMTP/IMAP in the backend service, SpamAssassin, ClamAV) plus FastAPI, PostgreSQL, Redis, Celery, Traefik, and Docker—see [ARCHITECTURE.md](./ARCHITECTURE.md) for the current technical map. Sections below that reference Postfix, Dovecot, Rspamd, or docker-mailserver describe the **target** mail infrastructure layer unless otherwise noted.

The platform combines three major systems into one unified product:

1. **Enterprise email hosting platform**
2. **Developer SMTP/API email service**
3. **Real-time email infrastructure management system**

Nexudo Mail is designed as a scalable SaaS platform where a single infrastructure can host multiple organizations, multiple domains, and thousands of mailboxes while maintaining strict tenant isolation, advanced security, and high deliverability.

### Current capabilities in this codebase

The following is implemented today (Next.js frontend, FastAPI backend, Docker). **Full detail:** [ARCHITECTURE.md](./ARCHITECTURE.md) § *Current feature set*.

- **Mail:** Inbound SMTP and submission (**587**), **IMAP** (**993**), Maildir storage, DKIM from DB keys, outbound **direct MX**, SpamAssassin + ClamAV integration.
- **Auth:** JWT + refresh, bcrypt, TOTP/2FA, sessions, password reset, invites, login activity; API rate limiting and audit middleware.
- **Super Admin:** Domains (CRUD, suspend, assign admin), DNS verify/guides, full backups, audit logs, SMTP submission test.
- **Domain Admin:** Mailboxes and aliases, DNS status/verify and Cloudflare automation, domain backup/restore, whitelabel, retention, eDiscovery admin flows, audit logs, stats.
- **Users:** Threads, folders, labels, rules, templates, contacts, calendar, tasks, notes, search, PGP helpers, spam reports, shared mailboxes, delegation.
- **Developers / ops:** Campaigns (send + analytics), webhooks, API keys (scopes + hourly limits), `POST /api/v1/send` → Celery delivery with retries, open/click tracking.
- **AI (optional):** Priority inbox, summarize, smart reply, label suggestions when configured.
- **Jobs:** Celery workers + Beat (email delivery, backups, campaigns, retention, cleanup, AI, scheduled mail, alerts).

Everything below in this document remains the **product and architecture vision**, including components (Postfix, Dovecot, Rspamd, WebSocket dashboards, reputation engine, sandbox SMTP, PgBouncer) that are **targets** or **partial** relative to the current tree.

---

## Core vision

The goal of Nexudo Mail is to provide a self-hosted, fully controlled email platform that offers:

- Complete ownership of mail infrastructure
- High deliverability
- Real-time monitoring and analytics
- Developer-friendly SMTP/API integrations
- Enterprise-grade administration
- Modern webmail experience

Unlike traditional mail hosting systems, Nexudo Mail is not only a mailbox provider but also a **programmable email infrastructure platform** capable of handling transactional email, marketing campaigns, automation workflows, inbound email parsing, and developer integrations.

---

## System architecture

Nexudo Mail is built using a layered architecture.

### 1. Mail infrastructure layer

This layer handles actual email delivery and mailbox management using industry-standard mail components.

**Technologies:**

- Postfix (SMTP server)
- Dovecot (IMAP/POP3 server)
- Rspamd (spam filtering and DKIM)
- Maildir storage
- TLS encryption

**Responsibilities:**

- Sending and receiving emails
- DKIM signing
- IMAP mailbox access
- Spam filtering
- SMTP authentication
- Mail storage management

This layer ensures RFC-compliant mail delivery and production-grade reliability.

### 2. Backend control plane

The backend acts as the centralized orchestration system.

**Technology stack:**

- FastAPI
- PostgreSQL
- Redis
- Celery workers

**Responsibilities:**

- Domain management
- Mailbox provisioning
- SMTP API system
- User management
- Role-based access control
- Rate limiting
- Backup and restore
- Analytics and monitoring
- DNS automation
- Webhook processing

The backend does not replace the mail server. Instead, it acts as a secure SaaS management layer around the mail infrastructure.

### 3. Frontend platform

The frontend provides a unified modern interface for all user roles.

**Technology stack:**

- Next.js
- Tailwind CSS
- Responsive UI

The frontend dynamically renders features based on user roles.

---

## Role-based access system

Nexudo Mail uses a hierarchical multi-tenant permission model.

### Super Admin

The Super Admin has complete control over the platform.

**Capabilities:**

- Create and manage domains
- Assign storage quotas per domain
- Configure DNS automation
- Suspend domains
- View platform analytics
- Manage SMTP infrastructure
- Export/import complete platform backups

The Super Admin acts as the infrastructure owner.

### Domain Admin

Domain Admins manage a single domain or organization.

**Capabilities:**

- Create and manage mailboxes
- Assign mailbox storage limits
- Generate SMTP API keys
- Manage campaigns
- Configure rules and filters
- View domain-level analytics
- Backup/import domain data

This role is designed for businesses or organizations using the platform.

### User

Users access only their personal mailbox and communication tools.

**Capabilities:**

- Send and receive emails
- Use labels and folders
- Create filters and rules
- Access templates
- Use webmail interface
- Manage contacts
- Access mailbox analytics

---

## SMTP developer platform

One of the most advanced components of Nexudo Mail is the developer-focused SMTP and API system.

The platform allows external applications to send emails using either:

- Standard SMTP credentials
- API-key-based SMTP authentication
- REST API endpoints

**Example SMTP configuration:**

```env
SMTP_HOST=mail.nexudo.dev
SMTP_PORT=587
SMTP_USERNAME=apikey
SMTP_PASSWORD=nexudo_sk_live_xxx
```

**Example API endpoint:**

```http
POST /api/v1/send-email
```

**Capabilities include:**

- Transactional email delivery
- Template-based email sending
- Sandbox testing mode
- Webhooks
- Delivery tracking
- Bounce management
- SMTP logs
- Rate limiting
- API key permissions

This transforms Nexudo Mail from a standard mail server into a programmable email delivery platform.

---

## Real-time infrastructure layer

Redis is used as a real-time processing engine.

**Responsibilities:**

- Rate limiting
- Queue tracking
- Live metrics
- Event streaming
- WebSocket updates
- Retry queue management
- Job tracking

The frontend receives real-time updates for:

- Emails per second
- Delivery status
- Queue size
- Failures
- Domain reputation

---

## Security model

Security is a major focus of the platform.

**Features:**

- JWT authentication
- bcrypt password hashing
- TLS encryption
- Fail2Ban protection
- DKIM signing
- SPF and DMARC support
- API key permissions
- Domain isolation
- Brute-force protection
- Login activity tracking

Sensitive values such as Cloudflare tokens, API keys, and encryption secrets are stored encrypted and never exposed to clients.

---

## DNS automation

Nexudo Mail supports automated DNS configuration using Cloudflare APIs.

When a new domain is added:

- MX records are generated
- SPF records are configured
- DKIM keys are created
- DMARC records are added

This drastically simplifies onboarding for organizations.

---

## Backup and recovery system

The platform includes enterprise-grade backup and import/export systems.

**Supported backup levels:**

- Full platform backup
- Domain backup
- Mailbox backup

**Backups include:**

- Database records
- Mail files
- DKIM keys
- Mailbox metadata

The restore system supports:

- Merge mode
- Overwrite mode

---

## Advanced features (vision + current code)

Nexudo Mail is intended to include enterprise and developer-oriented capabilities. The list below mixes **what the codebase already provides** (see [ARCHITECTURE.md](./ARCHITECTURE.md)) with **roadmap / extended platform** behavior.

**Present in this repository (partial or full):**

- SMTP API key management (UI + storage; secure the public send endpoint for production)
- Per-IP API rate limiting (SlowAPI); per-key hourly limits on keys
- Campaign sending system and basic analytics endpoint
- Email templates (user/domain flows)
- Webhooks (register, update, test)
- Queue retry engine (Celery delivery retries)
- Email rules engine, labels and tags, folders
- Audit logs (super-admin and domain-admin surfaces)
- Open/click tracking (when enabled)
- Backup and restore jobs (platform and domain scope)
- DNS automation (Cloudflare) and verification guides

**Vision / roadmap (not fully realized as described in later sections):**

- Real-time SMTP metrics and live dashboards (WebSocket)
- Priority mail queues and transactional vs bulk queue separation as first-class ops tools
- Sandbox SMTP mode
- Deep delivery analytics and inbox-placement telemetry
- Domain reputation scoring and automatic throttling from bounces/complaints
- Internal organization messaging as a dedicated product slice
- Fail2Ban and other host-level hardening (operational, outside app code)
- Postfix/Dovecot/Rspamd/docker-mailserver parity with the concept doc’s mail layer

---

## Deployment model

The platform is fully containerized using Docker and Docker Compose.

**Infrastructure includes:**

- Traefik reverse proxy
- Automatic TLS certificates
- PostgreSQL with PgBouncer
- Redis
- Celery workers
- docker-mailserver

The system is designed for:

- VPS deployment
- Horizontal scaling
- Secure production operation

---

## Final vision (foundation)

Nexudo Mail is not just an email client or a basic mail server.

It is a fully controlled email infrastructure platform that combines:

- Enterprise email hosting
- Developer SMTP services
- Real-time infrastructure monitoring
- Automation capabilities
- Multi-tenant SaaS architecture

into one unified system.

The platform aims to provide the flexibility of self-hosting with the capabilities of modern cloud email providers while maintaining complete ownership of infrastructure, data, and delivery systems.

---

# Nexudo Mail — Advanced application concept

Nexudo Mail is a production-grade, multi-tenant email infrastructure platform designed to provide complete ownership and control over email hosting, SMTP delivery, developer integrations, and real-time email operations without relying on external email providers such as Gmail, AWS SES, SendGrid, Mailgun, or Brevo.

The platform combines enterprise email hosting, developer SMTP APIs, real-time infrastructure monitoring, automation systems, and domain orchestration into one unified SaaS ecosystem.

Nexudo Mail is designed to function as:

- Enterprise email hosting platform
- Developer SMTP/API service
- Real-time email infrastructure platform
- Multi-tenant SaaS system
- Email automation and campaign engine

---

## Core vision (extended)

The primary goal of Nexudo Mail is to provide organizations and developers with a fully self-controlled email ecosystem capable of handling:

- Transactional email
- Marketing campaigns
- Internal communication
- Mailbox hosting
- Developer integrations
- Automation workflows
- Real-time monitoring

while maintaining:

- High deliverability
- Advanced security
- Infrastructure ownership
- Scalable architecture
- Enterprise-grade management

Unlike traditional mail hosting systems, Nexudo Mail is not only a mailbox provider but also a **programmable email infrastructure layer** capable of supporting modern application ecosystems.

---

## Multi-layer architecture

Nexudo Mail is built using a distributed service-oriented architecture.

### 1. Mail infrastructure layer

This layer is responsible for actual email transport and mailbox management.

**Technologies:**

- Postfix (SMTP)
- Dovecot (IMAP/POP3)
- Rspamd (spam filtering + DKIM)
- Maildir storage
- TLS encryption

**Responsibilities:**

- Sending and receiving emails
- DKIM signing
- IMAP access
- Mailbox storage
- Spam filtering
- SMTP relay handling
- Mail queue processing

This layer provides RFC-compliant mail delivery and enterprise-grade reliability.

### 2. Backend control plane

The backend acts as the orchestration engine of the platform.

**Technology stack:**

- FastAPI
- PostgreSQL
- Redis
- Celery

**Responsibilities:**

- Domain management
- Mailbox provisioning
- SMTP API management
- Authentication
- RBAC
- Analytics
- Backup systems
- Webhook processing
- DNS automation
- Quota management
- Queue monitoring
- API key generation

The backend controls infrastructure behavior while the mail server handles mail transport.

### 3. Frontend platform

The frontend provides a modern role-based interface.

**Technology stack:**

- Next.js
- Tailwind CSS
- WebSocket-based real-time updates

The frontend dynamically changes based on user roles.

---

## Role-based access system (extended)

Nexudo Mail implements hierarchical multi-tenant RBAC.

### Super Admin (extended)

The Super Admin acts as the infrastructure owner.

**Capabilities:**

- Create and manage domains
- Assign total domain storage
- Configure DNS automation
- Manage mail infrastructure
- Monitor SMTP queues
- Monitor deliverability
- Manage backups
- Suspend domains
- Transfer domains between organizations
- Configure system-wide policies

The Super Admin can onboard unlimited domains and organizations.

### Domain Admin (extended)

The Domain Admin manages a specific domain or organization.

**Capabilities:**

- Create mailboxes
- Assign mailbox quotas
- Generate SMTP API keys
- Manage campaigns
- Configure rules and filters
- Configure branding
- Backup/import domain data
- Manage webhooks
- Monitor analytics

### User (extended)

Users access personal mailbox features.

**Capabilities:**

- Send and receive emails
- Labels and folders
- Templates
- Rules and filters
- Contacts
- Mailbox search
- Email tracking
- Campaign tools

---

## Advanced domain automation system

One of the most powerful features of Nexudo Mail is automated DNS orchestration.

When a Super Admin adds a new domain:

1. The system requests an optional Cloudflare API token.
2. The token is encrypted and stored securely in the database.
3. Nexudo Mail automatically:

   - Creates MX records
   - Configures SPF
   - Generates DKIM keys
   - Creates DKIM TXT records
   - Creates DMARC records
   - Configures autoconfig/autodiscover records

This enables near one-click email infrastructure onboarding.

The system also validates:

- DNS propagation
- MX availability
- SPF correctness
- DKIM validation
- DMARC policy health

The dashboard displays real-time DNS health indicators.

---

## Smart deliverability system

Nexudo Mail includes a deliverability intelligence engine.

The platform tracks:

- Bounce rate
- Complaint rate
- Spam reports
- Delivery latency
- Inbox placement

Each domain receives a dynamic reputation score.

The reputation system automatically:

- Throttles suspicious domains
- Limits abusive senders
- Isolates risky traffic
- Protects shared IP reputation

This significantly improves deliverability and prevents spam abuse.

---

## Developer SMTP and API platform (extended)

Nexudo Mail provides both SMTP relay and REST APIs for developers.

**Example SMTP configuration:**

```env
SMTP_HOST=mail.nexudo.dev
SMTP_PORT=587
SMTP_USERNAME=apikey
SMTP_PASSWORD=nexudo_sk_live_xxx
```

**Example API:**

```http
POST /api/v1/send-email
```

**Capabilities:**

- Transactional email
- Marketing campaigns
- Template rendering
- Sandbox mode
- Webhooks
- Delivery tracking
- Open/click tracking
- Retry handling
- SMTP logs
- API key permissions

API keys support granular scopes such as:

- Send
- Logs
- Analytics
- Webhooks

---

## SMTP infrastructure engine

Nexudo Mail implements a production-grade SMTP processing pipeline.

**Flow:**

Request → API key validation → sender verification → recipient validation → Redis rate limiting → queue assignment → Postfix delivery → Rspamd filtering → DKIM signing → delivery tracking → webhook dispatch

The system supports:

- Transactional queues
- Bulk campaign queues
- Retry queues
- High-priority queues

---

## Real-time infrastructure monitoring

Redis acts as the real-time processing engine.

**Responsibilities:**

- Queue tracking
- Rate limiting
- Event streaming
- Metrics
- Live dashboards
- Retry scheduling

The dashboard displays:

- Emails/sec
- Delivery success
- Bounce rate
- SMTP latency
- Active queues
- Active SMTP sessions

All updates are delivered in real-time using WebSockets.

---

## SMTP API key system

Nexudo Mail supports advanced SMTP authentication using API keys.

**Flow:**

1. Domain Admin generates SMTP key.
2. Backend creates `nexudo_sk_live_xxx` (example format).
3. Key is hashed and stored securely.
4. User receives credentials:

```env
SMTP_HOST=mail.nexudo.dev
SMTP_PORT=587
SMTP_USERNAME=apikey
SMTP_PASSWORD=nexudo_sk_live_xxx
```

This allows secure SMTP access without exposing mailbox passwords.

---

## Intelligent rate limiting

The platform uses Redis-based dynamic rate limiting.

Limits are applied per:

- Mailbox
- API key
- Domain
- IP address

Rate limits automatically adjust based on:

- Reputation score
- Bounce rate
- Complaint history

---

## Backup and disaster recovery (extended)

Nexudo Mail supports enterprise-grade backup management.

**Backup levels:**

- Full platform
- Organization
- Domain
- Mailbox

**Backups include:**

- Database data
- Maildir files
- DKIM keys
- Rules and filters
- SMTP API keys
- Analytics metadata

**Import supports:**

- Merge mode
- Overwrite mode
- Selective mailbox restore

---

## Real-time queue and SMTP monitoring

Administrators can view:

- Active SMTP sessions
- Queued emails
- Retry queues
- Bounce queues
- Deferred mail

The system includes:

- Queue retry tools
- Forced re-delivery
- Stuck queue cleanup

This provides operational visibility similar to enterprise mail platforms.

---

## Security architecture (extended)

Security is deeply integrated into the platform.

**Features:**

- JWT authentication
- Refresh tokens
- bcrypt hashing
- TLS encryption
- DKIM/SPF/DMARC
- Fail2Ban
- Audit logs
- Encrypted secrets
- IP/device login tracking
- Brute-force protection

Sensitive data such as Cloudflare tokens, API keys, and encryption secrets are encrypted and never exposed to frontend clients.

---

## Deployment architecture (extended)

The platform is fully containerized.

**Infrastructure:**

- Docker
- Docker Compose
- Traefik
- PostgreSQL + PgBouncer
- Redis
- Celery workers
- docker-mailserver

**Domains (example):**

- `nexudo.dev` → frontend
- `api.nexudo.dev` → backend
- `mail.nexudo.dev` → SMTP/IMAP

Traefik automatically provisions TLS certificates using Let’s Encrypt.

---

## Final vision (advanced)

Nexudo Mail is not merely a mail server or webmail client.

It is a complete programmable email infrastructure ecosystem combining:

- Enterprise email hosting
- Developer SMTP services
- Automated DNS orchestration
- Real-time infrastructure monitoring
- Deliverability intelligence
- Automation systems
- Scalable SaaS architecture

into a single production-grade platform fully controlled by its owner.

The platform aims to provide the flexibility and ownership of self-hosting while delivering capabilities comparable to modern cloud email providers and developer-focused email infrastructure platforms.
