"use client";

import { useState } from "react";
import { X, Eye, EyeOff } from "lucide-react";
import { domainAdminApi } from "../../lib/api";
import { toast } from "../ui/Toast";

interface ResetPasswordModalProps {
  mailboxId: string;
  mailboxEmail: string;
  onClose: () => void;
}

export function ResetPasswordModal({ mailboxId, mailboxEmail, onClose }: ResetPasswordModalProps) {
  const [password, setPassword] = useState("");
  const [confirmPw, setConfirmPw] = useState("");
  const [showPw, setShowPw] = useState(false);
  const [saving, setSaving] = useState(false);

  async function handleReset() {
    if (password.length < 8) { toast("Password must be at least 8 characters", "error"); return; }
    if (password !== confirmPw) { toast("Passwords do not match", "error"); return; }
    if (!window.confirm(`Reset password for ${mailboxEmail}?`)) return;
    setSaving(true);
    try {
      await domainAdminApi.resetMailboxPassword(mailboxId, password);
      toast("Password reset successfully", "success");
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
          <h2 className="text-lg font-semibold text-gray-900 dark:text-white">Reset Password</h2>
          <button onClick={onClose} className="p-1.5 rounded hover:bg-gray-100 dark:hover:bg-gray-800"><X className="w-5 h-5 text-gray-500" /></button>
        </div>
        <div className="px-6 py-6 space-y-4">
          <p className="text-sm text-gray-600 dark:text-gray-400">Set a new password for <strong>{mailboxEmail}</strong>.</p>
          {[
            { label: "New password", val: password, set: setPassword },
            { label: "Confirm password", val: confirmPw, set: setConfirmPw },
          ].map(({ label, val, set }) => (
            <div key={label}>
              <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">{label}</label>
              <div className="relative">
                <input
                  type={showPw ? "text" : "password"}
                  value={val}
                  onChange={(e) => set(e.target.value)}
                  className="w-full px-3 py-2 pr-10 text-sm rounded-lg border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-800 text-gray-900 dark:text-gray-100 focus:outline-none focus:ring-2 focus:ring-indigo-400"
                />
                <button
                  type="button"
                  onClick={() => setShowPw((o) => !o)}
                  className="absolute right-2.5 top-1/2 -translate-y-1/2 text-gray-400 hover:text-gray-600 dark:hover:text-gray-200"
                >
                  {showPw ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
                </button>
              </div>
            </div>
          ))}
        </div>
        <div className="flex justify-end gap-3 px-6 py-4 border-t border-gray-100 dark:border-gray-800">
          <button onClick={onClose} className="px-4 py-2 text-sm rounded-lg text-gray-700 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-800">Cancel</button>
          <button onClick={handleReset} disabled={saving} className="px-4 py-2 text-sm rounded-lg bg-red-600 hover:bg-red-700 text-white font-medium disabled:opacity-60">
            {saving ? "Resetting…" : "Reset Password"}
          </button>
        </div>
      </div>
    </div>
  );
}
