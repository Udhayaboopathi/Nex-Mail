"use client";

import { useState } from "react";
import { X } from "lucide-react";
import { domainAdminApi } from "../../lib/api";
import { toast } from "../ui/Toast";

interface CreateAliasModalProps {
  open: boolean;
  domainId?: string;
  onClose: () => void;
  onCreate: () => void;
}

export default function CreateAliasModal({ open, onClose, onCreate }: CreateAliasModalProps) {
  const [source, setSource] = useState("");
  const [destination, setDestination] = useState("");
  const [isCatchAll, setIsCatchAll] = useState(false);
  const [busy, setBusy] = useState(false);

  if (!open) return null;

  async function submit() {
    if (!destination.trim()) { toast("Destination is required", "error"); return; }
    setBusy(true);
    try {
      await domainAdminApi.createAlias({ source_address: source.trim(), destination_address: destination.trim(), is_catch_all: isCatchAll });
      toast("Alias created!", "success");
      onCreate();
      setSource(""); setDestination(""); setIsCatchAll(false);
      onClose();
    } catch (err) { toast((err as Error).message, "error"); }
    finally { setBusy(false); }
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/50">
      <div className="bg-white dark:bg-gray-900 rounded-xl shadow-2xl w-full max-w-sm">
        <div className="flex items-center justify-between px-5 py-4 border-b border-gray-100 dark:border-gray-800">
          <h2 className="font-semibold text-gray-900 dark:text-white">Create Alias</h2>
          <button onClick={onClose} className="p-1.5 rounded hover:bg-gray-100 dark:hover:bg-gray-800"><X className="w-4 h-4 text-gray-500" /></button>
        </div>
        <div className="px-5 py-5 space-y-3">
          <div>
            <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">Source address</label>
            <input value={source} onChange={(e) => setSource(e.target.value)} placeholder="info@example.com (or leave blank for catch-all)"
              className="w-full px-3 py-2 text-sm rounded-lg border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-800 text-gray-900 dark:text-gray-100 focus:outline-none focus:ring-2 focus:ring-indigo-400" />
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">Destination address</label>
            <input value={destination} onChange={(e) => setDestination(e.target.value)} placeholder="alice@example.com"
              className="w-full px-3 py-2 text-sm rounded-lg border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-800 text-gray-900 dark:text-gray-100 focus:outline-none focus:ring-2 focus:ring-indigo-400" />
          </div>
          <label className="flex items-center gap-2 text-sm text-gray-700 dark:text-gray-300 cursor-pointer">
            <input type="checkbox" checked={isCatchAll} onChange={(e) => setIsCatchAll(e.target.checked)} className="accent-indigo-600" />
            Catch-all (forward all unmatched addresses)
          </label>
        </div>
        <div className="flex justify-end gap-2 px-5 py-4 border-t border-gray-100 dark:border-gray-800">
          <button onClick={onClose} className="px-4 py-2 text-sm rounded-lg text-gray-700 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-800">Cancel</button>
          <button onClick={submit} disabled={busy} className="px-4 py-2 text-sm rounded-lg bg-indigo-600 hover:bg-indigo-700 text-white font-medium disabled:opacity-60">
            {busy ? "Creating…" : "Create Alias"}
          </button>
        </div>
      </div>
    </div>
  );
}
