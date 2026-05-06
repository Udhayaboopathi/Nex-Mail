"use client";

import { useEffect, useState } from "react";
import { Plus, Pencil, Trash2, Filter } from "lucide-react";
import { rulesApi } from "../../../lib/api";
import { RuleBuilderModal } from "../../../components/mail/RuleBuilderModal";
import { toast } from "../../../components/ui/Toast";
import { Badge } from "../../../components/ui/Badge";
import type { EmailRule } from "../../../types";

export default function RulesPage() {
  const [rules, setRules] = useState<EmailRule[]>([]);
  const [loading, setLoading] = useState(true);
  const [editTarget, setEditTarget] = useState<EmailRule | undefined>();
  const [showBuilder, setShowBuilder] = useState(false);

  async function load() {
    try { setRules(await rulesApi.list()); }
    catch { /* ignore */ }
    finally { setLoading(false); }
  }

  useEffect(() => { load(); }, []);

  async function handleDelete(id: string) {
    if (!confirm("Delete rule?")) return;
    try { await rulesApi.remove(id); setRules((p) => p.filter((r) => r.id !== id)); toast("Rule deleted", "success"); }
    catch (e) { toast((e as Error).message, "error"); }
  }

  return (
    <div className="max-w-2xl mx-auto p-6 space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold text-gray-900 dark:text-white">Rules</h1>
        <button onClick={() => { setEditTarget(undefined); setShowBuilder(true); }} className="flex items-center gap-2 px-4 py-2 rounded-lg bg-indigo-600 hover:bg-indigo-700 text-white text-sm font-medium">
          <Plus className="w-4 h-4" /> New Rule
        </button>
      </div>

      <div className="space-y-3">
        {loading ? [1,2].map((i) => <div key={i} className="h-16 bg-white dark:bg-gray-900 rounded-xl animate-pulse" />) :
          rules.length === 0 ? (
            <div className="text-center py-12 text-gray-400 dark:text-gray-600">
              <Filter className="w-12 h-12 mx-auto mb-3 opacity-30" />
              <p className="text-sm">No rules. Create your first rule to auto-organize email.</p>
            </div>
          ) : rules.sort((a, b) => a.priority - b.priority).map((r) => (
            <div key={r.id} className="p-4 bg-white dark:bg-gray-900 rounded-xl border border-gray-100 dark:border-gray-800">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <span className="font-medium text-gray-800 dark:text-gray-200 text-sm">{r.name}</span>
                  <Badge variant={r.is_active ? "success" : "default"}>{r.is_active ? "Active" : "Disabled"}</Badge>
                </div>
                <div className="flex items-center gap-1">
                  <button onClick={() => { setEditTarget(r); setShowBuilder(true); }} className="p-1.5 rounded hover:bg-gray-100 dark:hover:bg-gray-800"><Pencil className="w-4 h-4 text-gray-500" /></button>
                  <button onClick={() => handleDelete(r.id)} className="p-1.5 rounded hover:bg-gray-100 dark:hover:bg-gray-800"><Trash2 className="w-4 h-4 text-red-500" /></button>
                </div>
              </div>
              <p className="text-xs text-gray-500 dark:text-gray-400 mt-1">
                {r.conditions.length} condition(s) → {r.actions.length} action(s) · Match {r.match_type}
              </p>
            </div>
          ))}
      </div>

      {showBuilder && <RuleBuilderModal rule={editTarget} onClose={() => setShowBuilder(false)} onSaved={load} />}
    </div>
  );
}
