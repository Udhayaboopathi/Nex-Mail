"use client";

import { useEffect, useState } from "react";
import { Plus, Pencil, Trash2, KeyRound, Search } from "lucide-react";
import CreateMailboxModal from "../../../components/domain-admin/CreateMailboxModal";
import EditMailboxModal from "../../../components/domain-admin/EditMailboxModal";
import CreateAliasModal from "../../../components/domain-admin/CreateAliasModal";
import { ResetPasswordModal } from "../../../components/domain-admin/ResetPasswordModal";
import { Badge } from "../../../components/ui/Badge";
import { ProgressBar } from "../../../components/ui/ProgressBar";
import { toast } from "../../../components/ui/Toast";
import { domainAdminApi } from "../../../lib/api";
import type { Mailbox } from "../../../types";

export default function MailboxesPage() {
  const [mailboxes, setMailboxes] = useState<Mailbox[]>([]);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState("");
  const [page, setPage] = useState(1);
  const [total, setTotal] = useState(0);
  const [createOpen, setCreateOpen] = useState(false);
  const [aliasOpen, setAliasOpen] = useState(false);
  const [editing, setEditing] = useState<Mailbox | null>(null);
  const [resetTarget, setResetTarget] = useState<Mailbox | null>(null);

  async function load(q = search, p = page) {
    setLoading(true);
    try {
      const res = await domainAdminApi.getMailboxes(q, p);
      setMailboxes(res.items);
      setTotal(res.total);
    } catch (e) { toast((e as Error).message, "error"); }
    finally { setLoading(false); }
  }

  useEffect(() => { load("", 1); }, []);

  async function handleDelete(id: string, addr: string) {
    if (!confirm(`Delete ${addr}? All emails will be permanently deleted.`)) return;
    try { await domainAdminApi.deleteMailbox(id); toast("Mailbox deleted", "success"); load(); }
    catch (e) { toast((e as Error).message, "error"); }
  }

  const filtered = mailboxes; // server-side filtering via load()

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between flex-wrap gap-3">
        <div>
          <h1 className="text-2xl font-bold text-gray-900 dark:text-white">Mailboxes</h1>
          <p className="text-sm text-gray-500 dark:text-gray-400 mt-0.5">{total} total</p>
        </div>
        <div className="flex gap-2">
          <button onClick={() => setAliasOpen(true)} className="flex items-center gap-2 px-4 py-2 rounded-lg border border-gray-300 dark:border-gray-600 text-gray-700 dark:text-gray-300 text-sm hover:bg-gray-50 dark:hover:bg-gray-800">
            Create Alias
          </button>
          <button onClick={() => setCreateOpen(true)} className="flex items-center gap-2 px-4 py-2 rounded-lg bg-indigo-600 hover:bg-indigo-700 text-white text-sm font-medium">
            <Plus className="w-4 h-4" /> Create Mailbox
          </button>
        </div>
      </div>

      {/* Search */}
      <div className="relative max-w-sm">
        <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-400" />
        <input value={search} onChange={(e) => { setSearch(e.target.value); load(e.target.value, 1); }} placeholder="Search mailboxes…"
          className="w-full pl-9 pr-3 py-2 text-sm rounded-lg border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-800 text-gray-900 dark:text-gray-100 focus:outline-none focus:ring-2 focus:ring-indigo-400" />
      </div>

      {/* Table */}
      <div className="bg-white dark:bg-gray-900 rounded-xl border border-gray-100 dark:border-gray-800 overflow-hidden">
        {loading ? (
          <div className="divide-y divide-gray-100 dark:divide-gray-800">
            {[1,2,3].map((i) => <div key={i} className="h-16 animate-pulse bg-gray-50 dark:bg-gray-800/50" />)}
          </div>
        ) : filtered.length === 0 ? (
          <div className="text-center py-16 text-gray-400 text-sm">No mailboxes found.</div>
        ) : (
          <table className="w-full text-sm">
            <thead className="bg-gray-50 dark:bg-gray-800/50 text-xs text-gray-500 dark:text-gray-400 uppercase">
              <tr>
                <th className="px-4 py-3 text-left">Address</th>
                <th className="px-4 py-3 text-left">Usage</th>
                <th className="px-4 py-3 text-left">Status</th>
                <th className="px-4 py-3 text-right">Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-100 dark:divide-gray-800">
              {filtered.map((m) => (
                <tr key={m.id} className="hover:bg-gray-50 dark:hover:bg-gray-800/30">
                  <td className="px-4 py-3 font-medium text-gray-900 dark:text-white">{m.full_address}</td>
                  <td className="px-4 py-3 min-w-32">
                    <ProgressBar value={m.used_mb} max={m.quota_mb} label={`${m.used_mb}/${m.quota_mb} MB`} />
                  </td>
                  <td className="px-4 py-3">
                    <Badge variant={m.is_active ? "success" : "danger"}>{m.is_active ? "Active" : "Suspended"}</Badge>
                  </td>
                  <td className="px-4 py-3 text-right">
                    <div className="flex items-center justify-end gap-1">
                      <button onClick={() => setEditing(m)} title="Edit" className="p-1.5 rounded hover:bg-gray-100 dark:hover:bg-gray-800">
                        <Pencil className="w-4 h-4 text-gray-500" />
                      </button>
                      <button onClick={() => setResetTarget(m)} title="Reset password" className="p-1.5 rounded hover:bg-gray-100 dark:hover:bg-gray-800">
                        <KeyRound className="w-4 h-4 text-gray-500" />
                      </button>
                      <button onClick={() => handleDelete(m.id, m.full_address)} title="Delete" className="p-1.5 rounded hover:bg-gray-100 dark:hover:bg-gray-800">
                        <Trash2 className="w-4 h-4 text-red-500" />
                      </button>
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>

      {/* Pagination */}
      {total > 50 && (
        <div className="flex justify-center gap-2">
          <button disabled={page === 1} onClick={() => { const p = page-1; setPage(p); load(search, p); }} className="px-3 py-1.5 text-sm rounded border border-gray-300 dark:border-gray-600 disabled:opacity-40 hover:bg-gray-50 dark:hover:bg-gray-800">Prev</button>
          <span className="px-3 py-1.5 text-sm text-gray-500">Page {page}</span>
          <button disabled={page * 50 >= total} onClick={() => { const p = page+1; setPage(p); load(search, p); }} className="px-3 py-1.5 text-sm rounded border border-gray-300 dark:border-gray-600 disabled:opacity-40 hover:bg-gray-50 dark:hover:bg-gray-800">Next</button>
        </div>
      )}

      {/* Modals */}
      <CreateMailboxModal open={createOpen} onClose={() => setCreateOpen(false)} onCreate={() => load()} />
      <CreateAliasModal open={aliasOpen} onClose={() => setAliasOpen(false)} onCreate={() => load()} />
      {editing && (
        <EditMailboxModal open mailboxId={editing.id} initialQuotaMb={editing.quota_mb} initialIsActive={editing.is_active}
          onClose={() => setEditing(null)} onSave={() => { setEditing(null); load(); }} />
      )}
      {resetTarget && (
        <ResetPasswordModal mailboxId={resetTarget.id} mailboxEmail={resetTarget.full_address} onClose={() => setResetTarget(null)} />
      )}
    </div>
  );
}
