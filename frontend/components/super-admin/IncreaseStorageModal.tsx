"use client";

import { useState } from "react";
import { X, HardDrive } from "lucide-react";
import { superAdminApi } from "../../lib/api";
import { toast } from "../ui/Toast";
import type { Domain } from "../../types";

interface IncreaseStorageModalProps {
  domain: Domain;
  onClose: () => void;
  onSaved: () => void;
}

export function IncreaseStorageModal({ domain, onClose, onSaved }: IncreaseStorageModalProps) {
  const [quotaGb, setQuotaGb] = useState(String(domain.storage_quota_gb ?? 10));
  const [saving, setSaving] = useState(false);

  async function handleSave() {
    const n = parseInt(quotaGb, 10);
    if (Number.isNaN(n) || n < 1) {
      toast("Enter a valid size in GB (at least 1).", "error");
      return;
    }
    if (n > 2048) {
      toast("Maximum domain storage is 2048 GB.", "error");
      return;
    }
    const used = domain.used_storage_gb ?? 0;
    if (n < used) {
      toast(`Quota cannot be below current usage (${used.toFixed(2)} GB).`, "error");
      return;
    }
    setSaving(true);
    try {
      await superAdminApi.updateDomain(domain.id, { storage_quota_gb: n });
      toast(`Storage for ${domain.name} set to ${n} GB.`, "success");
      onSaved();
      onClose();
    } catch (err) {
      toast((err as Error).message, "error");
    } finally {
      setSaving(false);
    }
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/50">
      <div className="bg-white dark:bg-gray-900 rounded-xl shadow-2xl w-full max-w-md">
        <div className="flex items-center justify-between px-6 py-4 border-b border-gray-100 dark:border-gray-800">
          <h2 className="text-lg font-semibold text-gray-900 dark:text-white">Domain storage</h2>
          <button type="button" onClick={onClose} className="p-1.5 rounded hover:bg-gray-100 dark:hover:bg-gray-800">
            <X className="w-5 h-5 text-gray-500" />
          </button>
        </div>
        <div className="px-6 py-6 space-y-4">
          <div className="flex items-start gap-3 p-3 rounded-lg bg-slate-50 dark:bg-slate-900/30 text-sm text-slate-700 dark:text-slate-300">
            <HardDrive className="w-5 h-5 shrink-0 mt-0.5" />
            <p>
              Total pool for <strong>{domain.name}</strong>. The domain admin divides this across mailboxes; mailbox
              quotas should not exceed this total.
            </p>
          </div>
          <p className="text-xs text-gray-500 dark:text-gray-400">
            Used: <span className="font-mono">{(domain.used_storage_gb ?? 0).toFixed(2)} GB</span> · Current limit:{" "}
            <span className="font-mono">{domain.storage_quota_gb ?? 10} GB</span>
          </p>
          <div>
            <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">Total storage (GB)</label>
            <input
              type="number"
              min={1}
              max={2048}
              value={quotaGb}
              onChange={(e) => setQuotaGb(e.target.value)}
              className="w-full px-3 py-2 text-sm rounded-lg border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-800 text-gray-900 dark:text-gray-100 focus:outline-none focus:ring-2 focus:ring-indigo-400"
              onKeyDown={(e) => e.key === "Enter" && handleSave()}
            />
          </div>
        </div>
        <div className="flex justify-end gap-3 px-6 py-4 border-t border-gray-100 dark:border-gray-800">
          <button
            type="button"
            onClick={onClose}
            className="px-4 py-2 text-sm rounded-lg text-gray-700 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-800"
          >
            Cancel
          </button>
          <button
            type="button"
            onClick={handleSave}
            disabled={saving}
            className="px-4 py-2 text-sm rounded-lg bg-indigo-600 hover:bg-indigo-700 text-white font-medium disabled:opacity-60"
          >
            {saving ? "Saving…" : "Save"}
          </button>
        </div>
      </div>
    </div>
  );
}
