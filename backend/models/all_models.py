from __future__ import annotations

import uuid
from datetime import date, datetime

from sqlalchemy import Boolean, Date, DateTime, Float, ForeignKey, Integer, PrimaryKeyConstraint, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import ARRAY, INET, JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from backend.models.base import Base
from backend.models.mixins import CreatedAtMixin, CreatedUpdatedMixin, UUIDPrimaryKeyMixin

class User(Base, UUIDPrimaryKeyMixin, CreatedUpdatedMixin):
    __tablename__ = "users"
    email: Mapped[str] = mapped_column(String(319), unique=True, nullable=False)
    hashed_password: Mapped[str] = mapped_column(Text, nullable=False)
    role: Mapped[str] = mapped_column(String(20), nullable=False, server_default="user")
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default="true")

class Domain(Base, UUIDPrimaryKeyMixin, CreatedAtMixin):
    __tablename__ = "domains"
    name: Mapped[str] = mapped_column(String, unique=True, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default="true")
    is_suspended: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default="false")
    suspended_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    suspended_reason: Mapped[str | None] = mapped_column(Text)
    storage_quota_gb: Mapped[int] = mapped_column(Integer, nullable=False, server_default="10")
    used_storage_gb: Mapped[float] = mapped_column(Float, nullable=False, server_default="0")
    cloudflare_token_encrypted: Mapped[str | None] = mapped_column(Text)
    cloudflare_zone_id: Mapped[str | None] = mapped_column(String(64))
    cloudflare_auto_dns: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default="false")
    dns_verified: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default="false")
    dns_verified_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    dkim_private_key_encrypted: Mapped[str | None] = mapped_column(Text)
    dkim_selector: Mapped[str] = mapped_column(String(63), nullable=False, server_default="mail")
    allow_custom_dkim_signing: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default="false")
    spf_record: Mapped[str | None] = mapped_column(Text)
    dmarc_record: Mapped[str | None] = mapped_column(Text)
    admin_user_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"))
    whitelabel_logo_url: Mapped[str | None] = mapped_column(Text)
    bimi_vmc_url: Mapped[str | None] = mapped_column(Text)
    whitelabel_primary_color: Mapped[str] = mapped_column(String(7), nullable=False, server_default="#6366f1")
    whitelabel_company_name: Mapped[str | None] = mapped_column(String(100))
    retention_days: Mapped[int] = mapped_column(Integer, nullable=False, server_default="0")
    ediscovery_enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default="false")

class DomainInvite(Base, UUIDPrimaryKeyMixin, CreatedAtMixin):
    __tablename__ = "domain_invites"
    domain_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("domains.id", ondelete="CASCADE"), nullable=False)
    email: Mapped[str] = mapped_column(String, nullable=False)
    token: Mapped[str | None] = mapped_column(String(128), unique=True)
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    accepted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

class Mailbox(Base, UUIDPrimaryKeyMixin, CreatedAtMixin):
    __tablename__ = "mailboxes"
    __table_args__ = (UniqueConstraint("local_part", "domain_id", name="uq_mailboxes_local_part_domain_id"),)
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    domain_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("domains.id", ondelete="CASCADE"), nullable=False)
    local_part: Mapped[str] = mapped_column(String(64), nullable=False)
    display_name: Mapped[str | None] = mapped_column(String(200))
    full_address: Mapped[str] = mapped_column(String(319), unique=True, nullable=False)
    quota_mb: Mapped[int] = mapped_column(Integer, nullable=False, server_default="1024")
    used_mb: Mapped[float] = mapped_column(Float, nullable=False, server_default="0")
    maildir_path: Mapped[str | None] = mapped_column(Text)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default="true")
    last_login_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

class Alias(Base, UUIDPrimaryKeyMixin, CreatedAtMixin):
    __tablename__ = "aliases"
    source_address: Mapped[str | None] = mapped_column(String, unique=True)
    destination_address: Mapped[str | None] = mapped_column(String)
    domain_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("domains.id", ondelete="CASCADE"), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default="true")
    is_catch_all: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default="false")

class Session(Base, UUIDPrimaryKeyMixin, CreatedAtMixin):
    __tablename__ = "sessions"
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    refresh_token_hash: Mapped[str | None] = mapped_column(Text)
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    ip_address: Mapped[str | None] = mapped_column(INET)

class AuditLog(Base, UUIDPrimaryKeyMixin, CreatedAtMixin):
    __tablename__ = "audit_logs"
    user_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"))
    action: Mapped[str | None] = mapped_column(String(100))
    target: Mapped[str | None] = mapped_column(Text)
    ip_address: Mapped[str | None] = mapped_column(INET)
    user_agent: Mapped[str | None] = mapped_column(Text)

class LoginActivity(Base, UUIDPrimaryKeyMixin, CreatedAtMixin):
    __tablename__ = "login_activity"
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    ip_address: Mapped[str | None] = mapped_column(INET)
    user_agent: Mapped[str | None] = mapped_column(Text)
    device_type: Mapped[str | None] = mapped_column(String(20))
    location: Mapped[str | None] = mapped_column(Text)
    success: Mapped[bool | None] = mapped_column(Boolean)
    failure_reason: Mapped[str | None] = mapped_column(Text)

class PasswordResetToken(Base, UUIDPrimaryKeyMixin, CreatedAtMixin):
    __tablename__ = "password_reset_tokens"
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    token: Mapped[str | None] = mapped_column(String(128), unique=True)
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    used_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

class TotpSecret(Base, UUIDPrimaryKeyMixin, CreatedAtMixin):
    __tablename__ = "totp_secrets"
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), unique=True, nullable=False)
    secret: Mapped[str | None] = mapped_column(Text)
    is_enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default="false")
    backup_codes: Mapped[list[str]] = mapped_column(ARRAY(Text), nullable=False, server_default="{}")

class PgpKey(Base, UUIDPrimaryKeyMixin, CreatedAtMixin):
    __tablename__ = "pgp_keys"
    mailbox_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("mailboxes.id", ondelete="CASCADE"), unique=True, nullable=False)
    public_key: Mapped[str | None] = mapped_column(Text)
    private_key_encrypted: Mapped[str | None] = mapped_column(Text)
    fingerprint: Mapped[str | None] = mapped_column(String(40), unique=True)
    is_enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default="false")

class ApiKey(Base, UUIDPrimaryKeyMixin, CreatedAtMixin):
    __tablename__ = "api_keys"
    mailbox_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("mailboxes.id", ondelete="CASCADE"), nullable=False)
    domain_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("domains.id", ondelete="CASCADE"), nullable=False)
    name: Mapped[str | None] = mapped_column(String(100))
    key_hash: Mapped[str | None] = mapped_column(Text, unique=True)
    key_prefix: Mapped[str | None] = mapped_column(String(8))
    scopes: Mapped[list[str]] = mapped_column(ARRAY(Text), nullable=False, server_default="{send}")
    rate_limit_per_hour: Mapped[int] = mapped_column(Integer, nullable=False, server_default="1000")
    last_used_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default="true")

class BackupJob(Base, UUIDPrimaryKeyMixin, CreatedAtMixin):
    __tablename__ = "backup_jobs"
    type: Mapped[str | None] = mapped_column(String(20))
    status: Mapped[str | None] = mapped_column(String(20))
    domain_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("domains.id", ondelete="SET NULL"))
    mailbox_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("mailboxes.id", ondelete="SET NULL"))
    file_path: Mapped[str | None] = mapped_column(Text)
    file_size_mb: Mapped[float | None] = mapped_column(Float)
    total_messages: Mapped[int | None] = mapped_column(Integer)
    error_message: Mapped[str | None] = mapped_column(Text)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

class EmailThread(Base, UUIDPrimaryKeyMixin, CreatedAtMixin):
    __tablename__ = "email_threads"
    mailbox_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("mailboxes.id", ondelete="CASCADE"), nullable=False)
    subject: Mapped[str | None] = mapped_column(String)
    participants: Mapped[list[str] | None] = mapped_column(ARRAY(Text))
    last_message_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    message_count: Mapped[int] = mapped_column(Integer, nullable=False, server_default="1")
    has_unread: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default="true")

class Email(Base, UUIDPrimaryKeyMixin, CreatedAtMixin):
    __tablename__ = "emails"
    mailbox_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("mailboxes.id", ondelete="CASCADE"), nullable=False)
    folder: Mapped[str] = mapped_column(String(50), nullable=False, server_default="inbox")
    from_address: Mapped[str | None] = mapped_column(String(319))
    to_addresses: Mapped[list[str]] = mapped_column(ARRAY(Text), nullable=False, server_default="{}")
    cc_addresses: Mapped[list[str]] = mapped_column(ARRAY(Text), nullable=False, server_default="{}")
    bcc_addresses: Mapped[list[str]] = mapped_column(ARRAY(Text), nullable=False, server_default="{}")
    subject: Mapped[str | None] = mapped_column(String)
    body_text: Mapped[str | None] = mapped_column(Text)
    body_html: Mapped[str | None] = mapped_column(Text)
    message_id: Mapped[str | None] = mapped_column(String(255))
    flags: Mapped[list[str]] = mapped_column(ARRAY(Text), nullable=False, server_default="{}")
    is_read: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default="false")
    is_flagged: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default="false")
    has_attachments: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default="false")
    headers: Mapped[dict] = mapped_column(JSONB, nullable=False, server_default="{}")
    sent_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

class Label(Base, UUIDPrimaryKeyMixin, CreatedAtMixin):
    __tablename__ = "labels"
    __table_args__ = (UniqueConstraint("mailbox_id", "name", name="uq_labels_mailbox_id_name"),)
    mailbox_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("mailboxes.id", ondelete="CASCADE"), nullable=False)
    name: Mapped[str | None] = mapped_column(String(50))
    color: Mapped[str] = mapped_column(String(7), nullable=False, server_default="#6366f1")

class EmailLabel(Base):
    __tablename__ = "email_labels"
    __table_args__ = (PrimaryKeyConstraint("email_uid", "label_id", name="pk_email_labels"),)
    email_uid: Mapped[str] = mapped_column(String(50), nullable=False)
    label_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("labels.id", ondelete="CASCADE"), nullable=False)
    mailbox_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("mailboxes.id", ondelete="CASCADE"), nullable=False)

class EmailRule(Base, UUIDPrimaryKeyMixin, CreatedAtMixin):
    __tablename__ = "email_rules"
    mailbox_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("mailboxes.id", ondelete="CASCADE"), nullable=False)
    name: Mapped[str | None] = mapped_column(String(100))
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default="true")
    priority: Mapped[int] = mapped_column(Integer, nullable=False, server_default="0")
    match_type: Mapped[str] = mapped_column(String(10), nullable=False, server_default="any")
    conditions: Mapped[dict] = mapped_column(JSONB, nullable=False, server_default="[]")
    actions: Mapped[dict] = mapped_column(JSONB, nullable=False, server_default="[]")

class EmailTemplate(Base, UUIDPrimaryKeyMixin, CreatedUpdatedMixin):
    __tablename__ = "email_templates"
    mailbox_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("mailboxes.id", ondelete="CASCADE"), nullable=False)
    name: Mapped[str | None] = mapped_column(String(100))
    subject: Mapped[str | None] = mapped_column(String)
    body_text: Mapped[str | None] = mapped_column(Text)
    body_html: Mapped[str | None] = mapped_column(Text)

class ReadReceipt(Base, UUIDPrimaryKeyMixin, CreatedAtMixin):
    __tablename__ = "read_receipts"
    sender_mailbox_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("mailboxes.id", ondelete="CASCADE"), nullable=False)
    message_id: Mapped[str | None] = mapped_column(String)
    recipient_email: Mapped[str | None] = mapped_column(String)
    opened_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    open_count: Mapped[int] = mapped_column(Integer, nullable=False, server_default="0")
    ip_address: Mapped[str | None] = mapped_column(INET)
    user_agent: Mapped[str | None] = mapped_column(Text)

class TrackingPixel(Base, UUIDPrimaryKeyMixin, CreatedAtMixin):
    __tablename__ = "email_tracking_pixels"
    read_receipt_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("read_receipts.id", ondelete="CASCADE"), nullable=False)
    token: Mapped[str | None] = mapped_column(String(64), unique=True)

class LinkClick(Base, UUIDPrimaryKeyMixin):
    __tablename__ = "email_link_clicks"
    read_receipt_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("read_receipts.id", ondelete="CASCADE"), nullable=False)
    original_url: Mapped[str | None] = mapped_column(Text)
    tracking_token: Mapped[str | None] = mapped_column(String(64), unique=True)
    click_count: Mapped[int] = mapped_column(Integer, nullable=False, server_default="0")
    first_clicked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    last_clicked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

class UnsubscribeToken(Base, UUIDPrimaryKeyMixin, CreatedAtMixin):
    __tablename__ = "unsubscribe_tokens"
    __table_args__ = (UniqueConstraint("sender_mailbox_id", "recipient_email", name="uq_unsub_tokens_sender_recipient"),)
    sender_mailbox_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("mailboxes.id", ondelete="CASCADE"), nullable=False)
    recipient_email: Mapped[str | None] = mapped_column(String)
    token: Mapped[str | None] = mapped_column(String(64), unique=True)
    unsubscribed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

class UnsubscribeList(Base):
    __tablename__ = "unsubscribe_list"
    __table_args__ = (PrimaryKeyConstraint("sender_mailbox_id", "recipient_email", name="pk_unsubscribe_list"),)
    sender_mailbox_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("mailboxes.id", ondelete="CASCADE"), nullable=False)
    recipient_email: Mapped[str] = mapped_column(String, nullable=False)
    unsubscribed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default="now()")

class Webhook(Base, UUIDPrimaryKeyMixin, CreatedAtMixin):
    __tablename__ = "webhooks"
    mailbox_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("mailboxes.id", ondelete="CASCADE"), nullable=False)
    url: Mapped[str | None] = mapped_column(Text)
    secret: Mapped[str | None] = mapped_column(String(64))
    events: Mapped[list[str]] = mapped_column(ARRAY(Text), nullable=False, server_default="{receive,send}")
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default="true")
    last_triggered_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    failure_count: Mapped[int] = mapped_column(Integer, nullable=False, server_default="0")

class Campaign(Base, UUIDPrimaryKeyMixin, CreatedAtMixin):
    __tablename__ = "campaign_emails"
    mailbox_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("mailboxes.id", ondelete="CASCADE"), nullable=False)
    name: Mapped[str | None] = mapped_column(String(100))
    subject: Mapped[str | None] = mapped_column(String)
    body_html: Mapped[str | None] = mapped_column(Text)
    body_text: Mapped[str | None] = mapped_column(Text)
    from_name: Mapped[str | None] = mapped_column(String(100))
    recipients: Mapped[dict] = mapped_column(JSONB, nullable=False, server_default="[]")
    status: Mapped[str] = mapped_column(String(20), nullable=False, server_default="draft")
    scheduled_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    total_recipients: Mapped[int] = mapped_column(Integer, nullable=False, server_default="0")
    sent_count: Mapped[int] = mapped_column(Integer, nullable=False, server_default="0")
    failed_count: Mapped[int] = mapped_column(Integer, nullable=False, server_default="0")
    open_count: Mapped[int] = mapped_column(Integer, nullable=False, server_default="0")
    click_count: Mapped[int] = mapped_column(Integer, nullable=False, server_default="0")
    unsubscribe_count: Mapped[int] = mapped_column(Integer, nullable=False, server_default="0")

class Autoresponder(Base, UUIDPrimaryKeyMixin, CreatedUpdatedMixin):
    __tablename__ = "autoresponders"
    mailbox_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("mailboxes.id", ondelete="CASCADE"), unique=True, nullable=False)
    is_enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default="false")
    subject: Mapped[str] = mapped_column(String, nullable=False, server_default="Out of Office")
    body: Mapped[str | None] = mapped_column(Text)
    start_date: Mapped[date | None] = mapped_column(Date)
    end_date: Mapped[date | None] = mapped_column(Date)
    reply_once_per_sender: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default="true")

class AutoresponderSent(Base, UUIDPrimaryKeyMixin):
    __tablename__ = "autoresponder_sent"
    autoresponder_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("autoresponders.id", ondelete="CASCADE"), nullable=False)
    sent_to: Mapped[str | None] = mapped_column(String)
    sent_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default="now()")

class ScheduledEmail(Base, UUIDPrimaryKeyMixin, CreatedAtMixin):
    __tablename__ = "scheduled_emails"
    mailbox_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("mailboxes.id", ondelete="CASCADE"), nullable=False)
    send_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    to_addresses: Mapped[list[str] | None] = mapped_column(ARRAY(Text))
    cc_addresses: Mapped[list[str]] = mapped_column(ARRAY(Text), nullable=False, server_default="{}")
    bcc_addresses: Mapped[list[str]] = mapped_column(ARRAY(Text), nullable=False, server_default="{}")
    subject: Mapped[str | None] = mapped_column(String)
    body_text: Mapped[str | None] = mapped_column(Text)
    body_html: Mapped[str | None] = mapped_column(Text)
    attachments: Mapped[dict] = mapped_column(JSONB, nullable=False, server_default="[]")
    status: Mapped[str] = mapped_column(String(20), nullable=False, server_default="pending")
    error_message: Mapped[str | None] = mapped_column(Text)

class Contact(Base, UUIDPrimaryKeyMixin, CreatedAtMixin):
    __tablename__ = "contacts"
    __table_args__ = (UniqueConstraint("user_id", "email", name="uq_contacts_user_email"),)
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    email: Mapped[str | None] = mapped_column(String)
    name: Mapped[str | None] = mapped_column(String)
    notes: Mapped[str | None] = mapped_column(Text)

class CalendarEvent(Base, UUIDPrimaryKeyMixin, CreatedUpdatedMixin):
    __tablename__ = "calendar_events"
    mailbox_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("mailboxes.id", ondelete="CASCADE"), nullable=False)
    uid: Mapped[str | None] = mapped_column(String, unique=True)
    title: Mapped[str | None] = mapped_column(String)
    description: Mapped[str | None] = mapped_column(Text)
    location: Mapped[str | None] = mapped_column(String)
    start_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    end_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    all_day: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default="false")
    rrule: Mapped[str | None] = mapped_column(Text)
    attendees: Mapped[dict] = mapped_column(JSONB, nullable=False, server_default="[]")
    linked_email_uid: Mapped[str | None] = mapped_column(String)

class Task(Base, UUIDPrimaryKeyMixin, CreatedUpdatedMixin):
    __tablename__ = "tasks"
    mailbox_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("mailboxes.id", ondelete="CASCADE"), nullable=False)
    title: Mapped[str | None] = mapped_column(String)
    description: Mapped[str | None] = mapped_column(Text)
    due_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    is_completed: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default="false")
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    priority: Mapped[str] = mapped_column(String(10), nullable=False, server_default="normal")
    linked_email_uid: Mapped[str | None] = mapped_column(String)

class Note(Base, UUIDPrimaryKeyMixin, CreatedUpdatedMixin):
    __tablename__ = "notes"
    mailbox_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("mailboxes.id", ondelete="CASCADE"), nullable=False)
    title: Mapped[str | None] = mapped_column(String)
    body: Mapped[str | None] = mapped_column(Text)
    linked_email_uid: Mapped[str | None] = mapped_column(String)

class SharedMailbox(Base, UUIDPrimaryKeyMixin, CreatedAtMixin):
    __tablename__ = "shared_mailboxes"
    mailbox_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("mailboxes.id", ondelete="CASCADE"), unique=True, nullable=False)
    domain_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("domains.id", ondelete="CASCADE"), nullable=False)
    display_name: Mapped[str | None] = mapped_column(String(100))

class SharedMailboxMember(Base):
    __tablename__ = "shared_mailbox_members"
    __table_args__ = (PrimaryKeyConstraint("shared_mailbox_id", "user_id", name="pk_shared_mailbox_members"),)
    shared_mailbox_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("shared_mailboxes.id", ondelete="CASCADE"), nullable=False)
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    permission: Mapped[str] = mapped_column(String(20), nullable=False, server_default="read_write")
    added_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

class Delegation(Base, UUIDPrimaryKeyMixin, CreatedAtMixin):
    __tablename__ = "mailbox_delegations"
    __table_args__ = (UniqueConstraint("owner_mailbox_id", "delegate_user_id", name="uq_mailbox_delegate_owner_user"),)
    owner_mailbox_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("mailboxes.id", ondelete="CASCADE"), nullable=False)
    delegate_user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    permission: Mapped[str] = mapped_column(String(20), nullable=False, server_default="send_on_behalf")

class SpamReport(Base, UUIDPrimaryKeyMixin, CreatedAtMixin):
    __tablename__ = "spam_reports"
    mailbox_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("mailboxes.id", ondelete="CASCADE"), nullable=False)
    email_uid: Mapped[str | None] = mapped_column(String)
    from_address: Mapped[str | None] = mapped_column(String)
    report_type: Mapped[str | None] = mapped_column(String(10))

class EdiscoveryExport(Base, UUIDPrimaryKeyMixin, CreatedAtMixin):
    __tablename__ = "ediscovery_exports"
    domain_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("domains.id", ondelete="CASCADE"), nullable=False)
    requested_by: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"))
    query: Mapped[dict | None] = mapped_column(JSONB)
    status: Mapped[str] = mapped_column(String(20), nullable=False, server_default="pending")
    file_path: Mapped[str | None] = mapped_column(Text)
    total_messages: Mapped[int] = mapped_column(Integer, nullable=False, server_default="0")
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
