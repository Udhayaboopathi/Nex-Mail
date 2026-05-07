from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")
    domain: str = "localhost"
    acme_email: str = "admin@localhost"
    database_url: str
    redis_url: str
    jwt_secret_key: str
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 30
    refresh_token_expire_days: int = 30
    encryption_secret_key: str
    max_message_size_mb: int = 25
    maildir_base: str = "/var/mail"
    dkim_selector: str = "mail"
    server_ip: str = ""  # .env SERVER_IP — used when pushing mail A record to Cloudflare
    smtp_hostname: str = ""  # .env SMTP_HOSTNAME — MX/A host (default mail.<apex> if empty)
    # Optional: force all outbound DKIM signing to this domain (e.g. sudoinnovation.tech).
    dkim_signing_domain: str = ""
    cloudflare_api_token: str = ""
    backup_retention_days: int = 7
    backup_schedule_hour: int = 2
    frontend_url: str = "http://localhost:3000"
    invite_base_url: str = "http://localhost:3000"
    tracking_base_url: str = "http://localhost:8000/api/track"
    tracking_enabled: bool = True
    anthropic_api_key: str = ""
    super_admin_email: str = "admin@example.com"
    super_admin_password: str = "change-me"
    # Authenticated SMTP submission (port 587) for super-admin "test mail" — avoids blocked outbound :25.
    smtp_submission_host: str = ""
    smtp_submission_port: int = 587
    smtp_submission_user: str = ""
    smtp_submission_password: str = ""
    smtp_submission_use_tls: bool = True
    # TCP target for aiosmtplib (default: same as SMTP_SUBMISSION_HOST). Use 127.0.0.1 in Docker when
    # the public hostname does not hairpin to this container's :587 (avoids "Timed out waiting for server response").
    smtp_submission_connect_host: str = ""
    smtp_submission_tls_insecure: bool = False  # If True, skip TLS cert verification (e.g. IP vs cert name).
    smtp_test_mail_from: str = ""
    domain_branding_storage_dir: str = "/var/nexmail/domain-branding"
    domain_branding_public_base_url: str = ""
    # When False, FastAPI skips Base.metadata.create_all on startup (use with Alembic).
    metadata_create_all_on_startup: bool = True

settings = Settings()
