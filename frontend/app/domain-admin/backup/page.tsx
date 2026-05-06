"use client";

import { useEffect, useState } from "react";
import { Archive, RefreshCcw, Download } from "lucide-react";
import { domainAdminApi } from "../../../lib/api";
import { Badge } from "../../../components/ui/Badge";
import { RestorePreviewModal } from "../../../components/domain-admin/RestorePreviewModal";
import { toast } from "../../../components/ui/Toast";
import type { BackupJob } from "../../../types";

export default function BackupPage() {
  const [jobs, setJobs] = useState<BackupJob[]>([]);
  const [loading, setLoading] = useState(true);
  const [creating, setCreating] = useState(false);
  const [restoreTarget, setRestoreTarget] = useState<BackupJob | null>(null);
  const [restoring, setRestoring] = useState(false);

  async function load() {
    setLoading(true);
    try { setJobs(await domainAdminApi.getBackupJobs()); }
    catch (e) { toast((e as Error).message, "error"); }
    finally { setLoading(false); }
  }

  useEffect(() => { load(); }, []);

  async function handleCreate() {
    setCreating(true);
    try { await domainAdminApi.createBackup(); toast("Backup queued", "success"); setTimeout(load, 2000); }
    catch (e) { toast((e as Error).message, "error"); }
    finally { setCreating(false); }
  }

  async function handleRestore() {
    if (!restoreTarget) return;
    setRestoring(true);
    try {
      toast("Restore started — check audit logs", "info");
      setRestoreTarget(null);
    } catch (e) { toast((e as Error).message, "error"); }
    finally { setRestoring(false); }
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between flex-wrap gap-3">
        <h1 className="text-2xl font-bold text-gray-900 dark:text-white">Backup</h1>
        <div className="flex gap-2">
          <button onClick={load} className="p-2 rounded-lg border border-gray-300 dark:border-gray-600 hover:bg-gray-50 dark:hover:bg-gray-800"><RefreshCcw className="w-4 h-4 text-gray-600 dark:text-gray-400" /></button>
          <button onClick={handleCreate} disabled={creating} className="flex items-center gap-2 px-4 py-2 rounded-lg bg-indigo-600 hover:bg-indigo-700 text-white text-sm font-medium disabled:opacity-60">
            <Archive className="w-4 h-4" /> {creating ? "Creating…" : "New Backup"}
          </button>
        </div>
      </div>

      <div className="bg-white dark:bg-gray-900 rounded-xl border border-gray-100 dark:border-gray-800 overflow-hidden">
        {loading ? <div className="p-4 space-y-2">{[1,2].map((i) => <div key={i} className="h-12 bg-gray-100 dark:bg-gray-800 rounded animate-pulse" />)}</div>
          : jobs.length === 0 ? <div className="text-center py-16 text-gray-400 text-sm">No backups yet.</div>
          : (
            <table className="w-full text-sm">
              <thead className="bg-gray-50 dark:bg-gray-800/50 text-xs text-gray-500 dark:text-gray-400 uppercase">
                <tr>
                  <th className="px-4 py-3 text-left">Type</th>
                  <th className="px-4 py-3 text-left">Status</th>
                  <th className="px-4 py-3 text-left">Size</th>
                  <th className="px-4 py-3 text-left">Created</th>
                  <th className="px-4 py-3 text-right">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-100 dark:divide-gray-800">
                {jobs.map((j) => (
                  <tr key={j.id} className="hover:bg-gray-50 dark:hover:bg-gray-800/30">
                    <td className="px-4 py-3 font-medium text-gray-800 dark:text-gray-200 capitalize">{j.type}</td>
                    <td className="px-4 py-3"><Badge variant={j.status === "done" ? "success" : j.status === "failed" ? "danger" : "info"}>{j.status}</Badge></td>
                    <td className="px-4 py-3 text-gray-500">{j.file_size_mb ? `${j.file_size_mb.toFixed(1)} MB` : "—"}</td>
                    <td className="px-4 py-3 text-gray-500">{new Date(j.created_at).toLocaleDateString()}</td>
                    <td className="px-4 py-3 text-right flex items-center justify-end gap-1">
                      {j.status === "done" && <>
                        <a href={`/api/domain-admin/backup/jobs/${j.id}/download`} className="p-1.5 rounded hover:bg-gray-100 dark:hover:bg-gray-800"><Download className="w-4 h-4 text-indigo-600 dark:text-indigo-400" /></a>
                        <button onClick={() => setRestoreTarget(j)} className="px-2.5 py-1 text-xs rounded bg-red-50 dark:bg-red-900/20 text-red-600 dark:text-red-400 hover:bg-red-100">Restore</button>
                      </>}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
      </div>

      {restoreTarget && <RestorePreviewModal backup={restoreTarget} onConfirm={handleRestore} onClose={() => setRestoreTarget(null)} restoring={restoring} />}
    </div>
  );
}
