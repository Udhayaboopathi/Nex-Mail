"use client";

import { useState } from "react";
import { Search } from "lucide-react";
import { domainAdminApi } from "../../../lib/api";
import { toast } from "../../../components/ui/Toast";

export default function EdiscoveryPage() {
  const [form, setForm] = useState({ from_address: "", subject: "", date_from: "", date_to: "" });
  const [searching, setSearching] = useState(false);
  const [exporting, setExporting] = useState(false);
  const [results, setResults] = useState<unknown[]>([]);

  async function handleSearch() {
    setSearching(true);
    try {
      const res = await domainAdminApi.ediscoverySearch(form) as { results: unknown[] };
      setResults(res.results ?? []);
    } catch (e) { toast((e as Error).message, "error"); }
    finally { setSearching(false); }
  }

  async function handleExport() {
    setExporting(true);
    try { await domainAdminApi.ediscoveryExport(form); toast("Export queued", "success"); }
    catch (e) { toast((e as Error).message, "error"); }
    finally { setExporting(false); }
  }

  return (
    <div className="space-y-6 max-w-3xl">
      <div>
        <h1 className="text-2xl font-bold text-gray-900 dark:text-white">eDiscovery</h1>
        <p className="text-sm text-gray-500 dark:text-gray-400 mt-0.5">Search and export emails for compliance.</p>
      </div>

      <div className="bg-white dark:bg-gray-900 rounded-xl border border-gray-100 dark:border-gray-800 p-6 space-y-4">
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {[
            { label: "From address", key: "from_address", type: "email", placeholder: "sender@example.com" },
            { label: "Subject contains", key: "subject", type: "text", placeholder: "keyword" },
            { label: "Date from", key: "date_from", type: "date", placeholder: "" },
            { label: "Date to", key: "date_to", type: "date", placeholder: "" },
          ].map(({ label, key, type, placeholder }) => (
            <div key={key}>
              <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">{label}</label>
              <input type={type} value={form[key as keyof typeof form]} onChange={(e) => setForm({ ...form, [key]: e.target.value })} placeholder={placeholder}
                className="w-full px-3 py-2 text-sm rounded-lg border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-800 text-gray-900 dark:text-gray-100 focus:outline-none focus:ring-2 focus:ring-indigo-400" />
            </div>
          ))}
        </div>
        <div className="flex gap-3">
          <button onClick={handleSearch} disabled={searching} className="flex items-center gap-2 px-4 py-2 rounded-lg bg-indigo-600 hover:bg-indigo-700 text-white text-sm font-medium disabled:opacity-60">
            <Search className="w-4 h-4" /> {searching ? "Searching…" : "Search"}
          </button>
          <button onClick={handleExport} disabled={exporting} className="px-4 py-2 rounded-lg border border-gray-300 dark:border-gray-600 text-gray-700 dark:text-gray-300 text-sm hover:bg-gray-50 dark:hover:bg-gray-800 disabled:opacity-60">
            {exporting ? "Exporting…" : "Export"}
          </button>
        </div>
      </div>

      {results.length > 0 && (
        <div className="bg-white dark:bg-gray-900 rounded-xl border border-gray-100 dark:border-gray-800 p-4">
          <p className="text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">{results.length} result(s)</p>
          <pre className="text-xs text-gray-500 dark:text-gray-400 overflow-auto max-h-64">{JSON.stringify(results, null, 2)}</pre>
        </div>
      )}
    </div>
  );
}
