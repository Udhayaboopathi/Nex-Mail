"use client";

import { useEffect, useState } from "react";
import { Plus, Trash2, Zap } from "lucide-react";
import { webhooksApi } from "../../../lib/api";
import { toast } from "../../../components/ui/Toast";
import { Badge } from "../../../components/ui/Badge";
import type { Webhook } from "../../../types";

export default function WebhooksPage() {
  const [webhooks, setWebhooks] = useState<Webhook[]>([]);
  const [loading, setLoading] = useState(true);
  const [showNew, setShowNew] = useState(false);
  const [url, setUrl] = useState("");
  const [creating, setCreating] = useState(false);

  async function load() {
    try { setWebhooks(await webhooksApi.list()); }
    catch { /* ignore */ }
    finally { setLoading(false); }
  }

  useEffect(() => { load(); }, []);

  async function handleCreate() {
    if (!url.trim()) return;
    setCreating(true);
    try {
      const w = await webhooksApi.create({ url, events: ["receive", "send"] });
      setWebhooks((p) => [w, ...p]);
      setUrl(""); setShowNew(false);
      toast("Webhook created", "success");
    } catch (e) { toast((e as Error).message, "error"); }
    finally { setCreating(false); }
  }

  async function handleTest(id: string) {
    try { await webhooksApi.test(id); toast("Test event sent!", "success"); }
    catch (e) { toast((e as Error).message, "error"); }
  }

  async function handleDelete(id: string) {
    if (!confirm("Delete webhook?")) return;
    try { await webhooksApi.remove(id); setWebhooks((p) => p.filter((w) => w.id !== id)); toast("Deleted", "success"); }
    catch (e) { toast((e as Error).message, "error"); }
  }

  return (
    <div className="max-w-2xl mx-auto p-6 space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold text-gray-900 dark:text-white">Webhooks</h1>
        <button onClick={() => setShowNew(true)} className="flex items-center gap-2 px-4 py-2 rounded-lg bg-indigo-600 hover:bg-indigo-700 text-white text-sm font-medium">
          <Plus className="w-4 h-4" /> Add Webhook
        </button>
      </div>

      {showNew && (
        <div className="p-4 bg-white dark:bg-gray-900 rounded-xl border border-gray-100 dark:border-gray-800 space-y-3">
          <input value={url} onChange={(e) => setUrl(e.target.value)} type="url" placeholder="https://your-server.com/webhook"
            className="w-full px-3 py-2 text-sm rounded-lg border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-800 text-gray-900 dark:text-gray-100 focus:outline-none focus:ring-2 focus:ring-indigo-400" />
          <div className="flex gap-2">
            <button onClick={handleCreate} disabled={creating} className="px-4 py-2 text-sm rounded-lg bg-indigo-600 hover:bg-indigo-700 text-white font-medium disabled:opacity-60">{creating ? "Creating…" : "Create"}</button>
            <button onClick={() => setShowNew(false)} className="px-4 py-2 text-sm rounded-lg text-gray-700 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-800">Cancel</button>
          </div>
        </div>
      )}

      <div className="space-y-3">
        {loading ? [1,2].map((i) => <div key={i} className="h-16 bg-white dark:bg-gray-900 rounded-xl animate-pulse" />) :
          webhooks.length === 0 ? <div className="text-center py-12 text-gray-400 text-sm">No webhooks yet.</div> :
          webhooks.map((w) => (
            <div key={w.id} className="p-4 bg-white dark:bg-gray-900 rounded-xl border border-gray-100 dark:border-gray-800">
              <div className="flex items-center justify-between">
                <p className="text-sm font-mono text-gray-700 dark:text-gray-300 truncate max-w-xs">{w.url}</p>
                <div className="flex items-center gap-2 shrink-0">
                  {w.is_active ? <Badge variant="success">Active</Badge> : <Badge variant="danger">Inactive</Badge>}
                  <button onClick={() => handleTest(w.id)} title="Send test" className="p-1.5 rounded hover:bg-gray-100 dark:hover:bg-gray-800"><Zap className="w-4 h-4 text-yellow-500" /></button>
                  <button onClick={() => handleDelete(w.id)} className="p-1.5 rounded hover:bg-gray-100 dark:hover:bg-gray-800"><Trash2 className="w-4 h-4 text-red-500" /></button>
                </div>
              </div>
              <div className="flex flex-wrap gap-1 mt-2">{w.events.map((e) => <Badge key={e} className="text-[10px]">{e}</Badge>)}</div>
              {w.failure_count > 0 && <p className="text-xs text-red-500 mt-1">{w.failure_count} recent failures</p>}
            </div>
          ))}
      </div>
    </div>
  );
}
