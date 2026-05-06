import { authHeaders } from "./auth";
import type {
  TokenPayload, Domain, Mailbox, Alias, EmailHeader, EmailFull,
  Label, Contact, CalendarEvent, Task, Note, EmailRule, EmailTemplate,
  Campaign, Webhook, ApiKey, BackupJob, DnsStatus, Autoresponder,
  LoginActivity, ActiveSession, Paginated, SuperAdminStats,
  DomainAdminStats, AuditLog, SharedMailbox,
} from "../types";

const BASE = process.env.NEXT_PUBLIC_API_URL ?? "";

async function request<T>(
  method: string,
  path: string,
  body?: unknown,
  extraHeaders?: HeadersInit
): Promise<T> {
  const res = await fetch(`${BASE}${path}`, {
    method,
    headers: {
      "Content-Type": "application/json",
      ...authHeaders(),
      ...extraHeaders,
    },
    body: body !== undefined ? JSON.stringify(body) : undefined,
  });
  if (!res.ok) {
    const text = await res.text();
    let msg = `HTTP ${res.status}`;
    const ct = res.headers.get("content-type") ?? "";
    if (ct.includes("application/json")) {
      try { msg = JSON.parse(text).detail ?? msg; } catch { /* ignore */ }
    } else if (!ct.includes("text/html")) {
      msg = text || msg;
    }
    // Map common status codes to human-readable messages
    if (res.status === 401) msg = "Invalid email or password.";
    else if (res.status === 403) msg = "Access denied.";
    else if (res.status === 404) msg = "Service not found — is the backend running?";
    else if (res.status === 429) msg = "Too many attempts. Please wait and try again.";
    else if (res.status >= 500) msg = "Server error. Please try again later.";
    throw new Error(msg);
  }
  const ct = res.headers.get("content-type") ?? "";
  if (ct.includes("application/json")) return res.json() as Promise<T>;
  return res.text() as unknown as T;
}

const get = <T>(p: string) => request<T>("GET", p);
const post = <T>(p: string, b?: unknown) => request<T>("POST", p, b);
const patch = <T>(p: string, b?: unknown) => request<T>("PATCH", p, b);
const put = <T>(p: string, b?: unknown) => request<T>("PUT", p, b);
const del = <T>(p: string) => request<T>("DELETE", p);

// ─── Auth ──────────────────────────────────────────────────────────────────
export const authApi = {
  login: (email: string, password: string) =>
    post<TokenPayload>("/api/auth/login", { email, password }),
  logout: () => post("/api/auth/logout"),
  requestPasswordReset: (email: string) =>
    post("/api/auth/password-reset/request", { email }),
  confirmPasswordReset: (token: string, password: string) =>
    post("/api/auth/password-reset/confirm", { token, password }),
  setupTotp: () => post<{ secret: string; qr_uri: string; backup_codes: string[] }>("/api/auth/totp/setup"),
  enableTotp: (code: string) => post("/api/auth/totp/enable", { code }),
  disableTotp: (password: string) => post("/api/auth/totp/disable", { password }),
  verifyTotp: (temp_token: string, code: string) =>
    post<TokenPayload>("/api/auth/totp/verify", { temp_token, code }),
  getLoginActivity: () => get<LoginActivity[]>("/api/auth/login-activity"),
  getSessions: () => get<ActiveSession[]>("/api/auth/sessions"),
  deleteSession: (id: string) => del(`/api/auth/sessions/${id}`),
  acceptInvite: (token: string, password: string) =>
    post<TokenPayload>("/api/auth/accept-invite", { token, password }),
};

// ─── Super Admin ──────────────────────────────────────────────────────────
export const superAdminApi = {
  getStats: () => get<SuperAdminStats>("/api/super-admin/stats"),
  getDomains: () => get<Domain[]>("/api/super-admin/domains"),
  createDomain: (name: string) => post<Domain>("/api/super-admin/domains", { name }),
  updateDomain: (id: string, data: Partial<Domain>) =>
    patch<Domain>(`/api/super-admin/domains/${id}`, data),
  deleteDomain: (id: string) => del(`/api/super-admin/domains/${id}`),
  assignAdmin: (id: string, email: string) =>
    post(`/api/super-admin/domains/${id}/assign-admin`, { email }),
  suspendDomain: (id: string, reason: string) =>
    post(`/api/super-admin/domains/${id}/suspend`, { reason }),
  unsuspendDomain: (id: string) =>
    post(`/api/super-admin/domains/${id}/unsuspend`),
  verifyDns: (id: string) => post<DnsStatus>(`/api/super-admin/domains/${id}/dns/verify`),
  getDnsGuide: (id: string) => get(`/api/super-admin/domains/${id}/dns/guide`),
  getAuditLogs: (p = 1) => get<Paginated<AuditLog>>(`/api/super-admin/audit-logs?page=${p}`),
  triggerFullBackup: () => post<{ job_id: string }>("/api/super-admin/backup/full"),
  getBackups: () => get<BackupJob[]>("/api/super-admin/backups"),
};

// ─── Domain Admin ─────────────────────────────────────────────────────────
export const domainAdminApi = {
  getStats: () => get<DomainAdminStats>("/api/domain-admin/stats"),
  getOnboarding: () => get("/api/domain-admin/onboarding"),
  getMailboxes: (search = "", page = 1) =>
    get<Paginated<Mailbox>>(`/api/domain-admin/mailboxes?search=${encodeURIComponent(search)}&page=${page}`),
  createMailbox: (data: { local_part: string; password: string; quota_mb?: number }) =>
    post<Mailbox>("/api/domain-admin/mailboxes", data),
  updateMailbox: (id: string, data: Partial<Mailbox>) =>
    patch<Mailbox>(`/api/domain-admin/mailboxes/${id}`, data),
  deleteMailbox: (id: string) => del(`/api/domain-admin/mailboxes/${id}`),
  resetMailboxPassword: (id: string, password: string) =>
    post(`/api/domain-admin/mailboxes/${id}/reset-password`, { password }),
  getAliases: () => get<Alias[]>("/api/domain-admin/aliases"),
  createAlias: (data: { source_address: string; destination_address: string; is_catch_all?: boolean }) =>
    post<Alias>("/api/domain-admin/aliases", data),
  updateAlias: (id: string, data: Partial<Alias>) =>
    patch<Alias>(`/api/domain-admin/aliases/${id}`, data),
  deleteAlias: (id: string) => del(`/api/domain-admin/aliases/${id}`),
  getDnsStatus: () => get<DnsStatus>("/api/domain-admin/dns/status"),
  getDnsGuide: () => get("/api/domain-admin/dns/guide"),
  verifyDns: () => post<DnsStatus>("/api/domain-admin/dns/verify"),
  autoDns: () => post("/api/domain-admin/dns/auto"),
  getSharedMailboxes: () => get<SharedMailbox[]>("/api/domain-admin/shared-mailboxes"),
  createSharedMailbox: (data: { mailbox_id: string; display_name: string }) =>
    post<SharedMailbox>("/api/domain-admin/shared-mailboxes", data),
  getWhitelabel: () => get("/api/domain-admin/whitelabel"),
  updateWhitelabel: (data: unknown) => patch("/api/domain-admin/whitelabel", data),
  getRetention: () => get("/api/domain-admin/retention"),
  updateRetention: (data: { retention_days: number }) =>
    patch("/api/domain-admin/retention", data),
  getAuditLogs: (p = 1) => get<Paginated<AuditLog>>(`/api/domain-admin/audit-logs?page=${p}`),
  createBackup: () => post<{ job_id: string }>("/api/domain-admin/backup"),
  getBackupJobs: () => get<BackupJob[]>("/api/domain-admin/backup/jobs"),
  ediscoverySearch: (query: unknown) => post("/api/domain-admin/ediscovery/search", query),
  ediscoveryExport: (query: unknown) => post("/api/domain-admin/ediscovery/export", query),
  getEdiscoveryExports: () => get("/api/domain-admin/ediscovery/exports"),
};

// ─── Mail ──────────────────────────────────────────────────────────────────
export const mailApi = {
  getFolders: () => get<{ folder: string; unread: number; total: number }[]>("/api/mail/folders"),
  getMessages: (folder: string, page = 1, limit = 50) =>
    get<Paginated<EmailHeader>>(`/api/mail/${folder}?page=${page}&limit=${limit}`),
  getMessage: (folder: string, uid: string) =>
    get<EmailFull>(`/api/mail/${folder}/${uid}`),
  sendEmail: (data: unknown) => post<{ message_id: string }>("/api/mail/send", data),
  deleteMessage: (folder: string, uid: string) =>
    del(`/api/mail/${folder}/${uid}`),
  moveMessage: (folder: string, uid: string, target: string) =>
    post(`/api/mail/${folder}/${uid}/move`, { target }),
  updateFlags: (folder: string, uid: string, flags: string[], add: boolean) =>
    patch(`/api/mail/${folder}/${uid}/flags`, { flags, add }),
  search: (q: string) => get<EmailHeader[]>(`/api/mail/search?q=${encodeURIComponent(q)}`),
  getAutoresponder: () => get<Autoresponder>("/api/mail/autoresponder"),
  setAutoresponder: (data: Partial<Autoresponder>) => put("/api/mail/autoresponder", data),
  deleteAutoresponder: () => del("/api/mail/autoresponder"),
  scheduleEmail: (data: unknown) => post("/api/mail/schedule", data),
  getScheduled: () => get("/api/mail/scheduled"),
  cancelScheduled: (id: string) => del(`/api/mail/scheduled/${id}/cancel`),
  reportSpam: (uid: string) => post("/api/mail/report/spam", { uid }),
};

// ─── Labels ────────────────────────────────────────────────────────────────
export const labelsApi = {
  list: () => get<Label[]>("/api/labels"),
  create: (name: string, color: string) => post<Label>("/api/labels", { name, color }),
  update: (id: string, data: Partial<Label>) => patch<Label>(`/api/labels/${id}`, data),
  remove: (id: string) => del(`/api/labels/${id}`),
  applyToEmail: (uid: string, label_id: string) =>
    post(`/api/labels/${label_id}/apply`, { email_uid: uid }),
  removeFromEmail: (uid: string, label_id: string) =>
    del(`/api/labels/${label_id}/email/${uid}`),
};

// ─── Rules ─────────────────────────────────────────────────────────────────
export const rulesApi = {
  list: () => get<EmailRule[]>("/api/rules"),
  create: (data: Omit<EmailRule, "id" | "created_at">) => post<EmailRule>("/api/rules", data),
  update: (id: string, data: Partial<EmailRule>) => patch<EmailRule>(`/api/rules/${id}`, data),
  remove: (id: string) => del(`/api/rules/${id}`),
  test: (id: string, email_uid: string) => post(`/api/rules/${id}/test`, { email_uid }),
};

// ─── Templates ─────────────────────────────────────────────────────────────
export const templatesApi = {
  list: () => get<EmailTemplate[]>("/api/templates"),
  create: (data: Omit<EmailTemplate, "id" | "created_at" | "updated_at">) =>
    post<EmailTemplate>("/api/templates", data),
  update: (id: string, data: Partial<EmailTemplate>) =>
    patch<EmailTemplate>(`/api/templates/${id}`, data),
  remove: (id: string) => del(`/api/templates/${id}`),
};

// ─── Contacts ─────────────────────────────────────────────────────────────
export const contactsApi = {
  list: (q = "") => get<Contact[]>(`/api/contacts?q=${encodeURIComponent(q)}`),
  create: (data: Omit<Contact, "id" | "created_at">) => post<Contact>("/api/contacts", data),
  update: (id: string, data: Partial<Contact>) => patch<Contact>(`/api/contacts/${id}`, data),
  remove: (id: string) => del(`/api/contacts/${id}`),
};

// ─── Calendar ─────────────────────────────────────────────────────────────
export const calendarApi = {
  list: () => get<CalendarEvent[]>("/api/calendar"),
  create: (data: Omit<CalendarEvent, "id" | "uid" | "created_at">) =>
    post<CalendarEvent>("/api/calendar", data),
  update: (id: string, data: Partial<CalendarEvent>) =>
    patch<CalendarEvent>(`/api/calendar/${id}`, data),
  remove: (id: string) => del(`/api/calendar/${id}`),
};

// ─── Tasks ─────────────────────────────────────────────────────────────────
export const tasksApi = {
  list: () => get<Task[]>("/api/tasks"),
  create: (data: Omit<Task, "id" | "created_at">) => post<Task>("/api/tasks", data),
  update: (id: string, data: Partial<Task>) => patch<Task>(`/api/tasks/${id}`, data),
  complete: (id: string) => post(`/api/tasks/${id}/complete`),
  remove: (id: string) => del(`/api/tasks/${id}`),
};

// ─── Notes ─────────────────────────────────────────────────────────────────
export const notesApi = {
  list: () => get<Note[]>("/api/notes"),
  create: (data: Omit<Note, "id" | "created_at" | "updated_at">) => post<Note>("/api/notes", data),
  update: (id: string, data: Partial<Note>) => patch<Note>(`/api/notes/${id}`, data),
  remove: (id: string) => del(`/api/notes/${id}`),
};

// ─── Webhooks ─────────────────────────────────────────────────────────────
export const webhooksApi = {
  list: () => get<Webhook[]>("/api/webhooks"),
  create: (data: { url: string; events: string[] }) => post<Webhook>("/api/webhooks", data),
  update: (id: string, data: Partial<Webhook>) => patch<Webhook>(`/api/webhooks/${id}`, data),
  remove: (id: string) => del(`/api/webhooks/${id}`),
  test: (id: string) => post(`/api/webhooks/${id}/test`),
};

// ─── API Keys ─────────────────────────────────────────────────────────────
export const apiKeysApi = {
  list: () => get<ApiKey[]>("/api/keys"),
  create: (data: { name: string; scopes: string[] }) => post<ApiKey>("/api/keys", data),
  remove: (id: string) => del(`/api/keys/${id}`),
};

// ─── AI ────────────────────────────────────────────────────────────────────
export const aiApi = {
  summarize: (thread_id: string) =>
    post<{ summary: string }>("/api/ai/summarize", { thread_id }),
  smartReply: (message_id: string) =>
    post<{ suggestions: string[] }>("/api/ai/smart-reply", { message_id }),
  priorityInbox: () => get<{ items: { uid: string; priority_score: number }[] }>("/api/ai/priority-inbox"),
  suggestLabels: (message_id: string) =>
    post<{ labels: string[] }>("/api/ai/suggest-labels", { message_id }),
};

// ─── PGP ────────────────────────────────────────────────────────────────────
export const pgpApi = {
  generate: () => post("/api/pgp/generate"),
  getOwnKey: () => get("/api/pgp/own-key"),
  lookupKey: (email: string) => get(`/api/pgp/lookup/${encodeURIComponent(email)}`),
  deleteKey: () => del("/api/pgp/own-key"),
};
