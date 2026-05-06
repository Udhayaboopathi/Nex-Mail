"use client";

import { useEffect, useState } from "react";
import { Plus, Trash2, RefreshCcw } from "lucide-react";
import { domainAdminApi } from "../../../lib/api";
import CreateAliasModal from "../../../components/domain-admin/CreateAliasModal";
import { Badge } from "../../../components/ui/Badge";
import { toast } from "../../../components/ui/Toast";
import type { Alias } from "../../../types";

export default function AliasesPage() {
  const [aliases, setAliases] = useState<Alias[]>([]);
  const [loading, setLoading] = useState(true);
  const [createOpen, setCreateOpen] = useState(false);

  async function load() {
    setLoading(true);
    try { setAliases(await domainAdminApi.getAliases()); }
    catch (e) { toast((e as Error).message, "error"); }
    finally { setLoading(false); }
  }

  useEffect(() => { load(); }, []);

  async function handleDelete(id: string) {
    if (!confirm("Delete this alias?")) return;
    try { await domainAdminApi.deleteAlias(id); setAliases((p) => p.filter((a) => a.id !== id)); toast("Alias deleted", "success"); }
    catch (e) { toast((e as Error).message, "error"); }
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between flex-wrap gap-3">
        <div>
          <h1 className="text-2xl font-bold text-gray-900 dark:text-white">Aliases</h1>
          <p className="text-sm text-gray-500 dark:text-gray-400 mt-0.5">{aliases.length} alias(es)</p>
        </div>
        <div className="flex gap-2">
          <button onClick={load} className="p-2 rounded-lg border border-gray-300 dark:border-gray-600 hover:bg-gray-50 dark:hover:bg-gray-800"><RefreshCcw className="w-4 h-4 text-gray-600 dark:text-gray-400" /></button>
          <button onClick={() => setCreateOpen(true)} className="flex items-center gap-2 px-4 py-2 rounded-lg bg-indigo-600 hover:bg-indigo-700 text-white text-sm font-medium">
            <Plus className="w-4 h-4" /> Create Alias
          </button>
        </div>
      </div>

      <div className="bg-white dark:bg-gray-900 rounded-xl border border-gray-100 dark:border-gray-800 overflow-hidden">
        {loading ? (
          <div className="divide-y divide-gray-100 dark:divide-gray-800">{[1,2,3].map((i) => <div key={i} className="h-14 animate-pulse bg-gray-50 dark:bg-gray-800/50" />)}</div>
        ) : aliases.length === 0 ? (
          <div className="text-center py-16 text-gray-400 text-sm">No aliases yet.</div>
        ) : (
          <table className="w-full text-sm">
            <thead className="bg-gray-50 dark:bg-gray-800/50 text-xs text-gray-500 dark:text-gray-400 uppercase">
              <tr>
                <th className="px-4 py-3 text-left">Source</th>
                <th className="px-4 py-3 text-left">Destination</th>
                <th className="px-4 py-3 text-left">Type</th>
                <th className="px-4 py-3 text-left">Status</th>
                <th className="px-4 py-3 text-right">Delete</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-100 dark:divide-gray-800">
              {aliases.map((a) => (
                <tr key={a.id} className="hover:bg-gray-50 dark:hover:bg-gray-800/30">
                  <td className="px-4 py-3 font-medium text-gray-900 dark:text-white">{a.source_address}</td>
                  <td className="px-4 py-3 text-gray-500 dark:text-gray-400">{a.destination_address}</td>
                  <td className="px-4 py-3"><Badge variant={a.is_catch_all ? "purple" : "default"}>{a.is_catch_all ? "Catch-all" : "Alias"}</Badge></td>
                  <td className="px-4 py-3"><Badge variant={a.is_active ? "success" : "danger"}>{a.is_active ? "Active" : "Inactive"}</Badge></td>
                  <td className="px-4 py-3 text-right">
                    <button onClick={() => handleDelete(a.id)} className="p-1.5 rounded hover:bg-gray-100 dark:hover:bg-gray-800"><Trash2 className="w-4 h-4 text-red-500" /></button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>

      <CreateAliasModal open={createOpen} onClose={() => setCreateOpen(false)} onCreate={load} />
    </div>
  );
}
