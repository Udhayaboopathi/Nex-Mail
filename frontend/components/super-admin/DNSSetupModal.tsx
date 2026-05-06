"use client";

import { useState, useEffect } from "react";
import { X, CheckCircle, XCircle, RefreshCcw } from "lucide-react";
import { superAdminApi } from "../../lib/api";
import { toast } from "../ui/Toast";
import type { DnsStatus } from "../../types";

interface DNSSetupModalProps {
  domainId: string;
  domainName: string;
  onClose: () => void;
}

export function DNSSetupModal({ domainId, domainName, onClose }: DNSSetupModalProps) {
  const [status, setStatus] = useState<DnsStatus | null>(null);
  const [loading, setLoading] = useState(true);
  const [verifying, setVerifying] = useState(false);

  async function loadStatus() {
    setLoading(true);
    try {
      const guide = await superAdminApi.getDnsGuide(domainId) as DnsStatus;
      setStatus(guide);
    } catch { /* ignore */ }
    finally { setLoading(false); }
  }

  async function handleVerify() {
    setVerifying(true);
    try {
      const result = await superAdminApi.verifyDns(domainId);
      setStatus(result);
      toast(result.all_valid ? "All DNS records verified!" : "Some records still invalid", result.all_valid ? "success" : "error");
    } catch (err) {
      toast((err as Error).message, "error");
    } finally {
      setVerifying(false);
    }
  }

  useEffect(() => { loadStatus(); }, []);

  const records = status
    ? [
        { label: "MX", ...status.mx },
        { label: "A", ...status.a },
        { label: "SPF", ...status.spf },
        { label: "DKIM", ...status.dkim },
        { label: "DMARC", ...status.dmarc },
      ]
    : [];

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/50">
      <div className="bg-white dark:bg-gray-900 rounded-xl shadow-2xl w-full max-w-2xl max-h-[90vh] flex flex-col">
        <div className="flex items-center justify-between px-6 py-4 border-b border-gray-100 dark:border-gray-800">
          <h2 className="text-lg font-semibold text-gray-900 dark:text-white">DNS Setup — {domainName}</h2>
          <button onClick={onClose} className="p-1.5 rounded hover:bg-gray-100 dark:hover:bg-gray-800"><X className="w-5 h-5 text-gray-500" /></button>
        </div>

        <div className="flex-1 overflow-y-auto px-6 py-4">
          {loading ? (
            <div className="space-y-3 animate-pulse">
              {[1, 2, 3, 4, 5].map((i) => <div key={i} className="h-12 bg-gray-100 dark:bg-gray-800 rounded-lg" />)}
            </div>
          ) : (
            <div className="space-y-3">
              {records.map((r) => (
                <div key={r.label} className="flex items-center gap-3 p-3 rounded-lg border border-gray-200 dark:border-gray-700">
                  {r.valid
                    ? <CheckCircle className="w-5 h-5 text-green-500 shrink-0" />
                    : <XCircle className="w-5 h-5 text-red-500 shrink-0" />}
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2">
                      <span className="text-xs font-bold bg-gray-100 dark:bg-gray-800 text-gray-600 dark:text-gray-400 px-1.5 py-0.5 rounded">{r.type}</span>
                      <span className="text-sm font-medium text-gray-800 dark:text-gray-200">{r.label}</span>
                      {r.valid && <span className="text-xs text-green-600 dark:text-green-400">✓ Valid</span>}
                    </div>
                    <p className="text-xs text-gray-500 dark:text-gray-400 mt-0.5 truncate font-mono">{r.value}</p>
                    {!r.valid && r.current && (
                      <p className="text-xs text-red-500 mt-0.5">Current: {r.current}</p>
                    )}
                  </div>
                </div>
              ))}
              {status?.ptr && (
                <div className="p-3 rounded-lg bg-amber-50 dark:bg-amber-900/20 text-sm text-amber-700 dark:text-amber-400">
                  <strong>PTR:</strong> Set reverse DNS in your VPS control panel → {status.ptr}
                </div>
              )}
            </div>
          )}
        </div>

        <div className="flex items-center justify-between px-6 py-4 border-t border-gray-100 dark:border-gray-800">
          <button onClick={loadStatus} className="flex items-center gap-2 text-sm text-gray-500 hover:text-gray-700 dark:hover:text-gray-300">
            <RefreshCcw className="w-4 h-4" /> Refresh
          </button>
          <div className="flex gap-3">
            <button onClick={onClose} className="px-4 py-2 text-sm rounded-lg text-gray-700 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-800">Close</button>
            <button onClick={handleVerify} disabled={verifying} className="px-4 py-2 text-sm rounded-lg bg-indigo-600 hover:bg-indigo-700 text-white font-medium disabled:opacity-60">
              {verifying ? "Verifying…" : "Verify DNS"}
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
