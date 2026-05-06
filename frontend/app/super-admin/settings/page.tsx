"use client";

import { useEffect, useState } from "react";
import { Mail } from "lucide-react";
import { superAdminApi } from "../../../lib/api";
import { toast } from "../../../components/ui/Toast";

export default function SuperAdminSettings() {
  const [status, setStatus] = useState<{
    submission_configured: boolean;
    host: string | null;
    port: number | null;
    from_hint: string | null;
  } | null>(null);
  const [to, setTo] = useState("");
  const [loadingStatus, setLoadingStatus] = useState(true);
  const [sending, setSending] = useState(false);

  useEffect(() => {
    let cancelled = false;
    (async () => {
      setLoadingStatus(true);
      try {
        const s = await superAdminApi.getMailTestStatus();
        if (!cancelled) setStatus(s);
      } catch (e) {
        if (!cancelled) toast((e as Error).message, "error");
      } finally {
        if (!cancelled) setLoadingStatus(false);
      }
    })();
    return () => {
      cancelled = true;
    };
  }, []);

  async function handleSendTest() {
    const addr = to.trim();
    if (!addr) {
      toast("Enter a recipient address", "error");
      return;
    }
    setSending(true);
    try {
      const res = await superAdminApi.sendTestMail(addr);
      toast(res.detail ?? "Test message sent.", "success");
    } catch (err) {
      toast((err as Error).message, "error");
    } finally {
      setSending(false);
    }
  }

  return (
    <div className="space-y-6 max-w-2xl">
      <div>
        <h1 className="text-2xl font-bold text-gray-900 dark:text-white">Platform Settings</h1>
        <p className="text-sm text-gray-500 dark:text-gray-400 mt-0.5">Global configuration</p>
      </div>
      <div className="bg-white dark:bg-gray-900 rounded-xl border border-gray-100 dark:border-gray-800 p-6 space-y-4">
        <p className="text-sm text-gray-500 dark:text-gray-400">
          Most settings come from environment variables in{" "}
          <code className="bg-gray-100 dark:bg-gray-800 px-1.5 py-0.5 rounded text-xs">.env</code> on the server.
        </p>
      </div>

      <div className="bg-white dark:bg-gray-900 rounded-xl border border-gray-100 dark:border-gray-800 p-6 space-y-4">
        <div className="flex items-center gap-2">
          <Mail className="w-5 h-5 text-indigo-600 dark:text-indigo-400" />
          <h2 className="text-lg font-semibold text-gray-900 dark:text-white">Test outbound mail (SMTP submission)</h2>
        </div>
        <p className="text-sm text-gray-500 dark:text-gray-400">
          Uses <strong>authenticated SMTP</strong> (port 587 + STARTTLS by default), not direct MX on port 25. Configure{" "}
          <code className="text-xs bg-gray-100 dark:bg-gray-800 px-1 rounded">SMTP_SUBMISSION_*</code> on the backend host,
          then send a message to any inbox you control.
        </p>
        {loadingStatus ? (
          <p className="text-sm text-gray-500">Loading mail configuration…</p>
        ) : status?.submission_configured ? (
          <div className="rounded-lg bg-emerald-50 dark:bg-emerald-950/30 border border-emerald-200 dark:border-emerald-800 px-3 py-2 text-sm text-emerald-800 dark:text-emerald-200">
            Ready: <span className="font-mono">{status.host}:{status.port}</span>
            {status.from_hint ? (
              <>
                {" "}
                · From: <span className="font-mono">{status.from_hint}</span>
              </>
            ) : null}
          </div>
        ) : (
          <div className="rounded-lg bg-amber-50 dark:bg-amber-950/30 border border-amber-200 dark:border-amber-800 px-3 py-2 text-sm text-amber-900 dark:text-amber-100">
            SMTP submission is not configured. Add to server <code className="text-xs">.env</code>:{" "}
            <code className="text-xs">SMTP_SUBMISSION_HOST</code>, <code className="text-xs">SMTP_SUBMISSION_USER</code>,{" "}
            <code className="text-xs">SMTP_SUBMISSION_PASSWORD</code>. Optional:{" "}
            <code className="text-xs">SMTP_TEST_MAIL_FROM</code>, <code className="text-xs">SMTP_SUBMISSION_PORT</code>,{" "}
            <code className="text-xs">SMTP_SUBMISSION_USE_TLS</code>. Restart the backend after changes.
          </div>
        )}
        <div className="flex flex-col sm:flex-row gap-3 sm:items-end">
          <div className="flex-1">
            <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">Recipient</label>
            <input
              type="email"
              value={to}
              onChange={(e) => setTo(e.target.value)}
              placeholder="you@gmail.com"
              className="w-full px-3 py-2 text-sm rounded-lg border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-800 text-gray-900 dark:text-gray-100 focus:outline-none focus:ring-2 focus:ring-indigo-400"
            />
          </div>
          <button
            type="button"
            onClick={handleSendTest}
            disabled={sending || !status?.submission_configured}
            className="px-4 py-2 text-sm rounded-lg bg-indigo-600 hover:bg-indigo-700 text-white font-medium disabled:opacity-50 disabled:cursor-not-allowed"
          >
            {sending ? "Sending…" : "Send test email"}
          </button>
        </div>
      </div>
    </div>
  );
}
