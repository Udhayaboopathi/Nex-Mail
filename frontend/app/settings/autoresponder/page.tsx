"use client";

import { useEffect, useState } from "react";
import { Mail, Save, Trash2 } from "lucide-react";
import { mailApi } from "../../../lib/api";
import { toast } from "../../../components/ui/Toast";
import type { Autoresponder } from "../../../types";

export default function AutoresponderPage() {
  const [data, setData] = useState<Partial<Autoresponder>>({ subject: "Out of Office", body: "", is_enabled: false });
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    mailApi.getAutoresponder()
      .then((r) => setData(r))
      .catch(() => { /* no autoresponder set yet */ })
      .finally(() => setLoading(false));
  }, []);

  async function handleSave() {
    setSaving(true);
    try {
      await mailApi.setAutoresponder(data);
      toast("Autoresponder saved", "success");
    } catch (e) {
      toast((e as Error).message, "error");
    } finally {
      setSaving(false);
    }
  }

  async function handleDelete() {
    if (!confirm("Delete autoresponder?")) return;
    try {
      await mailApi.deleteAutoresponder();
      setData({ subject: "Out of Office", body: "", is_enabled: false });
      toast("Autoresponder removed", "success");
    } catch (e) {
      toast((e as Error).message, "error");
    }
  }

  if (loading) {
    return (
      <div className="max-w-xl mx-auto p-6 space-y-4">
        {[1, 2, 3].map((i) => <div key={i} className="h-12 bg-gray-100 dark:bg-gray-800 rounded-lg animate-pulse" />)}
      </div>
    );
  }

  return (
    <div className="max-w-xl mx-auto p-6 space-y-6">
      <div className="flex items-center gap-3">
        <Mail className="w-6 h-6 text-indigo-600 dark:text-indigo-400" />
        <h1 className="text-2xl font-bold text-gray-900 dark:text-white">Autoresponder</h1>
      </div>

      <div className="bg-white dark:bg-gray-900 rounded-xl border border-gray-100 dark:border-gray-800 p-6 space-y-5">
        {/* Enable toggle */}
        <div className="flex items-center justify-between">
          <div>
            <p className="font-medium text-gray-800 dark:text-gray-200">Enable autoresponder</p>
            <p className="text-sm text-gray-500 dark:text-gray-400">Automatically reply to incoming emails</p>
          </div>
          <button
            onClick={() => setData((p) => ({ ...p, is_enabled: !p.is_enabled }))}
            className={`relative inline-flex h-6 w-11 items-center rounded-full transition-colors ${data.is_enabled ? "bg-indigo-600" : "bg-gray-200 dark:bg-gray-700"}`}
          >
            <span className={`inline-block h-4 w-4 transform rounded-full bg-white transition-transform ${data.is_enabled ? "translate-x-6" : "translate-x-1"}`} />
          </button>
        </div>

        {/* Subject */}
        <div>
          <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">Subject</label>
          <input
            type="text"
            value={data.subject ?? "Out of Office"}
            onChange={(e) => setData((p) => ({ ...p, subject: e.target.value }))}
            className="w-full px-3 py-2 rounded-lg border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-800 text-gray-900 dark:text-gray-100 focus:outline-none focus:border-indigo-400 text-sm"
          />
        </div>

        {/* Body */}
        <div>
          <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">Message</label>
          <textarea
            rows={6}
            value={data.body ?? ""}
            onChange={(e) => setData((p) => ({ ...p, body: e.target.value }))}
            placeholder="I am currently out of office and will respond when I return."
            className="w-full px-3 py-2 rounded-lg border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-800 text-gray-900 dark:text-gray-100 focus:outline-none focus:border-indigo-400 text-sm resize-none"
          />
        </div>

        {/* Date range */}
        <div className="grid grid-cols-2 gap-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">Start date (optional)</label>
            <input
              type="date"
              value={data.start_date ?? ""}
              onChange={(e) => setData((p) => ({ ...p, start_date: e.target.value }))}
              className="w-full px-3 py-2 rounded-lg border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-800 text-gray-900 dark:text-gray-100 focus:outline-none focus:border-indigo-400 text-sm"
            />
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">End date (optional)</label>
            <input
              type="date"
              value={data.end_date ?? ""}
              onChange={(e) => setData((p) => ({ ...p, end_date: e.target.value }))}
              className="w-full px-3 py-2 rounded-lg border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-800 text-gray-900 dark:text-gray-100 focus:outline-none focus:border-indigo-400 text-sm"
            />
          </div>
        </div>

        {/* Reply once toggle */}
        <div className="flex items-center gap-3">
          <input
            type="checkbox"
            id="reply-once"
            checked={data.reply_once_per_sender ?? true}
            onChange={(e) => setData((p) => ({ ...p, reply_once_per_sender: e.target.checked }))}
            className="w-4 h-4 rounded text-indigo-600"
          />
          <label htmlFor="reply-once" className="text-sm text-gray-700 dark:text-gray-300">Reply once per sender (recommended)</label>
        </div>

        <div className="flex items-center justify-between pt-2">
          <button
            onClick={handleDelete}
            className="flex items-center gap-2 px-3 py-2 rounded-lg text-red-600 dark:text-red-400 hover:bg-red-50 dark:hover:bg-red-900/20 text-sm"
          >
            <Trash2 className="w-4 h-4" /> Remove
          </button>
          <button
            onClick={handleSave}
            disabled={saving}
            className="flex items-center gap-2 px-4 py-2 rounded-lg bg-indigo-600 hover:bg-indigo-700 text-white text-sm font-medium disabled:opacity-60"
          >
            <Save className="w-4 h-4" /> {saving ? "Saving…" : "Save"}
          </button>
        </div>
      </div>
    </div>
  );
}
