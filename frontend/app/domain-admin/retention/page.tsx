"use client";

import { useEffect, useState } from "react";
import { AlertTriangle } from "lucide-react";
import { domainAdminApi } from "../../../lib/api";
import { toast } from "../../../components/ui/Toast";

export default function RetentionPage() {
  const [days, setDays] = useState(0);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    domainAdminApi.getRetention().then((r) => setDays((r as { retention_days: number }).retention_days)).catch(() => undefined).finally(() => setLoading(false));
  }, []);

  async function handleSave() {
    if (!confirm(days === 0 ? "Disable retention (keep emails forever)?" : `Delete emails older than ${days} days?`)) return;
    setSaving(true);
    try {
      await domainAdminApi.updateRetention({ retention_days: days });
      toast("Retention policy updated", "success");
    } catch (e) { toast((e as Error).message, "error"); }
    finally { setSaving(false); }
  }

  return (
    <div className="space-y-6 max-w-xl">
      <div>
        <h1 className="text-2xl font-bold text-gray-900 dark:text-white">Email Retention</h1>
        <p className="text-sm text-gray-500 dark:text-gray-400 mt-0.5">Auto-delete emails after a specified number of days.</p>
      </div>

      {loading ? <div className="h-24 bg-white dark:bg-gray-900 rounded-xl animate-pulse" /> : (
        <div className="bg-white dark:bg-gray-900 rounded-xl border border-gray-100 dark:border-gray-800 p-6 space-y-5">
          <div>
            <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
              Retention period: {days === 0 ? <span className="text-green-600 dark:text-green-400">Forever (disabled)</span> : <span className="text-yellow-600 dark:text-yellow-400">{days} days</span>}
            </label>
            <input type="range" min={0} max={3650} step={30} value={days} onChange={(e) => setDays(Number(e.target.value))} className="w-full accent-indigo-600" />
            <div className="flex justify-between text-xs text-gray-400 mt-1"><span>Off</span><span>1 yr</span><span>5 yr</span><span>10 yr</span></div>
          </div>

          {days > 0 && (
            <div className="flex items-start gap-3 p-3 bg-red-50 dark:bg-red-900/20 rounded-lg border border-red-200 dark:border-red-800">
              <AlertTriangle className="w-5 h-5 text-red-600 shrink-0 mt-0.5" />
              <p className="text-sm text-red-700 dark:text-red-400">
                Emails older than <strong>{days} days</strong> will be permanently deleted. This cannot be undone.
              </p>
            </div>
          )}

          <button onClick={handleSave} disabled={saving} className="px-5 py-2.5 rounded-lg bg-indigo-600 hover:bg-indigo-700 text-white text-sm font-medium disabled:opacity-60">
            {saving ? "Saving…" : "Save Policy"}
          </button>
        </div>
      )}
    </div>
  );
}
