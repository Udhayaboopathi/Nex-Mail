"use client";

import { useEffect, useState, useCallback } from "react";
import { EmailList } from "../../../components/mail/EmailList";
import { PriorityInbox } from "../../../components/mail/PriorityInbox";
import { SearchBar } from "../../../components/mail/SearchBar";
import { mailApi } from "../../../lib/api";
import type { EmailHeader } from "../../../types";

export default function InboxPage() {
  const [emails, setEmails] = useState<EmailHeader[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [query, setQuery] = useState("");
  const [total, setTotal] = useState(0);
  const [priorityMode, setPriorityMode] = useState(false);

  const load = useCallback(async (q = "") => {
    setLoading(true);
    setError("");
    try {
      if (q.trim()) {
        const res = await mailApi.search(q);
        setEmails(res);
        setTotal(res.length);
      } else {
        const res = await mailApi.getMessages("inbox");
        setEmails(res.items);
        setTotal(res.total);
      }
    } catch (e) { setError((e as Error).message); }
    finally { setLoading(false); }
  }, []);

  useEffect(() => { load(); }, [load]);

  return (
    <div className="flex flex-col h-full">
      <div className="flex items-center gap-3 px-4 py-3 border-b border-gray-100 dark:border-gray-800 bg-white dark:bg-gray-900">
        <h2 className="font-semibold text-gray-800 dark:text-white text-base">Inbox</h2>
        <SearchBar value={query} onChange={setQuery} onSubmit={load} className="w-52" />
        <button
          onClick={() => setPriorityMode((p) => !p)}
          className={`ml-auto text-xs px-3 py-1.5 rounded-lg border transition-colors ${priorityMode ? "border-yellow-400 bg-yellow-50 dark:bg-yellow-900/20 text-yellow-700 dark:text-yellow-400" : "border-gray-300 dark:border-gray-600 text-gray-500 hover:bg-gray-50 dark:hover:bg-gray-800"}`}
        >
          ✦ Priority
        </button>
        <span className="text-xs text-gray-400">{total}</span>
      </div>

      {error ? (
        <div className="flex items-center justify-center h-64 text-red-500 text-sm">{error}</div>
      ) : priorityMode ? (
        <PriorityInbox />
      ) : (
        <EmailList emails={emails} folder="inbox" isLoading={loading} onRefresh={() => load(query)} />
      )}
    </div>
  );
}
