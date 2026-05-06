"use client";

import { useState } from "react";
import { X, UserCheck, KeyRound, Cloud } from "lucide-react";
import { superAdminApi } from "../../lib/api";
import { toast } from "../ui/Toast";

function isConsumerGmail(email: string): boolean {
  const x = email.toLowerCase().trim();
  return x.endsWith("@gmail.com") || x.endsWith("@googlemail.com");
}

interface AssignAdminModalProps {
  domainId: string;
  domainName: string;
  onClose: () => void;
  onAssigned: () => void;
}

export function AssignAdminModal({ domainId, domainName, onClose, onAssigned }: AssignAdminModalProps) {
  const [cloudflareToken, setCloudflareToken] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [saving, setSaving] = useState(false);

  async function handleAssign() {
    const token = cloudflareToken.trim();
    if (!token) {
      toast("Enter the Cloudflare API token", "error");
      return;
    }
    if (!email.trim()) {
      toast("Enter an email address", "error");
      return;
    }
    if (password.length < 8) {
      toast("Password must be at least 8 characters", "error");
      return;
    }
    setSaving(true);
    try {
      const res = await superAdminApi.assignAdmin(domainId, {
        email: email.trim(),
        password,
        cloudflare_api_token: token,
      });
      toast(`Admin assigned for ${domainName}`, "success");
      if (isConsumerGmail(email)) {
        if (res.welcome_email_sent) {
          toast("Login details were emailed to the Gmail address.", "success");
        } else if (res.welcome_email_error) {
          toast(`Assigned, but email failed: ${res.welcome_email_error}`, "error");
        }
      }
      onAssigned();
      onClose();
    } catch (err) {
      toast((err as Error).message, "error");
    } finally {
      setSaving(false);
    }
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/50">
      <div className="bg-white dark:bg-gray-900 rounded-xl shadow-2xl w-full max-w-md max-h-[90vh] overflow-y-auto">
        <div className="flex items-center justify-between px-6 py-4 border-b border-gray-100 dark:border-gray-800">
          <h2 className="text-lg font-semibold text-gray-900 dark:text-white">Assign Domain Admin</h2>
          <button type="button" onClick={onClose} className="p-1.5 rounded hover:bg-gray-100 dark:hover:bg-gray-800">
            <X className="w-5 h-5 text-gray-500" />
          </button>
        </div>
        <div className="px-6 py-6 space-y-4">
          <div className="flex items-center gap-2 p-3 bg-blue-50 dark:bg-blue-900/20 rounded-lg text-blue-700 dark:text-blue-300 text-sm">
            <UserCheck className="w-5 h-5 shrink-0" />
            <span>
              Set admin for <strong>{domainName}</strong>. The Cloudflare token is stored encrypted for DNS automation.
              If the admin email is <strong>Gmail</strong>, login URL and password are emailed automatically.
            </span>
          </div>
          <div>
            <label className="flex items-center gap-1.5 text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
              <Cloud className="w-4 h-4" /> Cloudflare API token
            </label>
            <input
              value={cloudflareToken}
              onChange={(e) => setCloudflareToken(e.target.value)}
              placeholder="API token (Zone:DNS:Edit or broader)"
              type="password"
              autoComplete="off"
              className="w-full px-3 py-2 text-sm rounded-lg border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-800 text-gray-900 dark:text-gray-100 focus:outline-none focus:ring-2 focus:ring-indigo-400"
            />
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">Admin email (login ID)</label>
            <input
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              placeholder="admin@example.com or name@gmail.com"
              type="email"
              onKeyDown={(e) => e.key === "Enter" && handleAssign()}
              className="w-full px-3 py-2 text-sm rounded-lg border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-800 text-gray-900 dark:text-gray-100 focus:outline-none focus:ring-2 focus:ring-indigo-400"
            />
          </div>
          <div>
            <label className="flex items-center gap-1.5 text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
              <KeyRound className="w-4 h-4" /> Password
            </label>
            <input
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              placeholder="At least 8 characters"
              type="password"
              autoComplete="new-password"
              onKeyDown={(e) => e.key === "Enter" && handleAssign()}
              className="w-full px-3 py-2 text-sm rounded-lg border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-800 text-gray-900 dark:text-gray-100 focus:outline-none focus:ring-2 focus:ring-indigo-400"
            />
          </div>
        </div>
        <div className="flex justify-end gap-3 px-6 py-4 border-t border-gray-100 dark:border-gray-800">
          <button type="button" onClick={onClose} className="px-4 py-2 text-sm rounded-lg text-gray-700 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-800">
            Cancel
          </button>
          <button
            type="button"
            onClick={handleAssign}
            disabled={saving}
            className="px-4 py-2 text-sm rounded-lg bg-indigo-600 hover:bg-indigo-700 text-white font-medium disabled:opacity-60"
          >
            {saving ? "Assigning…" : "Assign Admin"}
          </button>
        </div>
      </div>
    </div>
  );
}
