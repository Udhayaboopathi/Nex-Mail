"use client";

import { useState } from "react";
import { X, AlertTriangle, Archive } from "lucide-react";
import type { BackupJob } from "../../types";

interface RestorePreviewModalProps {
  backup: BackupJob;
  onConfirm: () => void;
  onClose: () => void;
  restoring?: boolean;
}

export function RestorePreviewModal({ backup, onConfirm, onClose, restoring = false }: RestorePreviewModalProps) {
  const [confirmText, setConfirmText] = useState("");
  const ready = confirmText === "RESTORE";

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/50">
      <div className="bg-white dark:bg-gray-900 rounded-xl shadow-2xl w-full max-w-md">
        <div className="flex items-center justify-between px-6 py-4 border-b border-gray-100 dark:border-gray-800">
          <h2 className="text-lg font-semibold text-gray-900 dark:text-white">Restore Backup</h2>
          <button onClick={onClose} className="p-1.5 rounded hover:bg-gray-100 dark:hover:bg-gray-800">
            <X className="w-5 h-5 text-gray-500" />
          </button>
        </div>

        <div className="px-6 py-6 space-y-4">
          <div className="flex items-center gap-3 p-3 bg-red-50 dark:bg-red-900/20 rounded-lg border border-red-200 dark:border-red-800">
            <AlertTriangle className="w-6 h-6 text-red-600 shrink-0" />
            <p className="text-sm text-red-700 dark:text-red-400">
              This will <strong>overwrite current data</strong>. This action cannot be undone.
            </p>
          </div>

          <div className="bg-gray-50 dark:bg-gray-800 rounded-lg p-4 space-y-2 text-sm">
            <div className="flex items-center gap-2 mb-2">
              <Archive className="w-4 h-4 text-indigo-500" />
              <span className="font-medium text-gray-900 dark:text-white">Backup Details</span>
            </div>
            <div className="grid grid-cols-2 gap-1 text-gray-600 dark:text-gray-400 text-xs">
              <span>Type:</span><span className="font-medium">{backup.type}</span>
              <span>Status:</span><span className="font-medium">{backup.status}</span>
              <span>Size:</span><span className="font-medium">{backup.file_size_mb?.toFixed(1) ?? "—"} MB</span>
              <span>Messages:</span><span className="font-medium">{backup.total_messages ?? "—"}</span>
              <span>Created:</span><span className="font-medium">{new Date(backup.created_at).toLocaleString()}</span>
            </div>
          </div>

          <div>
            <label className="block text-sm text-gray-600 dark:text-gray-400 mb-1">
              Type <strong>RESTORE</strong> to confirm:
            </label>
            <div className="flex gap-2">
              <input
                value={confirmText}
                onChange={(e) => setConfirmText(e.target.value)}
                placeholder="RESTORE"
                className="flex-1 px-3 py-2 text-sm rounded-lg border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-800 text-gray-900 dark:text-gray-100 focus:outline-none focus:ring-2 focus:ring-red-400"
              />
              <button
                onClick={onConfirm}
                disabled={!ready || restoring}
                className="px-4 py-2 text-sm rounded-lg bg-red-600 hover:bg-red-700 text-white font-medium disabled:opacity-40"
              >
                {restoring ? "Restoring…" : "Restore"}
              </button>
            </div>
          </div>
        </div>

        <div className="flex justify-end px-6 py-4 border-t border-gray-100 dark:border-gray-800">
          <button onClick={onClose} className="px-4 py-2 text-sm rounded-lg text-gray-700 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-800">
            Cancel
          </button>
        </div>
      </div>
    </div>
  );
}
