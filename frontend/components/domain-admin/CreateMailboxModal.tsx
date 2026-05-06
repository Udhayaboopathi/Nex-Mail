"use client";

import { useState } from "react";
import { X } from "lucide-react";
import { domainAdminApi } from "../../lib/api";
import { toast } from "../ui/Toast";

interface CreateMailboxModalProps {
  open: boolean;
  domainId?: string;
  userId?: string;
  onClose: () => void;
  onCreate: () => void;
}

export default function CreateMailboxModal({ open, onClose, onCreate }: CreateMailboxModalProps) {
  const [localPart, setLocalPart] = useState("");
  const [password, setPassword] = useState("");
  const [quotaMb, setQuotaMb] = useState("1024");
  const [busy, setBusy] = useState(false);

  if (!open) return null;

  async function submit() {
    if (!localPart.trim()) { toast("Local part is required", "error"); return; }
    if (password.length < 8) { toast("Password must be at least 8 characters", "error"); return; }
    setBusy(true);
    try {
      await domainAdminApi.createMailbox({ local_part: localPart.trim(), password, quota_mb: Number(quotaMb) || 1024 });
      toast("Mailbox created!", "success");
      onCreate();
      setLocalPart(""); setPassword(""); setQuotaMb("1024");
      onClose();
    } catch (err) { toast((err as Error).message, "error"); }
    finally { setBusy(false); }
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/50">
      <div className="bg-white dark:bg-gray-900 rounded-xl shadow-2xl w-full max-w-sm">
        <div className="flex items-center justify-between px-5 py-4 border-b border-gray-100 dark:border-gray-800">
          <h2 className="font-semibold text-gray-900 dark:text-white">Create Mailbox</h2>
          <button onClick={onClose} className="p-1.5 rounded hover:bg-gray-100 dark:hover:bg-gray-800"><X className="w-4 h-4 text-gray-500" /></button>
        </div>
        <div className="px-5 py-5 space-y-3">
          {[
            { label: "Local part", val: localPart, set: setLocalPart, ph: "alice", type: "text" },
            { label: "Password", val: password, set: setPassword, ph: "••••••••", type: "password" },
            { label: "Quota (MB)", val: quotaMb, set: setQuotaMb, ph: "1024", type: "number" },
          ].map(({ label, val, set, ph, type }) => (
            <div key={label}>
              <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">{label}</label>
              <input type={type} value={val} onChange={(e) => set(e.target.value)} placeholder={ph}
                className="w-full px-3 py-2 text-sm rounded-lg border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-800 text-gray-900 dark:text-gray-100 focus:outline-none focus:ring-2 focus:ring-indigo-400" />
            </div>
          ))}
        </div>
        <div className="flex justify-end gap-2 px-5 py-4 border-t border-gray-100 dark:border-gray-800">
          <button onClick={onClose} className="px-4 py-2 text-sm rounded-lg text-gray-700 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-800">Cancel</button>
          <button onClick={submit} disabled={busy} className="px-4 py-2 text-sm rounded-lg bg-indigo-600 hover:bg-indigo-700 text-white font-medium disabled:opacity-60">
            {busy ? "Creating…" : "Create"}
          </button>
        </div>
      </div>
    </div>
  );
}
