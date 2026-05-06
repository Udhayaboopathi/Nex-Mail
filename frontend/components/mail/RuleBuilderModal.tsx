"use client";

import { useState } from "react";
import { Plus, Trash2, X } from "lucide-react";
import { rulesApi } from "../../lib/api";
import { toast } from "../ui/Toast";
import type { RuleCondition, RuleAction, EmailRule, ConditionField, ConditionOp, ActionType } from "../../types";

interface RuleBuilderModalProps {
  rule?: EmailRule;
  onClose: () => void;
  onSaved: () => void;
}

const CONDITION_FIELDS: ConditionField[] = ["from", "to", "subject", "body", "has_attachment"];
const CONDITION_OPS: ConditionOp[] = ["contains", "not_contains", "equals", "starts_with"];
const ACTIONS: ActionType[] = ["move_to", "label", "mark_read", "star", "mark_spam", "forward_to", "auto_reply", "delete"];

export function RuleBuilderModal({ rule, onClose, onSaved }: RuleBuilderModalProps) {
  const [name, setName] = useState(rule?.name ?? "");
  const [matchType, setMatchType] = useState<"any" | "all">(rule?.match_type ?? "any");
  const [conditions, setConditions] = useState<RuleCondition[]>(
    rule?.conditions ?? [{ field: "from", op: "contains", value: "" }]
  );
  const [actions, setActions] = useState<RuleAction[]>(
    rule?.actions ?? [{ action: "move_to", value: "inbox" }]
  );
  const [saving, setSaving] = useState(false);

  function addCondition() {
    setConditions((prev) => [...prev, { field: "from", op: "contains", value: "" }]);
  }

  function removeCondition(i: number) {
    setConditions((prev) => prev.filter((_, idx) => idx !== i));
  }

  function updateCondition<K extends keyof RuleCondition>(i: number, key: K, val: RuleCondition[K]) {
    setConditions((prev) => prev.map((c, idx) => idx === i ? { ...c, [key]: val } : c));
  }

  function addAction() {
    setActions((prev) => [...prev, { action: "mark_read" }]);
  }

  function removeAction(i: number) {
    setActions((prev) => prev.filter((_, idx) => idx !== i));
  }

  function updateAction<K extends keyof RuleAction>(i: number, key: K, val: RuleAction[K]) {
    setActions((prev) => prev.map((a, idx) => idx === i ? { ...a, [key]: val } : a));
  }

  async function handleSave() {
    if (!name.trim()) { toast("Rule name is required", "error"); return; }
    if (conditions.length === 0) { toast("Add at least one condition", "error"); return; }
    if (actions.length === 0) { toast("Add at least one action", "error"); return; }
    setSaving(true);
    try {
      const payload = { name, is_active: true, priority: 0, match_type: matchType, conditions, actions };
      if (rule) {
        await rulesApi.update(rule.id, payload);
      } else {
        await rulesApi.create(payload);
      }
      toast(`Rule ${rule ? "updated" : "created"}!`, "success");
      onSaved();
      onClose();
    } catch (err) {
      toast((err as Error).message, "error");
    } finally {
      setSaving(false);
    }
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/50">
      <div className="bg-white dark:bg-gray-900 rounded-xl shadow-2xl w-full max-w-2xl max-h-[90vh] flex flex-col">
        {/* Header */}
        <div className="flex items-center justify-between px-6 py-4 border-b border-gray-100 dark:border-gray-800">
          <h2 className="text-lg font-semibold text-gray-900 dark:text-white">
            {rule ? "Edit Rule" : "New Rule"}
          </h2>
          <button onClick={onClose} className="p-1.5 rounded hover:bg-gray-100 dark:hover:bg-gray-800">
            <X className="w-5 h-5 text-gray-500" />
          </button>
        </div>

        <div className="flex-1 overflow-y-auto px-6 py-4 space-y-6">
          {/* Name */}
          <div>
            <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">Rule name</label>
            <input
              value={name}
              onChange={(e) => setName(e.target.value)}
              className="w-full px-3 py-2 text-sm rounded-lg border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-800 text-gray-900 dark:text-gray-100 focus:outline-none focus:ring-2 focus:ring-indigo-400"
              placeholder="e.g. Move newsletters to archive"
            />
          </div>

          {/* Match type */}
          <div>
            <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">Match</label>
            <div className="flex gap-3">
              {(["any", "all"] as const).map((t) => (
                <label key={t} className="flex items-center gap-2 cursor-pointer">
                  <input type="radio" checked={matchType === t} onChange={() => setMatchType(t)} className="accent-indigo-600" />
                  <span className="text-sm text-gray-700 dark:text-gray-300 capitalize">{t} condition</span>
                </label>
              ))}
            </div>
          </div>

          {/* Conditions */}
          <div>
            <div className="flex items-center justify-between mb-2">
              <label className="text-sm font-medium text-gray-700 dark:text-gray-300">Conditions</label>
              <button onClick={addCondition} className="flex items-center gap-1 text-xs text-indigo-600 dark:text-indigo-400 hover:underline">
                <Plus className="w-3 h-3" /> Add
              </button>
            </div>
            <div className="space-y-2">
              {conditions.map((cond, i) => (
                <div key={i} className="flex items-center gap-2">
                  <select
                    value={cond.field}
                    onChange={(e) => updateCondition(i, "field", e.target.value as ConditionField)}
                    className="px-2 py-1.5 text-sm rounded-lg border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-800 text-gray-900 dark:text-gray-100 focus:outline-none"
                  >
                    {CONDITION_FIELDS.map((f) => <option key={f} value={f}>{f}</option>)}
                  </select>
                  <select
                    value={cond.op}
                    onChange={(e) => updateCondition(i, "op", e.target.value as ConditionOp)}
                    className="px-2 py-1.5 text-sm rounded-lg border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-800 text-gray-900 dark:text-gray-100 focus:outline-none"
                  >
                    {CONDITION_OPS.map((o) => <option key={o} value={o}>{o.replace(/_/g, " ")}</option>)}
                  </select>
                  {cond.field !== "has_attachment" && (
                    <input
                      value={cond.value}
                      onChange={(e) => updateCondition(i, "value", e.target.value)}
                      placeholder="Value"
                      className="flex-1 px-2 py-1.5 text-sm rounded-lg border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-800 text-gray-900 dark:text-gray-100 focus:outline-none"
                    />
                  )}
                  <button onClick={() => removeCondition(i)} disabled={conditions.length === 1} className="p-1.5 rounded hover:bg-gray-100 dark:hover:bg-gray-800 disabled:opacity-30">
                    <Trash2 className="w-4 h-4 text-red-500" />
                  </button>
                </div>
              ))}
            </div>
          </div>

          {/* Actions */}
          <div>
            <div className="flex items-center justify-between mb-2">
              <label className="text-sm font-medium text-gray-700 dark:text-gray-300">Actions</label>
              <button onClick={addAction} className="flex items-center gap-1 text-xs text-indigo-600 dark:text-indigo-400 hover:underline">
                <Plus className="w-3 h-3" /> Add
              </button>
            </div>
            <div className="space-y-2">
              {actions.map((act, i) => (
                <div key={i} className="flex items-center gap-2">
                  <select
                    value={act.action}
                    onChange={(e) => updateAction(i, "action", e.target.value as ActionType)}
                    className="px-2 py-1.5 text-sm rounded-lg border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-800 text-gray-900 dark:text-gray-100 focus:outline-none"
                  >
                    {ACTIONS.map((a) => <option key={a} value={a}>{a.replace(/_/g, " ")}</option>)}
                  </select>
                  {["move_to", "label", "forward_to", "auto_reply"].includes(act.action) && (
                    <input
                      value={act.value ?? ""}
                      onChange={(e) => updateAction(i, "value", e.target.value)}
                      placeholder={act.action === "move_to" ? "folder name" : act.action === "forward_to" ? "email address" : "value"}
                      className="flex-1 px-2 py-1.5 text-sm rounded-lg border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-800 text-gray-900 dark:text-gray-100 focus:outline-none"
                    />
                  )}
                  <button onClick={() => removeAction(i)} disabled={actions.length === 1} className="p-1.5 rounded hover:bg-gray-100 dark:hover:bg-gray-800 disabled:opacity-30">
                    <Trash2 className="w-4 h-4 text-red-500" />
                  </button>
                </div>
              ))}
            </div>
          </div>
        </div>

        {/* Footer */}
        <div className="flex items-center justify-end gap-3 px-6 py-4 border-t border-gray-100 dark:border-gray-800">
          <button onClick={onClose} className="px-4 py-2 text-sm rounded-lg text-gray-700 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-800">
            Cancel
          </button>
          <button
            onClick={handleSave}
            disabled={saving}
            className="px-4 py-2 text-sm rounded-lg bg-indigo-600 hover:bg-indigo-700 text-white font-medium transition-colors disabled:opacity-60"
          >
            {saving ? "Saving…" : "Save Rule"}
          </button>
        </div>
      </div>
    </div>
  );
}
