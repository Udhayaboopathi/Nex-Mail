"use client";

import { useEffect, useState } from "react";
import { X, AtSign } from "lucide-react";
import { domainAdminApi } from "../../lib/api";
import { toast } from "../ui/Toast";

interface CreateMailboxModalProps {
  open: boolean;
  onClose: () => void;
  onCreate: () => void;
}

export default function CreateMailboxModal({ open, onClose, onCreate }: CreateMailboxModalProps) {
  const [domainName, setDomainName] = useState<string | null>(null);
  const [domainLoadErr, setDomainLoadErr] = useState<string | null>(null);
  const [displayName, setDisplayName] = useState("");
  const [localPart, setLocalPart] = useState("");
  const [password, setPassword] = useState("");
  const [quotaMb, setQuotaMb] = useState("1024");
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    if (!open) return;
    setDomainLoadErr(null);
    domainAdminApi
      .getAdminDomain()
      .then((d) => setDomainName(d.name))
      .catch(() => {
        setDomainName(null);
        setDomainLoadErr("Could not load domain. Ensure you are a domain admin with an assigned domain.");
      });
  }, [open]);

  useEffect(() => {
    if (!open) return;
    setDisplayName("");
    setLocalPart("");
    setPassword("");
    setQuotaMb("1024");
  }, [open]);

  if (!open) return null;

  const previewEmail =
    domainName && localPart.trim() ? `${localPart.trim().toLowerCase()}@${domainName}` : null;

  async function submit() {
    if (domainLoadErr || !domainName) {
      toast(domainLoadErr || "Domain not loaded.", "error");
      return;
    }
    const lp = localPart.trim().toLowerCase();
    if (!lp) {
      toast("Enter an email alias (the part before @).", "error");
      return;
    }
    if (password.length < 8) {
      toast("Password must be at least 8 characters.", "error");
      return;
    }
    const q = Number(quotaMb);
    if (!Number.isFinite(q) || q < 64) {
      toast("Storage must be at least 64 MB.", "error");
      return;
    }
    setBusy(true);
    try {
      await domainAdminApi.createMailbox({
        local_part: lp,
        password,
        quota_mb: Math.floor(q),
        display_name: displayName.trim() || undefined,
      });
      toast("Mailbox created!", "success");
      onCreate();
      onClose();
    } catch (err) {
      toast((err as Error).message, "error");
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/50">
      <div className="bg-white dark:bg-gray-900 rounded-xl shadow-2xl w-full max-w-md max-h-[90vh] overflow-y-auto">
        <div className="flex items-center justify-between px-5 py-4 border-b border-gray-100 dark:border-gray-800">
          <h2 className="font-semibold text-gray-900 dark:text-white">Create Mailbox</h2>
          <button type="button" onClick={onClose} className="p-1.5 rounded hover:bg-gray-100 dark:hover:bg-gray-800">
            <X className="w-4 h-4 text-gray-500" />
          </button>
        </div>
        <div className="px-5 py-5 space-y-4">
          {domainLoadErr && (
            <p className="text-sm text-red-600 dark:text-red-400">{domainLoadErr}</p>
          )}
          <div>
            <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">Full name</label>
            <input
              type="text"
              value={displayName}
              onChange={(e) => setDisplayName(e.target.value)}
              placeholder="e.g. UDHAYABOOPATHI V"
              className="w-full px-3 py-2 text-sm rounded-lg border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-800 text-gray-900 dark:text-gray-100 focus:outline-none focus:ring-2 focus:ring-indigo-400"
            />
            <p className="text-xs text-gray-500 dark:text-gray-400 mt-1">Shown as the mailbox owner&apos;s display name.</p>
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">Email alias</label>
            <div className="flex rounded-lg border border-gray-300 dark:border-gray-600 overflow-hidden focus-within:ring-2 focus-within:ring-indigo-400">
              <span className="flex items-center px-2 bg-gray-50 dark:bg-gray-800 text-gray-400">
                <AtSign className="w-4 h-4" />
              </span>
              <input
                type="text"
                value={localPart}
                onChange={(e) => setLocalPart(e.target.value.replace(/\s/g, "").toLowerCase())}
                placeholder="udhaya"
                className="flex-1 min-w-0 px-3 py-2 text-sm bg-white dark:bg-gray-800 text-gray-900 dark:text-gray-100 border-0 focus:ring-0"
                autoComplete="off"
                onKeyDown={(e) => e.key === "Enter" && submit()}
              />
            </div>
            {previewEmail ? (
              <p className="text-xs text-indigo-600 dark:text-indigo-400 mt-1.5 font-mono">
                → {previewEmail}
              </p>
            ) : (
              <p className="text-xs text-gray-500 dark:text-gray-400 mt-1">
                {domainName ? `Address will be alias@${domainName}` : "Loading domain…"}
              </p>
            )}
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">Password</label>
            <input
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              placeholder="At least 8 characters"
              autoComplete="new-password"
              className="w-full px-3 py-2 text-sm rounded-lg border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-800 text-gray-900 dark:text-gray-100 focus:outline-none focus:ring-2 focus:ring-indigo-400"
            />
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">Mailbox storage (MB)</label>
            <input
              type="number"
              min={64}
              value={quotaMb}
              onChange={(e) => setQuotaMb(e.target.value)}
              className="w-full px-3 py-2 text-sm rounded-lg border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-800 text-gray-900 dark:text-gray-100 focus:outline-none focus:ring-2 focus:ring-indigo-400"
            />
            <p className="text-xs text-gray-500 dark:text-gray-400 mt-1">
              1024 MB = 1 GB. Total of all mailboxes cannot exceed the domain pool set by super-admin.
            </p>
          </div>
        </div>
        <div className="flex justify-end gap-2 px-5 py-4 border-t border-gray-100 dark:border-gray-800">
          <button
            type="button"
            onClick={onClose}
            className="px-4 py-2 text-sm rounded-lg text-gray-700 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-800"
          >
            Cancel
          </button>
          <button
            type="button"
            onClick={submit}
            disabled={busy || !!domainLoadErr || !domainName}
            className="px-4 py-2 text-sm rounded-lg bg-indigo-600 hover:bg-indigo-700 text-white font-medium disabled:opacity-60"
          >
            {busy ? "Creating…" : "Create"}
          </button>
        </div>
      </div>
    </div>
  );
}
