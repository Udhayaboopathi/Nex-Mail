"use client";

import { useEffect, useState } from "react";
import { Plus, Trash2 } from "lucide-react";
import { templatesApi } from "../../../lib/api";
import { toast } from "../../../components/ui/Toast";
import type { EmailTemplate } from "../../../types";

export default function TemplatesPage() {
  const [templates, setTemplates] = useState<EmailTemplate[]>([]);
  const [loading, setLoading] = useState(true);
  const [editing, setEditing] = useState<EmailTemplate | null>(null);
  const [form, setForm] = useState({ name: "", subject: "", body_text: "" });
  const [saving, setSaving] = useState(false);

  async function load() {
    try { setTemplates(await templatesApi.list()); }
    catch { /* ignore */ }
    finally { setLoading(false); }
  }

  useEffect(() => { load(); }, []);

  function openEdit(t: EmailTemplate | null) {
    setEditing(t);
    setForm(t ? { name: t.name, subject: t.subject, body_text: t.body_text ?? "" } : { name: "", subject: "", body_text: "" });
  }

  async function handleSave() {
    if (!form.name.trim()) { toast("Name required", "error"); return; }
    setSaving(true);
    try {
      if (editing) {
        const updated = await templatesApi.update(editing.id, form);
        setTemplates((p) => p.map((t) => t.id === updated.id ? updated : t));
      } else {
        const created = await templatesApi.create(form);
        setTemplates((p) => [created, ...p]);
      }
      toast("Template saved", "success");
      setEditing(null);
    } catch (e) { toast((e as Error).message, "error"); }
    finally { setSaving(false); }
  }

  async function handleDelete(id: string) {
    if (!confirm("Delete template?")) return;
    try { await templatesApi.remove(id); setTemplates((p) => p.filter((t) => t.id !== id)); toast("Deleted", "success"); }
    catch (e) { toast((e as Error).message, "error"); }
  }

  return (
    <div className="flex h-full min-h-screen">
      {/* List */}
      <div className="w-64 border-r border-gray-200 dark:border-gray-800 bg-white dark:bg-gray-900 flex flex-col">
        <div className="flex items-center justify-between px-4 py-3 border-b border-gray-100 dark:border-gray-800">
          <span className="font-semibold text-sm text-gray-800 dark:text-white">Templates</span>
          <button onClick={() => openEdit(null)} className="p-1.5 rounded hover:bg-gray-100 dark:hover:bg-gray-800">
            <Plus className="w-4 h-4 text-gray-600 dark:text-gray-400" />
          </button>
        </div>
        <div className="flex-1 overflow-y-auto">
          {loading ? (
            <div className="p-3 space-y-2">
              {[1, 2].map((i) => <div key={i} className="h-10 bg-gray-100 dark:bg-gray-800 rounded animate-pulse" />)}
            </div>
          ) : templates.length === 0 ? (
            <p className="p-4 text-sm text-gray-400 text-center">No templates yet.</p>
          ) : (
            templates.map((t) => (
              <button key={t.id} onClick={() => openEdit(t)}
                className={`w-full text-left px-4 py-3 border-b border-gray-50 dark:border-gray-800 hover:bg-gray-50 dark:hover:bg-gray-800 ${editing?.id === t.id ? "bg-indigo-50 dark:bg-indigo-900/20" : ""}`}
              >
                <p className="text-sm font-medium text-gray-800 dark:text-gray-200 truncate">{t.name}</p>
                <p className="text-xs text-gray-400 truncate">{t.subject}</p>
              </button>
            ))
          )}
        </div>
      </div>

      {/* Editor */}
      <div className="flex-1 bg-white dark:bg-gray-900 flex flex-col">
        <div className="flex flex-col h-full p-5 space-y-4">
          <div className="flex items-center justify-between">
            <h2 className="font-semibold text-gray-800 dark:text-white">{editing ? "Edit Template" : "New Template"}</h2>
            {editing && (
              <button onClick={() => handleDelete(editing.id)} className="p-1.5 rounded hover:bg-gray-100 dark:hover:bg-gray-800">
                <Trash2 className="w-4 h-4 text-red-500" />
              </button>
            )}
          </div>
          {[
            { label: "Name", key: "name", ph: "Template name" },
            { label: "Subject", key: "subject", ph: "Email subject" },
          ].map(({ label, key, ph }) => (
            <div key={key}>
              <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">{label}</label>
              <input
                value={form[key as keyof typeof form]}
                onChange={(e) => setForm({ ...form, [key]: e.target.value })}
                placeholder={ph}
                className="w-full px-3 py-2 text-sm rounded-lg border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-800 text-gray-900 dark:text-gray-100 focus:outline-none focus:ring-2 focus:ring-indigo-400"
              />
            </div>
          ))}
          <div className="flex-1 flex flex-col">
            <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">Body</label>
            <textarea
              value={form.body_text}
              onChange={(e) => setForm({ ...form, body_text: e.target.value })}
              placeholder="Email body…"
              className="flex-1 min-h-48 px-3 py-2 text-sm rounded-lg border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-800 text-gray-900 dark:text-gray-100 focus:outline-none focus:ring-2 focus:ring-indigo-400 resize-none"
            />
          </div>
          <button
            onClick={handleSave}
            disabled={saving}
            className="self-start px-5 py-2.5 rounded-lg bg-indigo-600 hover:bg-indigo-700 text-white text-sm font-medium disabled:opacity-60"
          >
            {saving ? "Saving…" : "Save Template"}
          </button>
        </div>
      </div>
    </div>
  );
}
