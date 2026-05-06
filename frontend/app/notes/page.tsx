"use client";

import { useEffect, useState } from "react";
import { Plus, StickyNote, Trash2 } from "lucide-react";
import { notesApi } from "../../lib/api";
import { toast } from "../../components/ui/Toast";
import { formatDate } from "../../lib/utils";
import type { Note } from "../../types";

export default function NotesPage() {
  const [notes, setNotes] = useState<Note[]>([]);
  const [loading, setLoading] = useState(true);
  const [selected, setSelected] = useState<Note | null>(null);
  const [editBody, setEditBody] = useState("");
  const [editTitle, setEditTitle] = useState("");
  const [saving, setSaving] = useState(false);

  async function load() {
    try { const n = await notesApi.list(); setNotes(n); if (n.length > 0 && !selected) { setSelected(n[0]); setEditBody(n[0].body); setEditTitle(n[0].title ?? ""); } }
    catch { /* ignore */ }
    finally { setLoading(false); }
  }

  useEffect(() => { load(); }, []);

  // Auto-save debounce
  useEffect(() => {
    if (!selected) return;
    const t = setTimeout(async () => {
      if (editBody === selected.body && editTitle === (selected.title ?? "")) return;
      setSaving(true);
      try {
        const updated = await notesApi.update(selected.id, { body: editBody, title: editTitle });
        setNotes((p) => p.map((n) => n.id === updated.id ? updated : n));
        setSelected(updated);
      } catch { /* ignore */ }
      finally { setSaving(false); }
    }, 800);
    return () => clearTimeout(t);
  }, [editBody, editTitle]);

  async function handleNew() {
    try {
      const n = await notesApi.create({ body: "" });
      setNotes((p) => [n, ...p]);
      setSelected(n);
      setEditBody("");
      setEditTitle("");
    } catch (e) { toast((e as Error).message, "error"); }
  }

  async function handleDelete(id: string) {
    if (!confirm("Delete note?")) return;
    try {
      await notesApi.remove(id);
      const remaining = notes.filter((n) => n.id !== id);
      setNotes(remaining);
      setSelected(remaining[0] ?? null);
      setEditBody(remaining[0]?.body ?? "");
      setEditTitle(remaining[0]?.title ?? "");
    } catch (e) { toast((e as Error).message, "error"); }
  }

  function selectNote(n: Note) { setSelected(n); setEditBody(n.body); setEditTitle(n.title ?? ""); }

  return (
    <div className="flex h-full min-h-screen">
      {/* List */}
      <div className="w-64 border-r border-gray-200 dark:border-gray-800 bg-white dark:bg-gray-900 flex flex-col">
        <div className="flex items-center justify-between px-4 py-3 border-b border-gray-100 dark:border-gray-800">
          <span className="font-semibold text-sm text-gray-800 dark:text-white">Notes</span>
          <button onClick={handleNew} className="p-1.5 rounded hover:bg-gray-100 dark:hover:bg-gray-800"><Plus className="w-4 h-4 text-gray-600 dark:text-gray-400" /></button>
        </div>
        <div className="flex-1 overflow-y-auto">
          {loading ? (
            <div className="p-3 space-y-2">{[1,2,3].map((i) => <div key={i} className="h-10 bg-gray-100 dark:bg-gray-800 rounded animate-pulse" />)}</div>
          ) : notes.length === 0 ? (
            <div className="p-4 text-center text-gray-400 text-sm">No notes yet.</div>
          ) : notes.map((n) => (
            <button key={n.id} onClick={() => selectNote(n)} className={`w-full text-left px-4 py-3 border-b border-gray-50 dark:border-gray-800 hover:bg-gray-50 dark:hover:bg-gray-800 ${selected?.id === n.id ? "bg-indigo-50 dark:bg-indigo-900/20" : ""}`}>
              <p className="text-sm font-medium text-gray-800 dark:text-gray-200 truncate">{n.title || n.body.slice(0, 40) || "Untitled"}</p>
              <p className="text-xs text-gray-400 mt-0.5">{formatDate(n.updated_at)}</p>
            </button>
          ))}
        </div>
      </div>

      {/* Editor */}
      <div className="flex-1 flex flex-col bg-white dark:bg-gray-900">
        {selected ? (
          <>
            <div className="flex items-center justify-between px-5 py-3 border-b border-gray-100 dark:border-gray-800">
              <input value={editTitle} onChange={(e) => setEditTitle(e.target.value)} placeholder="Note title…"
                className="flex-1 text-lg font-semibold bg-transparent text-gray-900 dark:text-white focus:outline-none placeholder-gray-300 dark:placeholder-gray-600" />
              <div className="flex items-center gap-2">
                {saving && <span className="text-xs text-gray-400">Saving…</span>}
                <button onClick={() => handleDelete(selected.id)} className="p-1.5 rounded hover:bg-gray-100 dark:hover:bg-gray-800"><Trash2 className="w-4 h-4 text-red-500" /></button>
              </div>
            </div>
            <textarea
              value={editBody}
              onChange={(e) => setEditBody(e.target.value)}
              placeholder="Start writing…"
              className="flex-1 px-5 py-4 resize-none bg-transparent text-sm text-gray-700 dark:text-gray-300 focus:outline-none placeholder-gray-300 dark:placeholder-gray-600"
            />
          </>
        ) : (
          <div className="flex-1 flex flex-col items-center justify-center text-gray-400 dark:text-gray-600">
            <StickyNote className="w-16 h-16 mb-4 opacity-20" />
            <p className="text-sm">Select a note or create one.</p>
            <button onClick={handleNew} className="mt-4 flex items-center gap-2 px-4 py-2 rounded-lg bg-indigo-600 hover:bg-indigo-700 text-white text-sm">
              <Plus className="w-4 h-4" /> New Note
            </button>
          </div>
        )}
      </div>
    </div>
  );
}
