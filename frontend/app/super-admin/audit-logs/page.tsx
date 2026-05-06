"use client";

import { useEffect, useState } from "react";
import { RefreshCcw } from "lucide-react";
import { superAdminApi } from "../../../lib/api";
import { toast } from "../../../components/ui/Toast";
import type { AuditLog } from "../../../types";

export default function AuditLogsPage() {
  const [logs, setLogs] = useState<AuditLog[]>([]);
  const [loading, setLoading] = useState(true);
  const [page, setPage] = useState(1);
  const [total, setTotal] = useState(0);

  async function load(p = 1) {
    setLoading(true);
    try {
      const res = await superAdminApi.getAuditLogs(p);
      setLogs(res.items);
      setTotal(res.total);
      setPage(p);
    } catch (e) { toast((e as Error).message, "error"); }
    finally { setLoading(false); }
  }

  useEffect(() => { load(); }, []);

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900 dark:text-white">Audit Logs</h1>
          <p className="text-sm text-gray-500 dark:text-gray-400 mt-0.5">{total} total events</p>
        </div>
        <button onClick={() => load(page)} className="p-2 rounded-lg border border-gray-300 dark:border-gray-600 hover:bg-gray-50 dark:hover:bg-gray-800">
          <RefreshCcw className="w-4 h-4 text-gray-600 dark:text-gray-400" />
        </button>
      </div>

      <div className="bg-white dark:bg-gray-900 rounded-xl border border-gray-100 dark:border-gray-800 overflow-hidden">
        {loading ? (
          <div className="space-y-2 p-4">{[1,2,3,4,5].map((i) => <div key={i} className="h-10 bg-gray-100 dark:bg-gray-800 rounded animate-pulse" />)}</div>
        ) : logs.length === 0 ? (
          <div className="text-center py-16 text-gray-400 text-sm">No audit events.</div>
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
                  <td className="px-4 py-3 text-gray-400 dark:text-gray-500 whitespace-nowrap text-xs">{new Date(l.created_at).toLocaleString()}</td>
                  <td className="px-4 py-3 font-medium text-gray-800 dark:text-gray-200">{l.action}</td>
                  <td className="px-4 py-3 text-gray-500 dark:text-gray-400 truncate max-w-xs">{l.target ?? "—"}</td>
                  <td className="px-4 py-3 text-gray-400 dark:text-gray-500 font-mono text-xs">{l.ip_address ?? "—"}</td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>

      {/* Pagination */}
      {total > 50 && (
        <div className="flex justify-center gap-2">
          <button disabled={page === 1} onClick={() => load(page - 1)} className="px-3 py-1.5 text-sm rounded border border-gray-300 dark:border-gray-600 disabled:opacity-40 hover:bg-gray-50 dark:hover:bg-gray-800">Prev</button>
          <span className="px-3 py-1.5 text-sm text-gray-500">Page {page}</span>
          <button disabled={page * 50 >= total} onClick={() => load(page + 1)} className="px-3 py-1.5 text-sm rounded border border-gray-300 dark:border-gray-600 disabled:opacity-40 hover:bg-gray-50 dark:hover:bg-gray-800">Next</button>
        </div>
      )}
    </div>
  );
}
