"use client";

import { useEffect, useState } from "react";
import { domainAdminApi } from "../../../lib/api";
import { toast } from "../../../components/ui/Toast";
import type { AuditLog } from "../../../types";

export default function DomainAuditPage() {
  const [logs, setLogs] = useState<AuditLog[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    domainAdminApi.getAuditLogs()
      .then((r) => setLogs(r.items))
      .catch((e) => toast(e.message, "error"))
      .finally(() => setLoading(false));
  }, []);

  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-bold text-gray-900 dark:text-white">Audit Logs</h1>
      <div className="bg-white dark:bg-gray-900 rounded-xl border border-gray-100 dark:border-gray-800 overflow-hidden">
        {loading ? (
          <div className="p-4 space-y-2">{[1,2,3].map((i)=><div key={i} className="h-10 bg-gray-100 dark:bg-gray-800 rounded animate-pulse"/>)}</div>
        ) : logs.length === 0 ? (
          <div className="py-16 text-center text-gray-400 text-sm">No audit events for this domain.</div>
        ) : (
          <table className="w-full text-sm">
            <thead className="bg-gray-50 dark:bg-gray-800/50 text-xs text-gray-500 dark:text-gray-400 uppercase">
              <tr>
                <th className="px-4 py-3 text-left">Time</th>
                <th className="px-4 py-3 text-left">Action</th>
                <th className="px-4 py-3 text-left">Target</th>
                <th className="px-4 py-3 text-left">IP</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-100 dark:divide-gray-800">
              {logs.map((l) => (
                <tr key={l.id} className="hover:bg-gray-50 dark:hover:bg-gray-800/30">
                  <td className="px-4 py-3 text-xs text-gray-400 whitespace-nowrap">{new Date(l.created_at).toLocaleString()}</td>
                  <td className="px-4 py-3 font-medium text-gray-800 dark:text-gray-200">{l.action}</td>
                  <td className="px-4 py-3 text-gray-500 dark:text-gray-400">{l.target ?? "—"}</td>
                  <td className="px-4 py-3 text-xs font-mono text-gray-400">{l.ip_address ?? "—"}</td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>
    </div>
  );
}
