"use client";

import { useEffect, useState } from "react";
import { domainAdminApi } from "../../../lib/api";
import { toast } from "../../../components/ui/Toast";

interface WhitelabelData {
  whitelabel_company_name: string;
  whitelabel_primary_color: string;
  whitelabel_logo_url: string;
}

export default function WhitelabelPage() {
  const [form, setForm] = useState<WhitelabelData>({ whitelabel_company_name: "", whitelabel_primary_color: "#6366f1", whitelabel_logo_url: "" });
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    domainAdminApi.getWhitelabel().then((r) => setForm(r as WhitelabelData)).catch(() => undefined).finally(() => setLoading(false));
  }, []);

  async function handleSave() {
    setSaving(true);
    try { await domainAdminApi.updateWhitelabel(form); toast("Whitelabel settings saved", "success"); }
    catch (e) { toast((e as Error).message, "error"); }
    finally { setSaving(false); }
  }

  return (
    <div className="flex flex-col lg:flex-row gap-6 max-w-5xl">
      <div className="flex-1 space-y-5">
        <h1 className="text-2xl font-bold text-gray-900 dark:text-white">Whitelabel</h1>
        {loading ? <div className="h-48 bg-white dark:bg-gray-900 rounded-xl animate-pulse" /> : (
          <div className="bg-white dark:bg-gray-900 rounded-xl border border-gray-100 dark:border-gray-800 p-6 space-y-4">
            {[
              { label: "Company name", key: "whitelabel_company_name", type: "text", placeholder: "Acme Corp" },
              { label: "Logo URL", key: "whitelabel_logo_url", type: "url", placeholder: "https://example.com/logo.png" },
            ].map(({ label, key, type, placeholder }) => (
              <div key={key}>
                <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">{label}</label>
                <input type={type} value={form[key as keyof WhitelabelData]} onChange={(e) => setForm({ ...form, [key]: e.target.value })} placeholder={placeholder}
                  className="w-full px-3 py-2 text-sm rounded-lg border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-800 text-gray-900 dark:text-gray-100 focus:outline-none focus:ring-2 focus:ring-indigo-400" />
              </div>
            ))}
            <div>
              <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">Primary color</label>
              <div className="flex items-center gap-3">
                <input type="color" value={form.whitelabel_primary_color} onChange={(e) => setForm({ ...form, whitelabel_primary_color: e.target.value })} className="w-10 h-10 rounded cursor-pointer border-0 p-0" />
                <span className="text-sm text-gray-600 dark:text-gray-400 font-mono">{form.whitelabel_primary_color}</span>
              </div>
            </div>
            <button onClick={handleSave} disabled={saving} className="px-5 py-2.5 rounded-lg bg-indigo-600 hover:bg-indigo-700 text-white text-sm font-medium disabled:opacity-60">
              {saving ? "Saving…" : "Save"}
            </button>
          </div>
        )}
      </div>

      {/* Live preview */}
      <div className="w-full lg:w-72">
        <p className="text-sm font-medium text-gray-700 dark:text-gray-300 mb-3">Preview</p>
        <div className="rounded-xl border border-gray-200 dark:border-gray-700 overflow-hidden shadow">
          <div className="p-4 text-white" style={{ background: form.whitelabel_primary_color }}>
            {form.whitelabel_logo_url && <img src={form.whitelabel_logo_url} alt="logo" className="h-8 mb-2 object-contain" />}
            <p className="font-bold">{form.whitelabel_company_name || "Your Company"}</p>
          </div>
          <div className="bg-white dark:bg-gray-900 p-4 text-sm text-gray-600 dark:text-gray-400">Login page & emails will use this branding.</div>
        </div>
      </div>
    </div>
  );
}
