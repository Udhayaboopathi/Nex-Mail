"use client";

import { useEffect, useState } from "react";
import { Plus, MoreVertical, CheckCircle, XCircle, Search } from "lucide-react";
import { superAdminApi } from "../../../lib/api";
import { AddDomainModal } from "../../../components/super-admin/AddDomainModal";
import { AssignAdminModal } from "../../../components/super-admin/AssignAdminModal";
import { DNSSetupModal } from "../../../components/super-admin/DNSSetupModal";
import { Badge } from "../../../components/ui/Badge";
import { toast } from "../../../components/ui/Toast";
import type { Domain } from "../../../types";

export default function DomainsPage() {
  const [domains, setDomains] = useState<Domain[]>([]);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState("");
  const [showAdd, setShowAdd] = useState(false);
  const [assignTarget, setAssignTarget] = useState<Domain | null>(null);
  const [dnsTarget, setDnsTarget] = useState<Domain | null>(null);
  const [menuOpen, setMenuOpen] = useState<string | null>(null);

  async function load() {
    setLoading(true);
    try { setDomains(await superAdminApi.getDomains()); }
    catch (e) { toast((e as Error).message, "error"); }
    finally { setLoading(false); }
  }

  useEffect(() => { load(); }, []);

  const filtered = domains.filter((d) => d.name.toLowerCase().includes(search.toLowerCase()));

  async function handleSuspend(d: Domain) {
    const reason = prompt(`Suspend reason for ${d.name}:`);
    if (!reason) return;
    try {
      await superAdminApi.suspendDomain(d.id, reason);
      toast(`${d.name} suspended`, "success");
      load();
    } catch (e) { toast((e as Error).message, "error"); }
  }

  async function handleUnsuspend(d: Domain) {
    if (!confirm(`Unsuspend ${d.name}?`)) return;
    try {
      await superAdminApi.unsuspendDomain(d.id);
      toast(`${d.name} unsuspended`, "success");
      load();
    } catch (e) { toast((e as Error).message, "error"); }
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between gap-4 flex-wrap">
        <div>
          <h1 className="text-2xl font-bold text-gray-900 dark:text-white">Domains</h1>
          <p className="text-sm text-gray-500 dark:text-gray-400 mt-0.5">{domains.length} domain(s)</p>
        </div>
        <button onClick={() => setShowAdd(true)} className="flex items-center gap-2 px-4 py-2 rounded-lg bg-indigo-600 hover:bg-indigo-700 text-white text-sm font-medium">
          <Plus className="w-4 h-4" /> Add Domain
        </button>
      </div>

      {/* Search */}
      <div className="relative max-w-sm">
        <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-400" />
        <input value={search} onChange={(e) => setSearch(e.target.value)} placeholder="Search domains…"
          className="w-full pl-9 pr-3 py-2 text-sm rounded-lg border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-800 text-gray-900 dark:text-gray-100 focus:outline-none focus:ring-2 focus:ring-indigo-400" />
      </div>

      {/* Table */}
      <div className="bg-white dark:bg-gray-900 rounded-xl border border-gray-100 dark:border-gray-800 overflow-hidden">
        {loading ? (
          <div className="divide-y divide-gray-100 dark:divide-gray-800">
            {[1, 2, 3].map((i) => <div key={i} className="h-14 animate-pulse bg-gray-50 dark:bg-gray-800/50" />)}
          </div>
        ) : filtered.length === 0 ? (
          <div className="text-center py-16 text-gray-400 dark:text-gray-600 text-sm">No domains found.</div>
        ) : (
          <table className="w-full text-sm">
            <thead className="bg-gray-50 dark:bg-gray-800/50 text-xs text-gray-500 dark:text-gray-400 uppercase tracking-wider">
              <tr>
                <th className="px-4 py-3 text-left">Domain</th>
                <th className="px-4 py-3 text-left">Status</th>
                <th className="px-4 py-3 text-left">DNS</th>
                <th className="px-4 py-3 text-left">Admin</th>
                <th className="px-4 py-3 text-right">Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-100 dark:divide-gray-800">
              {filtered.map((d) => (
                <tr key={d.id} className="hover:bg-gray-50 dark:hover:bg-gray-800/30">
                  <td className="px-4 py-3 font-medium text-gray-900 dark:text-white">{d.name}</td>
                  <td className="px-4 py-3">
                    {d.is_suspended
                      ? <Badge variant="danger">Suspended</Badge>
                      : d.is_active
                      ? <Badge variant="success">Active</Badge>
                      : <Badge>Inactive</Badge>}
                  </td>
                  <td className="px-4 py-3">
                    {d.dns_verified
                      ? <CheckCircle className="w-4 h-4 text-green-500" />
                      : <XCircle className="w-4 h-4 text-red-400" />}
                  </td>
                  <td className="px-4 py-3 text-gray-500 dark:text-gray-400">{d.admin_user_id ? "Assigned" : "—"}</td>
                  <td className="px-4 py-3 text-right">
                    <div className="relative inline-block">
                      <button onClick={() => setMenuOpen(menuOpen === d.id ? null : d.id)}
                        className="p-1.5 rounded hover:bg-gray-100 dark:hover:bg-gray-800">
                        <MoreVertical className="w-4 h-4 text-gray-500" />
                      </button>
                      {menuOpen === d.id && (
                        <div className="absolute right-0 mt-1 w-48 bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-lg shadow-lg z-20 py-1" onMouseLeave={() => setMenuOpen(null)}>
                          {[
                            { label: "Assign Admin", fn: () => { setAssignTarget(d); setMenuOpen(null); } },
                            { label: "DNS Setup", fn: () => { setDnsTarget(d); setMenuOpen(null); } },
                            d.is_suspended
                              ? { label: "Unsuspend", fn: () => { handleUnsuspend(d); setMenuOpen(null); } }
                              : { label: "Suspend", fn: () => { handleSuspend(d); setMenuOpen(null); } },
                          ].map(({ label, fn }) => (
                            <button key={label} onClick={fn} className="w-full text-left px-4 py-2 text-sm text-gray-700 dark:text-gray-300 hover:bg-gray-50 dark:hover:bg-gray-700">{label}</button>
                          ))}
                        </div>
                      )}
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>

      {showAdd && <AddDomainModal onClose={() => setShowAdd(false)} onAdded={load} />}
      {assignTarget && <AssignAdminModal domainId={assignTarget.id} domainName={assignTarget.name} onClose={() => setAssignTarget(null)} onAssigned={load} />}
      {dnsTarget && <DNSSetupModal domainId={dnsTarget.id} domainName={dnsTarget.name} onClose={() => setDnsTarget(null)} />}
    </div>
  );
}
