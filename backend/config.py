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
    smtp_test_mail_from: str = ""
    # After direct MX :25 fails (common when VPS blocks outbound 25), relay via this host (587 + AUTH).
    smtp_outbound_relay_host: str = ""
    smtp_outbound_relay_port: int = 587
    smtp_outbound_relay_user: str = ""
    smtp_outbound_relay_password: str = ""
    smtp_outbound_relay_use_tls: bool = True
    # When False, FastAPI skips Base.metadata.create_all on startup (use with Alembic).
    metadata_create_all_on_startup: bool = True

settings = Settings()
