"use client";

import { useEffect, useState } from "react";
import { Plus, Trash2, Copy } from "lucide-react";
import { apiKeysApi } from "../../../lib/api";
import { toast } from "../../../components/ui/Toast";
import { Badge } from "../../../components/ui/Badge";
import type { ApiKey } from "../../../types";

export default function ApiKeysPage() {
  const [keys, setKeys] = useState<ApiKey[]>([]);
  const [loading, setLoading] = useState(true);
  const [showNew, setShowNew] = useState(false);
  const [newKey, setNewKey] = useState("");
  const [name, setName] = useState("");
  const [creating, setCreating] = useState(false);

  async function load() {
    try { setKeys(await apiKeysApi.list()); }
    catch { /* ignore */ }
    finally { setLoading(false); }
  }

  useEffect(() => { load(); }, []);

  async function handleCreate() {
    if (!name.trim()) { toast("Name is required", "error"); return; }
    setCreating(true);
    try {
      const k = await apiKeysApi.create({ name, scopes: ["send"] });
      setNewKey(k.full_key ?? "");
      setKeys((p) => [k, ...p]);
      setName("");
    } catch (e) { toast((e as Error).message, "error"); }
    finally { setCreating(false); setShowNew(false); }
  }

  async function handleDelete(id: string) {
    if (!confirm("Delete API key?")) return;
    try { await apiKeysApi.remove(id); setKeys((p) => p.filter((k) => k.id !== id)); toast("Key deleted", "success"); }
    catch (e) { toast((e as Error).message, "error"); }
  }

  return (
    <div className="max-w-2xl mx-auto p-6 space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold text-gray-900 dark:text-white">API Keys</h1>
        <button onClick={() => setShowNew(true)} className="flex items-center gap-2 px-4 py-2 rounded-lg bg-indigo-600 hover:bg-indigo-700 text-white text-sm font-medium">
          <Plus className="w-4 h-4" /> New Key
        </button>
      </div>

      {/* New key revealed once */}
      {newKey && (
        <div className="p-4 rounded-xl bg-green-50 dark:bg-green-900/20 border border-green-200 dark:border-green-800">
          <p className="text-sm font-medium text-green-800 dark:text-green-300 mb-2">Copy your key — it won&apos;t be shown again!</p>
          <div className="flex items-center gap-2 bg-white dark:bg-gray-800 rounded-lg p-2 font-mono text-xs break-all">
            <span className="flex-1">{newKey}</span>
            <button onClick={() => { navigator.clipboard.writeText(newKey); toast("Copied!", "success"); }}>
              <Copy className="w-4 h-4 text-indigo-600 dark:text-indigo-400" />
            </button>
          </div>
          <button onClick={() => setNewKey("")} className="mt-2 text-xs text-green-700 dark:text-green-400 hover:underline">I&apos;ve copied it →</button>
        </div>
      )}

      {/* Create form */}
      {showNew && (
        <div className="p-4 bg-white dark:bg-gray-900 rounded-xl border border-gray-100 dark:border-gray-800 space-y-3">
          <input value={name} onChange={(e) => setName(e.target.value)} placeholder="Key name (e.g. My App)"
            className="w-full px-3 py-2 text-sm rounded-lg border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-800 text-gray-900 dark:text-gray-100 focus:outline-none focus:ring-2 focus:ring-indigo-400" />
          <div className="flex gap-2">
            <button onClick={handleCreate} disabled={creating} className="px-4 py-2 text-sm rounded-lg bg-indigo-600 hover:bg-indigo-700 text-white font-medium disabled:opacity-60">{creating ? "Creating…" : "Create"}</button>
            <button onClick={() => setShowNew(false)} className="px-4 py-2 text-sm rounded-lg text-gray-700 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-800">Cancel</button>
          </div>
        </div>
      )}

      {/* Keys list */}
      <div className="space-y-3">
        {loading ? [1,2].map((i) => <div key={i} className="h-16 bg-white dark:bg-gray-900 rounded-xl animate-pulse" />) :
          keys.length === 0 ? <div className="text-center py-12 text-gray-400 text-sm">No API keys yet.</div> :
          keys.map((k) => (
            <div key={k.id} className="flex items-center justify-between p-4 bg-white dark:bg-gray-900 rounded-xl border border-gray-100 dark:border-gray-800">
              <div>
                <p className="font-medium text-gray-800 dark:text-gray-200 text-sm">{k.name}</p>
                <p className="text-xs text-gray-400 font-mono mt-0.5">{k.key_prefix}••••••••</p>
                <div className="flex flex-wrap gap-1 mt-1">{k.scopes.map((s) => <Badge key={s} variant="purple" className="text-[10px]">{s}</Badge>)}</div>
              </div>
              <div className="flex items-center gap-2">
                {k.is_active ? <Badge variant="success">Active</Badge> : <Badge variant="danger">Inactive</Badge>}
                <button onClick={() => handleDelete(k.id)} className="p-1.5 rounded hover:bg-gray-100 dark:hover:bg-gray-800"><Trash2 className="w-4 h-4 text-red-500" /></button>
              </div>
            </div>
          ))}
      </div>
    </div>
  );
}
