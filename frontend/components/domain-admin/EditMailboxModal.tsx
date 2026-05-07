"use client";

import { useEffect, useState } from "react";
import { X } from "lucide-react";
import { domainAdminApi } from "../../lib/api";
import { toast } from "../ui/Toast";

interface EditMailboxModalProps {
  open: boolean;
  mailboxId: string;
  initialDisplayName?: string;
  initialQuotaMb: number;
  initialIsActive: boolean;
  onClose: () => void;
  onSave: () => void;
}

export default function EditMailboxModal({
  open,
  mailboxId,
  initialDisplayName = "",
  initialQuotaMb,
  initialIsActive,
  onClose,
  onSave,
}: EditMailboxModalProps) {
  const [displayName, setDisplayName] = useState(initialDisplayName);
  const [quotaMb, setQuotaMb] = useState(String(initialQuotaMb));
  const [isActive, setIsActive] = useState(initialIsActive);
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    if (!open) return;
    setDisplayName(initialDisplayName);
    setQuotaMb(String(initialQuotaMb));
    setIsActive(initialIsActive);
  }, [open, mailboxId, initialDisplayName, initialQuotaMb, initialIsActive]);

  if (!open) return null;

  async function save() {
    setBusy(true);
    try {
      await domainAdminApi.updateMailbox(mailboxId, {
        display_name: displayName.trim() || null,
        quota_mb: Number(quotaMb),
        is_active: isActive,
      });
      toast("Mailbox updated!", "success");
      onSave();
      onClose();
    } catch (err) { toast((err as Error).message, "error"); }
    finally { setBusy(false); }
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/50">
      <div className="bg-white dark:bg-gray-900 rounded-xl shadow-2xl w-full max-w-sm">
        <div className="flex items-center justify-between px-5 py-4 border-b border-gray-100 dark:border-gray-800">
          <h2 className="font-semibold text-gray-900 dark:text-white">Edit Mailbox</h2>
          <button onClick={onClose} className="p-1.5 rounded hover:bg-gray-100 dark:hover:bg-gray-800"><X className="w-4 h-4 text-gray-500" /></button>
        </div>
        <div className="px-5 py-5 space-y-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">Full name</label>
            <input
              type="text"
              value={displayName}
              onChange={(e) => setDisplayName(e.target.value)}
              placeholder="Display name"
              className="w-full px-3 py-2 text-sm rounded-lg border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-800 text-gray-900 dark:text-gray-100 focus:outline-none focus:ring-2 focus:ring-indigo-400"
            />
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">Quota (MB)</label>
            <input type="number" value={quotaMb} onChange={(e) => setQuotaMb(e.target.value)} min={64}
              className="w-full px-3 py-2 text-sm rounded-lg border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-800 text-gray-900 dark:text-gray-100 focus:outline-none focus:ring-2 focus:ring-indigo-400" />
          </div>
          <label className="flex items-center gap-2 text-sm text-gray-700 dark:text-gray-300 cursor-pointer">
            <input type="checkbox" checked={isActive} onChange={(e) => setIsActive(e.target.checked)} className="accent-indigo-600" />
            Mailbox active
          </label>
        </div>
        <div className="flex justify-end gap-2 px-5 py-4 border-t border-gray-100 dark:border-gray-800">
          <button onClick={onClose} className="px-4 py-2 text-sm rounded-lg text-gray-700 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-800">Cancel</button>
          <button onClick={save} disabled={busy} className="px-4 py-2 text-sm rounded-lg bg-indigo-600 hover:bg-indigo-700 text-white font-medium disabled:opacity-60">
            {busy ? "Saving…" : "Save Changes"}
          </button>
        </div>
      </div>
    </div>
  );
}
