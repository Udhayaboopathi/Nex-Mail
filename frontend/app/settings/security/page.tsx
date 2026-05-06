"use client";

import { useEffect, useState } from "react";
import { Shield, Smartphone, Key, LogOut } from "lucide-react";
import { authApi } from "../../../lib/api";
import { toast } from "../../../components/ui/Toast";
import { Badge } from "../../../components/ui/Badge";
import { formatDate } from "../../../lib/utils";
import type { LoginActivity, ActiveSession } from "../../../types";

export default function SecurityPage() {
  const [activity, setActivity] = useState<LoginActivity[]>([]);
  const [sessions, setSessions] = useState<ActiveSession[]>([]);
  const [totpSetup, setTotpSetup] = useState<{ secret: string; qr_uri: string; backup_codes: string[] } | null>(null);
  const [totpCode, setTotpCode] = useState("");
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    Promise.all([authApi.getLoginActivity(), authApi.getSessions()])
      .then(([a, s]) => { setActivity(a); setSessions(s); })
      .catch(() => undefined)
      .finally(() => setLoading(false));
  }, []);

  async function handleSetupTotp() {
    try { setTotpSetup(await authApi.setupTotp()); }
    catch (e) { toast((e as Error).message, "error"); }
  }

  async function handleEnableTotp() {
    try { await authApi.enableTotp(totpCode); toast("2FA enabled!", "success"); setTotpSetup(null); }
    catch { toast("Invalid code", "error"); }
  }

  async function revokeSession(id: string) {
    try { await authApi.deleteSession(id); setSessions((p) => p.filter((s) => s.id !== id)); toast("Session revoked", "success"); }
    catch (e) { toast((e as Error).message, "error"); }
  }

  return (
    <div className="max-w-2xl mx-auto p-6 space-y-8">
      <h1 className="text-2xl font-bold text-gray-900 dark:text-white">Security</h1>

      {/* 2FA */}
      <section className="bg-white dark:bg-gray-900 rounded-xl border border-gray-100 dark:border-gray-800 p-6 space-y-4">
        <div className="flex items-center gap-2">
          <Smartphone className="w-5 h-5 text-indigo-600 dark:text-indigo-400" />
          <h2 className="font-semibold text-gray-800 dark:text-white">Two-Factor Authentication</h2>
        </div>
        {totpSetup ? (
          <div className="space-y-3">
            {/* eslint-disable-next-line @next/next/no-img-element */}
            <img src={totpSetup.qr_uri} alt="TOTP QR" className="w-40 h-40 rounded-lg border" />
            <p className="text-xs font-mono bg-gray-50 dark:bg-gray-800 p-2 rounded break-all">{totpSetup.secret}</p>
            <div className="flex gap-2">
              <input value={totpCode} onChange={(e) => setTotpCode(e.target.value.slice(0,6))} placeholder="6-digit code" maxLength={6}
                className="flex-1 px-3 py-2 text-sm rounded-lg border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-800 text-gray-900 dark:text-gray-100 focus:outline-none focus:ring-2 focus:ring-indigo-400" />
              <button onClick={handleEnableTotp} disabled={totpCode.length < 6} className="px-4 py-2 rounded-lg bg-indigo-600 hover:bg-indigo-700 text-white text-sm font-medium disabled:opacity-60">Enable</button>
            </div>
          </div>
        ) : (
          <button onClick={handleSetupTotp} className="flex items-center gap-2 px-4 py-2 rounded-lg border border-indigo-300 dark:border-indigo-600 text-indigo-600 dark:text-indigo-400 text-sm hover:bg-indigo-50 dark:hover:bg-indigo-900/20">
            <Shield className="w-4 h-4" /> Set up 2FA
          </button>
        )}
      </section>

      {/* Sessions */}
      <section className="bg-white dark:bg-gray-900 rounded-xl border border-gray-100 dark:border-gray-800 p-6 space-y-3">
        <div className="flex items-center gap-2">
          <Key className="w-5 h-5 text-indigo-600 dark:text-indigo-400" />
          <h2 className="font-semibold text-gray-800 dark:text-white">Active Sessions ({sessions.length})</h2>
        </div>
        {loading ? <div className="h-16 bg-gray-100 dark:bg-gray-800 rounded animate-pulse" /> : sessions.map((s) => (
          <div key={s.id} className="flex items-center justify-between p-3 rounded-lg bg-gray-50 dark:bg-gray-800">
            <div>
              <p className="text-sm text-gray-800 dark:text-gray-200">{s.ip_address}</p>
              <p className="text-xs text-gray-400">{formatDate(s.created_at)}</p>
            </div>
            <button onClick={() => revokeSession(s.id)} className="p-1.5 rounded hover:bg-gray-200 dark:hover:bg-gray-700">
              <LogOut className="w-4 h-4 text-red-500" />
            </button>
          </div>
        ))}
      </section>

      {/* Login activity */}
      <section className="bg-white dark:bg-gray-900 rounded-xl border border-gray-100 dark:border-gray-800 p-6 space-y-3">
        <h2 className="font-semibold text-gray-800 dark:text-white">Login Activity</h2>
        {loading ? <div className="h-24 bg-gray-100 dark:bg-gray-800 rounded animate-pulse" /> : activity.slice(0, 20).map((a) => (
          <div key={a.id} className="flex items-center justify-between py-2 border-b border-gray-50 dark:border-gray-800 last:border-0">
            <div>
              <p className="text-sm text-gray-700 dark:text-gray-300">{a.ip_address} — {a.device_type}</p>
              <p className="text-xs text-gray-400">{formatDate(a.created_at)}</p>
            </div>
            <Badge variant={a.success ? "success" : "danger"}>{a.success ? "OK" : "Failed"}</Badge>
          </div>
        ))}
      </section>
    </div>
  );
}
