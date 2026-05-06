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
    submission_tcp_target: string | null;
    outbound_relay_configured: boolean;
    outbound_relay_ready: boolean;
    outbound_relay_host: string | null;
    outbound_relay_port: number | null;
    can_send_test_mail: boolean;
    mail_test_sends_via: string | null;
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
          The test uses <strong>your Nex Mail server first</strong> (<code className="text-xs bg-gray-100 dark:bg-gray-800 px-1 rounded">SMTP_SUBMISSION_*</code>, port 587).
          Outbound mail tries <strong>direct MX</strong> from your IP, then{" "}
          <code className="text-xs bg-gray-100 dark:bg-gray-800 px-1 rounded">SMTP_OUTBOUND_RELAY_*</code> only if that fails.
          On Docker, set <code className="text-xs bg-gray-100 dark:bg-gray-800 px-1 rounded">SMTP_SUBMISSION_CONNECT_HOST=127.0.0.1</code>{" "}
          if submission to your public hostname times out.
        </p>
        {loadingStatus ? (
          <p className="text-sm text-gray-500">Loading mail configuration…</p>
        ) : status?.can_send_test_mail ? (
          <div className="rounded-lg bg-emerald-50 dark:bg-emerald-950/30 border border-emerald-200 dark:border-emerald-800 px-3 py-2 text-sm text-emerald-800 dark:text-emerald-200 space-y-1">
            {status.mail_test_sends_via === "outbound_relay" ? (
              <div>
                Super-admin test sends via <strong>outbound relay</strong>{" "}
                <span className="font-mono">
                  {status.outbound_relay_host}:{status.outbound_relay_port ?? 587}
                </span>
                {status.from_hint ? (
                  <>
                    {" "}
                    · From: <span className="font-mono">{status.from_hint}</span>
                  </>
                ) : null}
              </div>
            ) : (
              <div>
                Super-admin test sends via <strong>local submission</strong>{" "}
                <span className="font-mono">
                  {status.host}:{status.port}
                </span>
                {status.from_hint ? (
                  <>
                    {" "}
                    · From: <span className="font-mono">{status.from_hint}</span>
                  </>
                ) : null}
              </div>
            )}
            {status.mail_test_sends_via === "local_submission" &&
            status.submission_tcp_target &&
            status.host &&
            status.submission_tcp_target !== status.host ? (
              <div className="text-emerald-700 dark:text-emerald-300">
                TCP connect: <span className="font-mono">{status.submission_tcp_target}:{status.port}</span> (logical:{" "}
                <span className="font-mono">{status.host}</span>)
              </div>
            ) : null}
            {status.outbound_relay_ready && status.outbound_relay_host ? (
              <div className="text-emerald-700 dark:text-emerald-300">
                Smarthost fallback (after direct MX fails):{" "}
                <span className="font-mono">
                  {status.outbound_relay_host}:{status.outbound_relay_port ?? 587}
                </span>
              </div>
            ) : null}
          </div>
        ) : (
          <div className="rounded-lg bg-amber-50 dark:bg-amber-950/30 border border-amber-200 dark:border-amber-800 px-3 py-2 text-sm text-amber-900 dark:text-amber-100">
            Cannot send a test email yet. On the server <code className="text-xs">.env</code> set either full{" "}
            <code className="text-xs">SMTP_OUTBOUND_RELAY_*</code> (host, user, password — e.g. Brevo), or{" "}
            <code className="text-xs">SMTP_SUBMISSION_HOST</code> and <code className="text-xs">SMTP_SUBMISSION_USER</code> for local
            :587. Also set <code className="text-xs">SMTP_TEST_MAIL_FROM</code> or <code className="text-xs">SUPER_ADMIN_EMAIL</code>.
            Copy the same <code className="text-xs">.env</code> to the VPS and{" "}
            <strong>restart the backend</strong> (<code className="text-xs">docker compose up -d --force-recreate backend</code>).
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
            disabled={sending || !status?.can_send_test_mail}
            className="px-4 py-2 text-sm rounded-lg bg-indigo-600 hover:bg-indigo-700 text-white font-medium disabled:opacity-50 disabled:cursor-not-allowed"
          >
            {sending ? "Sending…" : "Send test email"}
          </button>
        </div>
      </div>
    </div>
  );
}
