"use client";

import { useState, FormEvent } from "react";
import { useParams, useRouter } from "next/navigation";
import { Eye, EyeOff, Mail } from "lucide-react";
import { authApi } from "../../../lib/api";
import { setToken } from "../../../lib/auth";

export default function AcceptInvitePage() {
  const { token } = useParams<{ token: string }>();
  const router = useRouter();
  const [password, setPassword] = useState("");
  const [confirm, setConfirm] = useState("");
  const [showPw, setShowPw] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  async function handleSubmit(e: FormEvent) {
    e.preventDefault();
    if (password.length < 8) { setError("Min 8 characters"); return; }
    if (password !== confirm) { setError("Passwords do not match"); return; }
    setError(""); setLoading(true);
    try {
      const res = await authApi.acceptInvite(token, password);
      setToken(res.access_token, res.role ?? "user");
      router.push("/mail/inbox");
    } catch (err) { setError((err as Error).message); }
    finally { setLoading(false); }
  }

  return (
    <div className="min-h-screen bg-gradient-to-br from-indigo-50 via-white to-purple-50 dark:from-gray-950 dark:via-gray-900 dark:to-indigo-950 flex items-center justify-center p-4">
      <div className="w-full max-w-sm">
        <div className="text-center mb-8">
          <div className="inline-flex items-center justify-center w-14 h-14 bg-indigo-600 rounded-2xl mb-4 shadow-lg"><Mail className="w-7 h-7 text-white" /></div>
          <h1 className="text-2xl font-bold text-gray-900 dark:text-white">Accept Invitation</h1>
          <p className="text-gray-500 dark:text-gray-400 text-sm mt-1">Create a password to get started.</p>
        </div>
        <div className="bg-white dark:bg-gray-900 rounded-2xl shadow-xl border border-gray-100 dark:border-gray-800 p-8">
          <form onSubmit={handleSubmit} className="space-y-4">
            {[{ label: "Password", val: password, set: setPassword }, { label: "Confirm", val: confirm, set: setConfirm }].map(({ label, val, set }) => (
              <div key={label}>
                <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">{label}</label>
                <div className="relative">
                  <input type={showPw ? "text" : "password"} value={val} onChange={(e) => set(e.target.value)} required
                    className="w-full px-4 py-2.5 pr-11 rounded-lg border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-800 text-gray-900 dark:text-gray-100 focus:outline-none focus:ring-2 focus:ring-indigo-400 text-sm" />
                  <button type="button" onClick={() => setShowPw((o) => !o)} className="absolute right-3 top-1/2 -translate-y-1/2 text-gray-400">
                    {showPw ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
                  </button>
                </div>
              </div>
            ))}
            {error && <p className="text-sm text-red-600 dark:text-red-400">{error}</p>}
            <button type="submit" disabled={loading} className="w-full py-2.5 rounded-lg bg-indigo-600 hover:bg-indigo-700 text-white font-medium disabled:opacity-60">
              {loading ? "Setting up…" : "Create Account"}
            </button>
          </form>
        </div>
      </div>
    </div>
  );
}
