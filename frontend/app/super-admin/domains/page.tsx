"use client";

import { useEffect, useState } from "react";
import { Plus, MoreVertical, CheckCircle, XCircle, Search } from "lucide-react";
import { superAdminApi } from "../../../lib/api";
import { AddDomainModal } from "../../../components/super-admin/AddDomainModal";
import { AssignAdminModal } from "../../../components/super-admin/AssignAdminModal";
import { IncreaseStorageModal } from "../../../components/super-admin/IncreaseStorageModal";
import { DNSSetupModal } from "../../../components/super-admin/DNSSetupModal";
import { DomainRowActionMenu } from "../../../components/super-admin/DomainRowActionMenu";
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
  const [storageTarget, setStorageTarget] = useState<Domain | null>(null);
  /** Portal menu anchored to viewport (avoids clip from scroll containers). */
  const [menu, setMenu] = useState<{ domainId: string; rect: DOMRect } | null>(null);

  async function load() {
    setLoading(true);
    try {
      setDomains(await superAdminApi.getDomains());
    } catch (e) {
      toast((e as Error).message, "error");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    load();
  }, []);

  const filtered = domains.filter((d) => d.name.toLowerCase().includes(search.toLowerCase()));

  const menuDomain =
    menu ? (domains.find((x) => x.id === menu.domainId) ?? filtered.find((x) => x.id === menu.domainId) ?? null) : null;

  async function handleSuspend(d: Domain) {
    const reason = prompt(`Suspend reason for ${d.name}:`);
    if (!reason) return;
    try {
      await superAdminApi.suspendDomain(d.id, reason);
      toast(`${d.name} suspended`, "success");
      load();
    } catch (e) {
      toast((e as Error).message, "error");
    }
  }

  async function handleUnsuspend(d: Domain) {
    if (!confirm(`Unsuspend ${d.name}?`)) return;
    try {
      await superAdminApi.unsuspendDomain(d.id);
      toast(`${d.name} unsuspended`, "success");
      load();
    } catch (e) {
      toast((e as Error).message, "error");
    }
  }

  async function handlePushCloudflare(d: Domain) {
    setMenu(null);
    try {
      const r = await superAdminApi.syncCloudflareDns(d.id);
      if (r.ok) toast(r.message || "Cloudflare DNS updated.", "success");
      else toast(r.message || "Cloudflare DNS finished with errors.", "error");
      load();
    } catch (e) {
      toast((e as Error).message, "error");
    }
  }

  async function handleDelete(d: Domain) {
    const ok = confirm(
      `Delete domain ${d.name}? This permanently removes the domain and related data (mailboxes, aliases, etc.). This cannot be undone.`
    );
    if (!ok) return;
    setMenu(null);
    try {
      await superAdminApi.deleteDomain(d.id);
      toast(`Domain ${d.name} deleted.`, "success");
      load();
    } catch (e) {
      toast((e as Error).message, "error");
    }
  }

  const menuItems =
    menuDomain != null
      ? [
          { label: "Assign Admin", fn: () => setAssignTarget(menuDomain) },
          { label: "Increase storage", fn: () => setStorageTarget(menuDomain) },
          { label: "DNS Setup", fn: () => setDnsTarget(menuDomain) },
          ...(menuDomain.cloudflare_auto_dns
            ? [{ label: "Push DNS to Cloudflare", fn: () => void handlePushCloudflare(menuDomain) }]
            : []),
          menuDomain.is_suspended
            ? { label: "Unsuspend", fn: () => void handleUnsuspend(menuDomain) }
            : { label: "Suspend", fn: () => void handleSuspend(menuDomain) },
          { label: "Delete domain", fn: () => void handleDelete(menuDomain) },
        ]
      : [];

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between gap-4 flex-wrap">
        <div>
          <h1 className="text-2xl font-bold text-gray-900 dark:text-white">Domains</h1>
          <p className="text-sm text-gray-500 dark:text-gray-400 mt-0.5">{domains.length} domain(s)</p>
        </div>
        <button
          type="button"
          onClick={() => setShowAdd(true)}
          className="flex items-center gap-2 px-4 py-2 rounded-lg bg-indigo-600 hover:bg-indigo-700 text-white text-sm font-medium"
        >
          <Plus className="w-4 h-4" /> Add Domain
        </button>
      </div>

      <div className="relative max-w-sm">
        <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-400" />
        <input
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          placeholder="Search domains…"
          className="w-full pl-9 pr-3 py-2 text-sm rounded-lg border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-800 text-gray-900 dark:text-gray-100 focus:outline-none focus:ring-2 focus:ring-indigo-400"
        />
      </div>

      <div className="bg-white dark:bg-gray-900 rounded-xl border border-gray-100 dark:border-gray-800">
        {loading ? (
          <div className="divide-y divide-gray-100 dark:divide-gray-800 rounded-xl overflow-hidden">
            {[1, 2, 3].map((i) => (
              <div key={i} className="h-14 animate-pulse bg-gray-50 dark:bg-gray-800/50" />
            ))}
          </div>
        ) : filtered.length === 0 ? (
          <div className="text-center py-16 text-gray-400 dark:text-gray-600 text-sm">No domains found.</div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead className="bg-gray-50 dark:bg-gray-800/50 text-xs text-gray-500 dark:text-gray-400 uppercase tracking-wider">
                <tr>
                  <th className="px-4 py-3 text-left">Domain</th>
                  <th className="px-4 py-3 text-left">Storage</th>
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
                    <td className="px-4 py-3 text-gray-600 dark:text-gray-400 tabular-nums text-xs">
                      {(d.used_storage_gb ?? 0).toFixed(1)} / {d.storage_quota_gb ?? 10} GB
                    </td>
                    <td className="px-4 py-3">
                      {d.is_suspended ? (
                        <Badge variant="danger">Suspended</Badge>
                      ) : d.is_active ? (
                        <Badge variant="success">Active</Badge>
                      ) : (
                        <Badge>Inactive</Badge>
                      )}
                    </td>
                    <td className="px-4 py-3">
                      {d.dns_verified ? (
                        <CheckCircle className="w-4 h-4 text-green-500" />
                      ) : (
                        <XCircle className="w-4 h-4 text-red-400" />
                      )}
                    </td>
                    <td className="px-4 py-3 text-gray-500 dark:text-gray-400">
                      {d.admin_user_id ? "Assigned" : "—"}
                    </td>
                    <td className="px-4 py-3 text-right">
                      <button
                        type="button"
                        aria-haspopup="menu"
                        aria-expanded={menu?.domainId === d.id}
                        onClick={(e) => {
                          e.stopPropagation();
                          const rect = e.currentTarget.getBoundingClientRect();
                          setMenu((m) => (m?.domainId === d.id ? null : { domainId: d.id, rect }));
                        }}
                        className="p-1.5 rounded hover:bg-gray-100 dark:hover:bg-gray-800"
                      >
                        <MoreVertical className="w-4 h-4 text-gray-500" />
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>

      <DomainRowActionMenu
        open={!!menu && !!menuDomain}
        anchorRect={menu?.rect ?? null}
        items={menuItems}
        onClose={() => setMenu(null)}
      />

      {showAdd && <AddDomainModal onClose={() => setShowAdd(false)} onAdded={load} />}
      {assignTarget && (
        <AssignAdminModal
          domainId={assignTarget.id}
          domainName={assignTarget.name}
          onClose={() => setAssignTarget(null)}
          onAssigned={load}
        />
      )}
      {dnsTarget && (
        <DNSSetupModal domainId={dnsTarget.id} domainName={dnsTarget.name} onClose={() => setDnsTarget(null)} />
      )}
      {storageTarget && (
        <IncreaseStorageModal
          domain={storageTarget}
          onClose={() => setStorageTarget(null)}
          onSaved={load}
        />
      )}
    </div>
  );
}
