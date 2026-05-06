"use client";

import { useEffect, useState } from "react";
import { Plus, Trash2 } from "lucide-react";
import { labelsApi } from "../../../lib/api";
import { toast } from "../../../components/ui/Toast";
import type { Label } from "../../../types";

export default function LabelsPage() {
  const [labels, setLabels] = useState<Label[]>([]);
  const [loading, setLoading] = useState(true);
  const [name, setName] = useState("");
  const [color, setColor] = useState("#6366f1");
  const [adding, setAdding] = useState(false);

  async function load() {
    try { setLabels(await labelsApi.list()); }
    catch { /* ignore */ }
    finally { setLoading(false); }
  }

  useEffect(() => { load(); }, []);

  async function handleAdd() {
    if (!name.trim()) return;
    setAdding(true);
    try {
      const l = await labelsApi.create(name, color);
      setLabels((p) => [...p, l]);
      setName(""); setColor("#6366f1");
      toast("Label created", "success");
    } catch (e) { toast((e as Error).message, "error"); }
    finally { setAdding(false); }
  }

  async function handleDelete(id: string) {
    if (!confirm("Delete label?")) return;
    try { await labelsApi.remove(id); setLabels((p) => p.filter((l) => l.id !== id)); toast("Deleted", "success"); }
    catch (e) { toast((e as Error).message, "error"); }
  }

  return (
    <div className="max-w-xl mx-auto p-6 space-y-6">
      <h1 className="text-2xl font-bold text-gray-900 dark:text-white">Labels</h1>

      {/* Add form */}
      <div className="flex items-center gap-3 p-4 bg-white dark:bg-gray-900 rounded-xl border border-gray-100 dark:border-gray-800">
        <input type="color" value={color} onChange={(e) => setColor(e.target.value)} className="w-8 h-8 rounded cursor-pointer border-0 p-0 shrink-0" />
        <input value={name} onChange={(e) => setName(e.target.value)} onKeyDown={(e) => e.key === "Enter" && handleAdd()} placeholder="Label name"
          className="flex-1 px-3 py-2 text-sm rounded-lg border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-800 text-gray-900 dark:text-gray-100 focus:outline-none focus:ring-2 focus:ring-indigo-400" />
        <button onClick={handleAdd} disabled={adding || !name.trim()} className="flex items-center gap-1.5 px-3 py-2 rounded-lg bg-indigo-600 hover:bg-indigo-700 text-white text-sm disabled:opacity-60">
          <Plus className="w-4 h-4" /> Add
        </button>
      </div>

      {/* Labels list */}
      <div className="space-y-2">
        {loading ? [1,2,3].map((i) => <div key={i} className="h-12 bg-white dark:bg-gray-900 rounded-xl animate-pulse" />) :
          labels.length === 0 ? <p className="text-center py-8 text-gray-400 text-sm">No labels yet.</p> :
          labels.map((l) => (
            <div key={l.id} className="flex items-center gap-3 p-3 bg-white dark:bg-gray-900 rounded-xl border border-gray-100 dark:border-gray-800 group">
              <span className="w-4 h-4 rounded-full shrink-0" style={{ background: l.color }} />
              <span className="flex-1 text-sm text-gray-800 dark:text-gray-200">{l.name}</span>
              <button onClick={() => handleDelete(l.id)} className="opacity-0 group-hover:opacity-100 p-1 rounded hover:bg-gray-100 dark:hover:bg-gray-800">
                <Trash2 className="w-4 h-4 text-red-500" />
              </button>
            </div>
          ))}
      </div>
    </div>
  );
}
