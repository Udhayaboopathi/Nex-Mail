// ─── Auth ──────────────────────────────────────────────────────────────────
export type Role = "super_admin" | "domain_admin" | "user";

export interface TokenPayload {
  access_token: string;
  token_type: string;
  role?: Role;
  domain_id?: string;
}

// ─── User ──────────────────────────────────────────────────────────────────
export interface User {
  id: string;
  email: string;
  role: Role;
  is_active: boolean;
  created_at: string;
}

// ─── Domain ────────────────────────────────────────────────────────────────
export interface Domain {
  id: string;
  name: string;
  is_active: boolean;
  is_suspended: boolean;
  suspended_reason?: string;
  storage_quota_gb: number;
  used_storage_gb: number;
  dns_verified: boolean;
  dkim_selector: string;
  /** DNS TXT record name under the apex zone, e.g. mail._domainkey */
  dkim_dns_name?: string | null;
  /** Full TXT value: v=DKIM1; k=rsa; p=... */
  dkim_txt_record?: string | null;
  cloudflare_auto_dns: boolean;
  whitelabel_company_name?: string;
  whitelabel_primary_color: string;
  whitelabel_logo_url?: string;
  retention_days: number;
  ediscovery_enabled: boolean;
  admin_user_id?: string;
  created_at: string;
}

// ─── Mailbox ───────────────────────────────────────────────────────────────
export interface Mailbox {
  id: string;
  user_id: string;
  domain_id: string;
  local_part: string;
  display_name?: string | null;
  full_address: string;
  quota_mb: number;
  used_mb: number;
  is_active: boolean;
  last_login_at?: string;
  created_at: string;
}

// ─── Alias ─────────────────────────────────────────────────────────────────
export interface Alias {
  id: string;
  source_address: string;
  destination_address: string;
  domain_id: string;
  is_active: boolean;
  is_catch_all: boolean;
  created_at: string;
}

// ─── Email ─────────────────────────────────────────────────────────────────
export interface EmailHeader {
  uid: string;
  from: string;
  to: string[];
  subject: string;
  date: string;
  is_read: boolean;
  is_flagged: boolean;
  has_attachments: boolean;
  folder: string;
  preview: string;
  labels?: Label[];
  thread_id?: string;
}

export interface EmailFull extends EmailHeader {
  body_html?: string;
  body_text?: string;
  cc?: string[];
  bcc?: string[];
  reply_to?: string;
  message_id: string;
  attachments?: Attachment[];
  read_receipt_token?: string;
  is_pgp_encrypted?: boolean;
}

export interface Attachment {
  filename: string;
  content_type: string;
  size: number;
  url: string;
}

// ─── Thread ────────────────────────────────────────────────────────────────
export interface Thread {
  id: string;
  subject: string;
  participants: string[];
  last_message_at: string;
  message_count: number;
  has_unread: boolean;
  messages?: EmailFull[];
}

// ─── Label ─────────────────────────────────────────────────────────────────
export interface Label {
  id: string;
  name: string;
  color: string;
  mailbox_id: string;
  created_at: string;
}

// ─── Folder counts ─────────────────────────────────────────────────────────
export interface FolderInfo {
  name: string;
  unread: number;
  total: number;
}

// ─── Contact ───────────────────────────────────────────────────────────────
export interface Contact {
  id: string;
  email: string;
  name?: string;
  notes?: string;
  created_at: string;
}

// ─── Calendar ──────────────────────────────────────────────────────────────
export interface CalendarEvent {
  id: string;
  uid: string;
  title: string;
  description?: string;
  location?: string;
  start_at: string;
  end_at?: string;
  all_day: boolean;
  rrule?: string;
  attendees?: string[];
  linked_email_uid?: string;
  created_at: string;
}

// ─── Task ──────────────────────────────────────────────────────────────────
export interface Task {
  id: string;
  title: string;
  description?: string;
  due_at?: string;
  is_completed: boolean;
  completed_at?: string;
  priority: "low" | "normal" | "high";
  linked_email_uid?: string;
  created_at: string;
}

// ─── Note ──────────────────────────────────────────────────────────────────
export interface Note {
  id: string;
  title?: string;
  body: string;
  linked_email_uid?: string;
  created_at: string;
  updated_at: string;
}

// ─── Email Rule ────────────────────────────────────────────────────────────
export type ConditionField = "from" | "to" | "subject" | "body" | "has_attachment";
export type ConditionOp = "contains" | "not_contains" | "equals" | "starts_with";
export type ActionType = "move_to" | "label" | "mark_read" | "star" | "mark_spam" | "forward_to" | "auto_reply" | "delete";

export interface RuleCondition {
  field: ConditionField;
  op: ConditionOp;
  value: string;
}

export interface RuleAction {
  action: ActionType;
  value?: string;
}

export interface EmailRule {
  id: string;
  name: string;
  is_active: boolean;
  priority: number;
  match_type: "any" | "all";
  conditions: RuleCondition[];
  actions: RuleAction[];
  created_at: string;
}

// ─── Template ──────────────────────────────────────────────────────────────
export interface EmailTemplate {
  id: string;
  name: string;
  subject: string;
  body_html?: string;
  body_text?: string;
  created_at: string;
  updated_at: string;
}

// ─── Campaign ──────────────────────────────────────────────────────────────
export type CampaignStatus = "draft" | "scheduled" | "running" | "completed" | "failed";

export interface Campaign {
  id: string;
  name: string;
  subject: string;
  from_name: string;
  status: CampaignStatus;
  total_recipients: number;
  sent_count: number;
  open_count: number;
  click_count: number;
  unsubscribe_count: number;
  scheduled_at?: string;
  created_at: string;
}

// ─── Webhook ───────────────────────────────────────────────────────────────
export interface Webhook {
  id: string;
  url: string;
  events: string[];
  is_active: boolean;
  failure_count: number;
  last_triggered_at?: string;
  created_at: string;
}

// ─── API Key ───────────────────────────────────────────────────────────────
export interface ApiKey {
  id: string;
  name: string;
  key_prefix: string;
  scopes: string[];
  rate_limit_per_hour: number;
  expires_at?: string;
  last_used_at?: string;
  is_active: boolean;
  created_at: string;
  full_key?: string; // only on creation
}

// ─── Backup ────────────────────────────────────────────────────────────────
export type BackupStatus = "pending" | "running" | "done" | "failed";

export interface BackupJob {
  id: string;
  type: string;
  status: BackupStatus;
  file_size_mb?: number;
  total_messages?: number;
  error_message?: string;
  created_at: string;
  completed_at?: string;
}

// ─── DNS ───────────────────────────────────────────────────────────────────
export interface DnsRecord {
  type: string;
  name: string;
  value: string;
  valid: boolean;
  current?: string;
}

export interface DnsStatus {
  mx: DnsRecord;
  a: DnsRecord;
  spf: DnsRecord;
  dkim: DnsRecord;
  dmarc: DnsRecord;
  ptr?: string;
  all_valid: boolean;
}

// ─── Shared Mailbox ────────────────────────────────────────────────────────
export interface SharedMailbox {
  id: string;
  mailbox_id: string;
  display_name: string;
  members: SharedMailboxMember[];
  created_at: string;
}

export interface SharedMailboxMember {
  user_id: string;
  email: string;
  permission: "read_only" | "read_write";
  added_at: string;
}

// ─── Audit Log ────────────────────────────────────────────────────────────
export interface AuditLog {
  id: string;
  user_id?: string;
  action: string;
  target?: string;
  ip_address?: string;
  user_agent?: string;
  created_at: string;
}

// ─── Autoresponder ────────────────────────────────────────────────────────
export interface Autoresponder {
  id: string;
  is_enabled: boolean;
  subject: string;
  body: string;
  start_date?: string;
  end_date?: string;
  reply_once_per_sender: boolean;
}

// ─── Login Activity ───────────────────────────────────────────────────────
export interface LoginActivity {
  id: string;
  ip_address: string;
  user_agent: string;
  device_type: string;
  location?: string;
  success: boolean;
  failure_reason?: string;
  created_at: string;
}

// ─── Session ──────────────────────────────────────────────────────────────
export interface ActiveSession {
  id: string;
  ip_address: string;
  created_at: string;
  expires_at: string;
}

// ─── Paginated ────────────────────────────────────────────────────────────
export interface Paginated<T> {
  items: T[];
  total: number;
  page: number;
  limit: number;
}

// ─── Stats ────────────────────────────────────────────────────────────────
export interface SuperAdminStats {
  total_domains: number;
  active_domains: number;
  total_mailboxes: number;
  total_messages_today: number;
}

export interface DomainAdminStats {
  total_mailboxes: number;
  active_mailboxes: number;
  used_storage_gb: number;
  storage_quota_gb: number;
  messages_today: number;
}
