"use client";

import { useEffect, useState } from "react";
import { CheckCircle, XCircle, RefreshCcw, Zap } from "lucide-react";
import { domainAdminApi } from "../../../lib/api";
import { toast } from "../../../components/ui/Toast";
import type { DnsStatus } from "../../../types";

export default function DnsPage() {
  const [status, setStatus] = useState<DnsStatus | null>(null);
  const [loading, setLoading] = useState(true);
  const [verifying, setVerifying] = useState(false);
  const [autoing, setAutoing] = useState(false);

  async function load() {
    setLoading(true);
    try { setStatus(await domainAdminApi.getDnsStatus()); }
    catch { /* ignore */ }
    finally { setLoading(false); }
  }

  async function verify() {
    setVerifying(true);
    try {
      const res = await domainAdminApi.verifyDns();
      setStatus(res);
      toast(res.all_valid ? "All DNS records valid!" : "Some records still missing", res.all_valid ? "success" : "error");
    } catch (e) { toast((e as Error).message, "error"); }
    finally { setVerifying(false); }
  }

  async function autoDns() {
    setAutoing(true);
    try {
      await domainAdminApi.autoDns();
      toast("Cloudflare auto-config applied", "success");
      load();
    } catch (e) { toast((e as Error).message, "error"); }
    finally { setAutoing(false); }
  }

  useEffect(() => { load(); }, []);

  const records = status ? [
    { key: "MX", ...status.mx },
    { key: "A", ...status.a },
    { key: "SPF", ...status.spf },
    { key: "DKIM", ...status.dkim },
    { key: "DMARC", ...status.dmarc },
  ] : [];

  return (
    <div className="space-y-6 max-w-3xl">
      <div className="flex items-center justify-between flex-wrap gap-3">
        <div>
          <h1 className="text-2xl font-bold text-gray-900 dark:text-white">DNS Status</h1>
          {status && (
            <p className={`text-sm mt-0.5 ${status.all_valid ? "text-green-600 dark:text-green-400" : "text-yellow-600 dark:text-yellow-400"}`}>
              {status.all_valid ? "✓ All records verified" : "⚠ Some records need attention"}
            </p>
          )}
        </div>
        <div className="flex gap-2">
          <button onClick={load} className="p-2 rounded-lg border border-gray-300 dark:border-gray-600 hover:bg-gray-50 dark:hover:bg-gray-800">
            <RefreshCcw className="w-4 h-4 text-gray-600 dark:text-gray-400" />
          </button>
          <button onClick={autoDns} disabled={autoing} className="flex items-center gap-2 px-3 py-2 rounded-lg border border-indigo-300 dark:border-indigo-600 text-indigo-600 dark:text-indigo-400 text-sm hover:bg-indigo-50 dark:hover:bg-indigo-900/20 disabled:opacity-60">
            <Zap className="w-4 h-4" /> {autoing ? "Configuring…" : "Auto-configure"}
          </button>
          <button onClick={verify} disabled={verifying} className="flex items-center gap-2 px-3 py-2 rounded-lg bg-indigo-600 hover:bg-indigo-700 text-white text-sm font-medium disabled:opacity-60">
            {verifying ? "Verifying…" : "Verify DNS"}
          </button>
        </div>
      </div>

      {loading ? (
        <div className="space-y-3">{[1,2,3,4,5].map((i) => <div key={i} className="h-16 bg-white dark:bg-gray-900 rounded-xl animate-pulse" />)}</div>
      ) : (
        <div className="space-y-3">
          {records.map((r) => (
            <div key={r.key} className={`bg-white dark:bg-gray-900 rounded-xl p-4 border ${r.valid ? "border-green-200 dark:border-green-800" : "border-red-200 dark:border-red-800"}`}>
              <div className="flex items-center gap-3">
                {r.valid ? <CheckCircle className="w-5 h-5 text-green-500 shrink-0" /> : <XCircle className="w-5 h-5 text-red-500 shrink-0" />}
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2 mb-0.5">
                    <span className="text-xs font-bold bg-gray-100 dark:bg-gray-800 text-gray-600 dark:text-gray-400 px-1.5 py-0.5 rounded">{r.type}</span>
                    <span className="font-medium text-gray-800 dark:text-gray-200 text-sm">{r.key}</span>
                  </div>
                  <p className="text-xs font-mono text-gray-500 dark:text-gray-400 truncate">{r.value}</p>
                  {!r.valid && r.current && <p className="text-xs text-red-500 mt-0.5">Current: {r.current}</p>}
                </div>
              </div>
            </div>
          ))}
          {status?.ptr && (
            <div className="p-4 rounded-xl bg-amber-50 dark:bg-amber-900/20 border border-amber-200 dark:border-amber-800 text-sm text-amber-700 dark:text-amber-400">
              <strong>PTR (Reverse DNS):</strong> Set in VPS panel → {status.ptr}
            </div>
          )}
        </div>
      )}
    </div>
  );
}
