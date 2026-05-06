# Nex Mail — VPS Preparation & DNS Configuration Guide

> **Target:** Ubuntu 24.04 LTS, 2 vCPU / 4 GB RAM minimum (4 vCPU / 8 GB recommended)

---

## Table of Contents

1. [VPS Initial Setup](#1-vps-initial-setup)
2. [Firewall & Ports](#2-firewall--ports)
3. [Docker & Docker Compose](#3-docker--docker-compose)
4. [Clone & Configure the Project](#4-clone--configure-the-project)
5. [DNS Records](#5-dns-records)
6. [TLS Certificates](#6-tls-certificates)
7. [DKIM Key Setup](#7-dkim-key-setup)
8. [Database Migrations](#8-database-migrations)
9. [Seeding the Super-Admin Account](#9-seeding-the-super-admin-account)
10. [Starting All Services](#10-starting-all-services)
11. [Smoke Tests](#11-smoke-tests)
12. [Ongoing Maintenance](#12-ongoing-maintenance)
13. [Troubleshooting](#13-troubleshooting)

---

## 1. VPS Initial Setup

```bash
# Log in as root, then create a deploy user
adduser deploy
usermod -aG sudo deploy
su - deploy

# Update the system
sudo apt update && sudo apt upgrade -y
sudo apt install -y git curl wget unzip ufw fail2ban

# Set the server hostname — must match your mail domain
sudo hostnamectl set-hostname mail.yourdomain.com

# Update /etc/hosts
echo "127.0.0.1  mail.yourdomain.com" | sudo tee -a /etc/hosts
```

### Harden SSH (optional but recommended)

```bash
# In /etc/ssh/sshd_config set:
#   PermitRootLogin no
#   PasswordAuthentication no   # only if you have SSH keys set up
sudo systemctl restart ssh
```

---

## 2. Firewall & Ports

```bash
sudo ufw default deny incoming
sudo ufw default allow outgoing

# SSH
sudo ufw allow 22/tcp

# HTTP / HTTPS (Traefik)
sudo ufw allow 80/tcp
sudo ufw allow 443/tcp

# SMTP
sudo ufw allow 25/tcp      # inbound mail from other servers
sudo ufw allow 587/tcp     # submission (authenticated clients)
sudo ufw allow 465/tcp     # SMTPS (optional)

# IMAP
sudo ufw allow 143/tcp     # IMAP
sudo ufw allow 993/tcp     # IMAPS

sudo ufw enable
sudo ufw status verbose
```

> **Cloud provider note:** If your VPS is on AWS/GCP/Azure/Hetzner, also open the same ports in the cloud-level security group / firewall console.

---

## 3. Docker & Docker Compose

```bash
# Install Docker Engine (official script)
curl -fsSL https://get.docker.com | sudo bash

# Add deploy user to the docker group
sudo usermod -aG docker deploy
newgrp docker

# Verify
docker version
docker compose version    # v2+ ships as a plugin
```

---

## 4. Clone & Configure the Project

```bash
cd /opt
sudo git clone https://github.com/your-org/email-server.git nexmail
sudo chown -R deploy:deploy /opt/nexmail
cd /opt/nexmail
```

### Create `.env`

Copy the example and fill in every value:

```bash
cp .env.example .env
nano .env
```

**Minimum required values:**

```dotenv
# ── Core ──────────────────────────────────────────────────────────────
DOMAIN=yourdomain.com
ACME_EMAIL=admin@yourdomain.com

# ── Database ──────────────────────────────────────────────────────────
POSTGRES_DB=nexmail
POSTGRES_USER=nexmail
POSTGRES_PASSWORD=CHANGE_ME_STRONG_PASSWORD

DATABASE_URL=postgresql+asyncpg://nexmail:CHANGE_ME_STRONG_PASSWORD@db:5432/nexmail

# ── Redis ─────────────────────────────────────────────────────────────
REDIS_URL=redis://redis:6379/0

# ── Security ──────────────────────────────────────────────────────────
JWT_SECRET_KEY=at-least-64-random-chars
ENCRYPTION_SECRET_KEY=exactly-32-bytes-base64url-here=

# ── Super Admin ───────────────────────────────────────────────────────
SUPER_ADMIN_EMAIL=admin@yourdomain.com
SUPER_ADMIN_PASSWORD=CHANGE_ME_SUPER_ADMIN_PASSWORD

# ── Mail ──────────────────────────────────────────────────────────────
MAILDIR_BASE=/var/mail
DKIM_SELECTOR=mail
MAX_MESSAGE_SIZE_MB=25

# ── Frontend ──────────────────────────────────────────────────────────
FRONTEND_URL=https://mail.yourdomain.com
INVITE_BASE_URL=https://mail.yourdomain.com
TRACKING_BASE_URL=https://mail.yourdomain.com/api/track

# ── Optional ──────────────────────────────────────────────────────────
ANTHROPIC_API_KEY=             # leave blank to disable AI features
CLOUDFLARE_API_TOKEN=          # leave blank if not using Cloudflare auto-DNS

# ── Traefik dashboard basic auth ──────────────────────────────────────
# Generate: echo $(htpasswd -nB admin) | sed -e s/\\$/\\$\\$/g
TRAEFIK_DASHBOARD_AUTH=admin:$$2y$$05$$...
```

Generate strong secrets:

```bash
# JWT secret (64+ random bytes)
openssl rand -hex 64

# Encryption key (32 bytes → 44-char base64)
openssl rand -base64 32
```

---

## 5. DNS Records

Log in to your domain registrar / DNS provider and add **all** of the following records.

Replace `1.2.3.4` with your VPS's public IPv4 address.

### 5.1 Basic Records

| Type | Name | Value | TTL |
|------|------|-------|-----|
| `A` | `@` (root domain) | `1.2.3.4` | 300 |
| `A` | `mail` | `1.2.3.4` | 300 |
| `MX` | `@` | `mail.yourdomain.com` (priority 10) | 300 |

> The MX record **must** point to the A record hostname, not the bare IP.

### 5.2 Reverse DNS (PTR)

Set the **rDNS / PTR** record for your VPS IP in your hosting provider's control panel:

```
1.2.3.4  →  mail.yourdomain.com
```

Most spam filters reject mail from IPs with no matching PTR record.

### 5.3 SPF Record

| Type | Name | Value |
|------|------|-------|
| `TXT` | `@` | `v=spf1 mx a:mail.yourdomain.com ~all` |

The `~all` softfail is a safe starting point.  Change to `-all` once you are sure no other servers send on your behalf.

### 5.4 DKIM Record

DKIM keys are created when you **add a domain** in the super-admin UI (or when calling `POST /api/super-admin/domains`). Each domain has its own key pair; the **private** key stays in the database (encrypted).

**Get the TXT record (recommended — super-admin API)**

```bash
# 1) Log in and set TOKEN (JSON access_token)
TOKEN=$(curl -s -X POST https://mail.yourdomain.com/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"YOUR_SUPER_ADMIN_EMAIL","password":"YOUR_PASSWORD"}' \
  | jq -r '.access_token')

# 2) List domains — each item includes dkim_dns_name and dkim_txt_record
curl -s -H "Authorization: Bearer $TOKEN" \
  https://mail.yourdomain.com/api/super-admin/domains | jq .

# 3) Example: print DKIM for the first domain
curl -s -H "Authorization: Bearer $TOKEN" \
  https://mail.yourdomain.com/api/super-admin/domains \
  | jq '.[0] | {name, dkim_selector, dkim_dns_name, dkim_txt_record}'
```

**Or inside the backend container** (derive TXT from the DB):

```bash
docker compose exec backend python -c "
import asyncio
from sqlalchemy import select
from backend.database import AsyncSessionLocal
from backend.models import Domain
from backend.services.domain_service import build_dkim_txt_record, dkim_txt_dns_name

async def main():
    async with AsyncSessionLocal() as db:
        d = (await db.execute(select(Domain).order_by(Domain.created_at).limit(1))).scalar_one_or_none()
        if not d:
            print('No domain')
            return
        print('Zone:', d.name)
        print('TXT name (under zone):', dkim_txt_dns_name(d))
        print('TXT value:', build_dkim_txt_record(d))

asyncio.run(main())
"
```

Add the DKIM TXT record at your DNS host (for the **mail domain’s zone**, e.g. `yourdomain.com`):

| Type | Name | Value |
|------|------|-------|
| `TXT` | `mail._domainkey` | paste `dkim_txt_record` from the API (starts with `v=DKIM1; k=rsa; p=`…) |

> Replace `mail` with `dkim_dns_name` from the API if you changed `DKIM_SELECTOR` in `.env` (default is `mail`).

**Cloudflare token in “Assign domain admin”**

Storing a Cloudflare API token only **resolves the zone ID** and sets `cloudflare_auto_dns` in the app. **This project does not yet push MX/SPF/DKIM/DMARC records to the Cloudflare API automatically** — you (or a future automation step) still create those records in the Cloudflare DNS UI (or API). Use **DNS Setup** / **Verify DNS** in the admin UI and the values from `GET /api/super-admin/domains/{id}/dns/guide` as needed.

### 5.5 DMARC Record

| Type | Name | Value |
|------|------|-------|
| `TXT` | `_dmarc` | `v=DMARC1; p=quarantine; rua=mailto:dmarc@yourdomain.com; pct=100` |

Start with `p=quarantine`.  Once mail flow is confirmed, switch to `p=reject`.

### 5.6 Full DNS Checklist

```
✅  A       yourdomain.com          → 1.2.3.4
✅  A       mail.yourdomain.com     → 1.2.3.4
✅  MX      yourdomain.com          → mail.yourdomain.com  (pri 10)
✅  PTR     1.2.3.4                 → mail.yourdomain.com  (set at VPS provider)
✅  TXT     yourdomain.com          → v=spf1 mx a:mail.yourdomain.com ~all
✅  TXT     mail._domainkey         → v=DKIM1; k=rsa; p=<KEY>
✅  TXT     _dmarc.yourdomain.com   → v=DMARC1; p=quarantine; rua=mailto:dmarc@yourdomain.com
```

Verify with online tools:
- SPF: [mxtoolbox.com/spf.aspx](https://mxtoolbox.com/spf.aspx)
- DKIM: [dkimcore.org/tools/](https://dkimcore.org/tools/)
- DMARC: [dmarcanalyzer.com](https://www.dmarcanalyzer.com/dmarc/dmarc-record-check/)
- Blacklist check: [mxtoolbox.com/blacklists.aspx](https://mxtoolbox.com/blacklists.aspx)

---

## 6. TLS Certificates

### 6.1 Traefik auto-TLS (HTTPS for the web UI & REST API)

Traefik handles this automatically via Let's Encrypt ACME when it detects Docker containers with the correct labels.  No manual action is needed — **just make sure port 80 and 443 are open** and DNS is pointing to the VPS.

The certificate is stored in `traefik/acme.json` (mounted volume).

### 6.2 SMTP / IMAP TLS (Certbot)

SMTP and IMAP use separate certificates from Let's Encrypt via Certbot:

```bash
sudo apt install -y certbot

# Obtain certificate (standalone mode — stop any existing port-80 service first)
sudo certbot certonly --standalone \
  -d mail.yourdomain.com \
  --email admin@yourdomain.com \
  --agree-tos \
  --non-interactive

# Certificates will be at:
#   /etc/letsencrypt/live/mail.yourdomain.com/fullchain.pem
#   /etc/letsencrypt/live/mail.yourdomain.com/privkey.pem

# Set up auto-renewal
sudo systemctl enable certbot.timer
sudo systemctl start certbot.timer

# Test renewal
sudo certbot renew --dry-run
```

> The `docker-compose.yml` mounts `/etc/letsencrypt` read-only into the SMTP and IMAP containers.

---

## 7. DKIM Key Setup

DKIM keys are generated when you **create** a domain via the super-admin UI or `POST /api/super-admin/domains` (older builds that inserted an empty domain row had no key — recreate the domain or restore keys from backup).

**Verify a key exists and copy the TXT record:**

```bash
# Connect to the DB and check
docker compose exec db psql -U nexmail -c \
  "SELECT name, dkim_selector, LEFT(dkim_private_key_encrypted, 20) AS key_preview FROM domains;"
```

**Or use the API** — each domain includes `dkim_dns_name` and `dkim_txt_record` (see §5.4).

Create the domain if needed:

```bash
TOKEN=$(curl -s -X POST https://mail.yourdomain.com/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"admin@yourdomain.com","password":"YOUR_SUPER_ADMIN_PASSWORD"}' \
  | jq -r '.access_token')

curl -s -X POST https://mail.yourdomain.com/api/super-admin/domains \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"name":"yourdomain.com"}'
```

---

## 8. Database Migrations

```bash
cd /opt/nexmail

# Run the initial migration (creates all tables)
docker compose run --rm backend alembic upgrade head

# Verify
docker compose exec db psql -U nexmail -c "\dt"
```

Expected output: a list of ~30+ tables including `users`, `domains`, `mailboxes`, `emails`, etc.

---

## 9. Seeding the Super-Admin Account

```bash
docker compose run --rm backend python -m backend.seed
```

This creates the super-admin user using `SUPER_ADMIN_EMAIL` and `SUPER_ADMIN_PASSWORD` from `.env`.  The script is idempotent — safe to run multiple times.

---

## 10. Starting All Services

```bash
cd /opt/nexmail

# Pull/build images and start detached
docker compose pull
docker compose build
docker compose up -d

# Check all containers are running
docker compose ps

# Tail logs
docker compose logs -f --tail=50
```

### Expected running services

| Container | Role |
|-----------|------|
| `traefik` | Reverse proxy + TLS termination |
| `frontend` | Next.js web UI |
| `backend` | FastAPI REST + SMTP + IMAP |
| `db` | PostgreSQL 16 |
| `redis` | Celery broker & cache |
| `worker` | Celery background worker |
| `beat` | Celery periodic scheduler |
| `spamassassin` | Spam scoring daemon |
| `clamav` | Antivirus scanner |
| `fail2ban` | Brute-force protection |

---

## 11. Smoke Tests

### Web UI
Open `https://mail.yourdomain.com` in a browser — you should see the Nex Mail login page with a valid TLS certificate.

### REST API
```bash
# Health check
curl -s https://mail.yourdomain.com/health
# Expected: {"status":"ok"}

# Login
curl -s -X POST https://mail.yourdomain.com/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"admin@yourdomain.com","password":"YOUR_PASSWORD"}' | jq .
```

### SMTP (send a test email)
```bash
sudo apt install -y swaks
swaks --to test@gmail.com \
      --from admin@yourdomain.com \
      --server mail.yourdomain.com \
      --port 587 \
      --auth LOGIN \
      --auth-user admin@yourdomain.com \
      --auth-password YOUR_PASSWORD \
      --tls
```

### IMAP
```bash
sudo apt install -y curl
curl -v imaps://mail.yourdomain.com \
     --user "admin@yourdomain.com:YOUR_PASSWORD"
```

### DNS Verification via API
```bash
TOKEN=<access token from login>
curl -s -H "Authorization: Bearer $TOKEN" \
  "https://mail.yourdomain.com/api/super-admin/domains/<domain-id>/verify-dns" | jq .
```

---

## 12. Ongoing Maintenance

### Backup
```bash
# Manual DB dump
docker compose exec db pg_dump -U nexmail nexmail | gzip > /opt/backups/nexmail_$(date +%F).sql.gz
```

Automated backups run nightly via the Celery beat schedule (configured in `backend/tasks/backup_tasks.py`).

### Certificate renewal
Certbot auto-renews via systemd timer.  Traefik auto-renews its own cert.

### Update the application
```bash
cd /opt/nexmail
git pull
docker compose build backend frontend
docker compose up -d
docker compose run --rm backend alembic upgrade head
```

### Monitoring
- Traefik dashboard: `https://traefik.yourdomain.com` (protected by basic auth)
- Container logs: `docker compose logs -f <service>`
- DB size: `docker compose exec db psql -U nexmail -c "SELECT pg_size_pretty(pg_database_size('nexmail'));"`

---

## 13. Troubleshooting

### Port 25 blocked by VPS provider
Many cloud providers block port 25 by default.  Submit a ticket requesting it be unblocked, or use a relay service (Mailgun, AWS SES, Postmark) and configure `SMTP_RELAY_HOST` in `.env`.

### Let's Encrypt rate limits
If you exceed Let's Encrypt's rate limits during testing, use the staging environment:
```bash
certbot certonly --staging ...
```

### Alembic migration fails
```bash
# Check the DB URL is reachable
docker compose exec backend python -c "
import asyncio
from backend.database import AsyncSessionLocal
async def test():
    async with AsyncSessionLocal() as db:
        print(await db.execute('SELECT 1'))
asyncio.run(test())
"
```

### Emails going to spam
1. Check SPF, DKIM, DMARC are all passing: `swaks` with `--server mail.yourdomain.com` then check return headers.
2. Verify rDNS/PTR record matches your hostname.
3. Check blacklists: [mxtoolbox.com/blacklists.aspx](https://mxtoolbox.com/blacklists.aspx)
4. Warm up IP gradually — don't send bulk mail on day 1.

### TOTP / 2FA locked out
```bash
# Disable TOTP for a user directly in DB
docker compose exec db psql -U nexmail -c \
  "UPDATE totp_secrets SET is_enabled = false WHERE user_id = (SELECT id FROM users WHERE email = 'you@yourdomain.com');"
```

---

*Generated for Nex Mail — self-hosted email platform.*
