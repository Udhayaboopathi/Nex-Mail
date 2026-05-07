"use client";

import { useEffect, useState } from "react";
import { domainAdminApi } from "../../../lib/api";
import { toast } from "../../../components/ui/Toast";

interface WhitelabelData {
  company_name: string;
  primary_color: string;
  logo_url: string;
  bimi_vmc_url: string;
}

export default function WhitelabelPage() {
  const [form, setForm] = useState<WhitelabelData>({ company_name: "", primary_color: "#6366f1", logo_url: "", bimi_vmc_url: "" });
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [uploadingLogo, setUploadingLogo] = useState(false);
  const [uploadingVmc, setUploadingVmc] = useState(false);
  const [readiness, setReadiness] = useState<{ all_ready: boolean; dmarc_ok: boolean; dkim_ok: boolean; spf_ok: boolean; bimi_ok: boolean; vmc_set: boolean } | null>(null);

  useEffect(() => {
    Promise.all([domainAdminApi.getWhitelabel(), domainAdminApi.getBrandingReadiness()])
      .then(([r, ready]) => {
        setForm({
          company_name: (r as { company_name?: string }).company_name || "",
          primary_color: (r as { primary_color?: string }).primary_color || "#6366f1",
          logo_url: (r as { logo_url?: string }).logo_url || "",
          bimi_vmc_url: (r as { bimi_vmc_url?: string }).bimi_vmc_url || "",
        });
        setReadiness(ready);
      })
      .catch(() => undefined)
      .finally(() => setLoading(false));
  }, []);

  async function handleSave() {
    setSaving(true);
    try { await domainAdminApi.updateWhitelabel(form); toast("Whitelabel settings saved", "success"); }
    catch (e) { toast((e as Error).message, "error"); }
    finally { setSaving(false); }
  }

  async function handleLogoUpload(file: File | null) {
    if (!file) return;
    setUploadingLogo(true);
    try {
      const r = await domainAdminApi.uploadLogo(file);
      setForm((p) => ({ ...p, logo_url: r.logo_url || p.logo_url }));
      toast("Logo uploaded", "success");
    } catch (e) {
      toast((e as Error).message, "error");
    } finally {
      setUploadingLogo(false);
    }
  }

  async function handleVmcUpload(file: File | null) {
    if (!file) return;
    setUploadingVmc(true);
    try {
      const r = await domainAdminApi.uploadVmc(file);
      setForm((p) => ({ ...p, bimi_vmc_url: r.bimi_vmc_url || p.bimi_vmc_url }));
      toast("VMC uploaded", "success");
    } catch (e) {
      toast((e as Error).message, "error");
    } finally {
      setUploadingVmc(false);
    }
  }

  return (
    <div className="flex flex-col lg:flex-row gap-6 max-w-5xl">
      <div className="flex-1 space-y-5">
        <h1 className="text-2xl font-bold text-gray-900 dark:text-white">Whitelabel</h1>
        {loading ? <div className="h-48 bg-white dark:bg-gray-900 rounded-xl animate-pulse" /> : (
          <div className="bg-white dark:bg-gray-900 rounded-xl border border-gray-100 dark:border-gray-800 p-6 space-y-4">
            {[
              { label: "Company name", key: "company_name", type: "text", placeholder: "Acme Corp" },
              { label: "Logo URL", key: "logo_url", type: "url", placeholder: "https://example.com/logo.svg" },
              { label: "VMC URL (optional)", key: "bimi_vmc_url", type: "url", placeholder: "https://example.com/vmc.pem" },
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
                <input type="color" value={form.primary_color} onChange={(e) => setForm({ ...form, primary_color: e.target.value })} className="w-10 h-10 rounded cursor-pointer border-0 p-0" />
                <span className="text-sm text-gray-600 dark:text-gray-400 font-mono">{form.primary_color}</span>
              </div>
            </div>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
              <label className="text-sm border rounded-lg px-3 py-2 cursor-pointer hover:bg-gray-50 dark:hover:bg-gray-800">
                {uploadingLogo ? "Uploading logo..." : "Upload BIMI logo (SVG)"}
                <input type="file" accept=".svg,image/svg+xml" className="hidden" onChange={(e) => handleLogoUpload(e.target.files?.[0] || null)} />
              </label>
              <label className="text-sm border rounded-lg px-3 py-2 cursor-pointer hover:bg-gray-50 dark:hover:bg-gray-800">
                {uploadingVmc ? "Uploading VMC..." : "Upload VMC (PEM/CRT)"}
                <input type="file" accept=".pem,.crt,application/x-x509-ca-cert" className="hidden" onChange={(e) => handleVmcUpload(e.target.files?.[0] || null)} />
              </label>
            </div>
            {readiness && (
              <div className="text-xs text-gray-600 dark:text-gray-400 space-y-1">
                <p>BIMI readiness: {readiness.all_ready ? "Ready" : "Not ready"}</p>
                <p>DMARC: {readiness.dmarc_ok ? "OK" : "Missing"} | DKIM: {readiness.dkim_ok ? "OK" : "Missing"} | SPF: {readiness.spf_ok ? "OK" : "Missing"} | BIMI TXT: {readiness.bimi_ok ? "OK" : "Missing"} | VMC: {readiness.vmc_set ? "Set" : "Not set"}</p>
              </div>
            )}
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
          <div className="p-4 text-white" style={{ background: form.primary_color }}>
            {form.logo_url && <img src={form.logo_url} alt="logo" className="h-8 mb-2 object-contain" />}
            <p className="font-bold">{form.company_name || "Your Company"}</p>
          </div>
          <div className="bg-white dark:bg-gray-900 p-4 text-sm text-gray-600 dark:text-gray-400">Login page & emails will use this branding.</div>
        </div>
      </div>
    </div>
  );
}
