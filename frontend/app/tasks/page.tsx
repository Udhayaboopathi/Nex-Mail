"use client";

import { useEffect, useState } from "react";
import { Plus, CheckSquare, Square, Trash2 } from "lucide-react";
import { tasksApi } from "../../lib/api";
import { toast } from "../../components/ui/Toast";
import { Badge } from "../../components/ui/Badge";
import type { Task } from "../../types";

export default function TasksPage() {
  const [tasks, setTasks] = useState<Task[]>([]);
  const [loading, setLoading] = useState(true);
  const [title, setTitle] = useState("");
  const [adding, setAdding] = useState(false);

  async function load() {
    try { setTasks(await tasksApi.list()); }
    catch { /* ignore */ }
    finally { setLoading(false); }
  }

  useEffect(() => { load(); }, []);

  async function handleAdd() {
    if (!title.trim()) return;
    setAdding(true);
    try {
      const t = await tasksApi.create({ title, is_completed: false, priority: "normal" });
      setTasks((p) => [t, ...p]);
      setTitle("");
    } catch (e) { toast((e as Error).message, "error"); }
    finally { setAdding(false); }
  }

  async function handleComplete(t: Task) {
    try {
      await tasksApi.complete(t.id);
      setTasks((p) => p.map((x) => x.id === t.id ? { ...x, is_completed: true } : x));
    } catch (e) { toast((e as Error).message, "error"); }
  }

  async function handleDelete(id: string) {
    if (!confirm("Delete task?")) return;
    try { await tasksApi.remove(id); setTasks((p) => p.filter((t) => t.id !== id)); }
    catch (e) { toast((e as Error).message, "error"); }
  }

  const incomplete = tasks.filter((t) => !t.is_completed);
  const complete = tasks.filter((t) => t.is_completed);

  return (
    <div className="max-w-2xl mx-auto p-6 space-y-6">
      <h1 className="text-2xl font-bold text-gray-900 dark:text-white">Tasks</h1>

      {/* Quick add */}
      <div className="flex gap-2">
        <input value={title} onChange={(e) => setTitle(e.target.value)} onKeyDown={(e) => e.key === "Enter" && handleAdd()} placeholder="Add a task…"
          className="flex-1 px-4 py-2.5 text-sm rounded-lg border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-800 text-gray-900 dark:text-gray-100 focus:outline-none focus:ring-2 focus:ring-indigo-400" />
        <button onClick={handleAdd} disabled={adding || !title.trim()} className="flex items-center gap-1.5 px-4 py-2.5 rounded-lg bg-indigo-600 hover:bg-indigo-700 text-white text-sm disabled:opacity-60">
          <Plus className="w-4 h-4" /> Add
        </button>
      </div>

      {loading ? (
        <div className="space-y-2">{[1,2,3].map((i) => <div key={i} className="h-12 bg-white dark:bg-gray-900 rounded-xl animate-pulse" />)}</div>
      ) : (
        <>
          {/* Incomplete */}
          {incomplete.length > 0 && (
            <div className="space-y-2">
              {incomplete.map((t) => (
                <div key={t.id} className="flex items-center gap-3 p-3 bg-white dark:bg-gray-900 rounded-xl border border-gray-100 dark:border-gray-800 group">
                  <button onClick={() => handleComplete(t)} className="shrink-0">
                    <Square className="w-5 h-5 text-gray-400 hover:text-indigo-600 dark:hover:text-indigo-400" />
                  </button>
                  <span className="flex-1 text-sm text-gray-800 dark:text-gray-200">{t.title}</span>
                  <Badge variant={t.priority === "high" ? "danger" : t.priority === "low" ? "default" : "info"} className="hidden group-hover:inline-flex">{t.priority}</Badge>
                  {t.due_at && <span className="text-xs text-gray-400">{new Date(t.due_at).toLocaleDateString()}</span>}
                  <button onClick={() => handleDelete(t.id)} className="opacity-0 group-hover:opacity-100 p-1 rounded hover:bg-gray-100 dark:hover:bg-gray-800">
                    <Trash2 className="w-4 h-4 text-red-500" />
                  </button>
                </div>
              ))}
            </div>
          )}

          {/* Complete */}
          {complete.length > 0 && (
            <div>
              <p className="text-xs font-medium text-gray-400 uppercase tracking-wider mb-2">Completed ({complete.length})</p>
              <div className="space-y-1">
                {complete.map((t) => (
                  <div key={t.id} className="flex items-center gap-3 p-2.5 bg-gray-50 dark:bg-gray-800/50 rounded-lg">
                    <CheckSquare className="w-4 h-4 text-green-500 shrink-0" />
                    <span className="flex-1 text-sm text-gray-400 line-through">{t.title}</span>
                    <button onClick={() => handleDelete(t.id)} className="p-1 rounded hover:bg-gray-100 dark:hover:bg-gray-700">
                      <Trash2 className="w-3.5 h-3.5 text-gray-400" />
                    </button>
                  </div>
                ))}
              </div>
            </div>
          )}

          {tasks.length === 0 && (
            <div className="text-center py-12 text-gray-400 dark:text-gray-600">
              <CheckSquare className="w-12 h-12 mx-auto mb-3 opacity-30" />
              <p className="text-sm">No tasks yet. Add one above!</p>
            </div>
          )}
        </>
      )}
    </div>
  );
}
