"use client";

import { useEffect, useState, useCallback } from "react";
import { useParams } from "next/navigation";
import { EmailList } from "../../../components/mail/EmailList";
import { SearchBar } from "../../../components/mail/SearchBar";
import { mailApi } from "../../../lib/api";
import type { EmailHeader } from "../../../types";

export default function FolderPage() {
  const { folder } = useParams<{ folder: string }>();
  const [emails, setEmails] = useState<EmailHeader[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [query, setQuery] = useState("");
  const [page, setPage] = useState(1);
  const [total, setTotal] = useState(0);

  const load = useCallback(async (q = query, p = page) => {
    setLoading(true);
    setError("");
    try {
      if (q.trim()) {
        const results = await mailApi.search(q);
        setEmails(results.filter((e) => e.folder === folder));
        setTotal(results.length);
      } else {
        const res = await mailApi.getMessages(folder, p);
        setEmails(res.items);
        setTotal(res.total);
      }
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setLoading(false);
    }
  }, [folder, query, page]);

  useEffect(() => { load(query, 1); setPage(1); }, [folder]);

  const folderLabel = folder.charAt(0).toUpperCase() + folder.slice(1);

  return (
    <div className="flex flex-col h-full">
      {/* Header */}
      <div className="flex items-center justify-between px-4 py-3 border-b border-gray-100 dark:border-gray-800 bg-white dark:bg-gray-900">
        <h2 className="font-semibold text-gray-800 dark:text-white text-base">{folderLabel}</h2>
        <div className="flex items-center gap-3">
          <SearchBar
            value={query}
            onChange={setQuery}
            onSubmit={(q) => load(q, 1)}
            className="w-56"
          />
          <span className="text-xs text-gray-400 hidden sm:block">{total} messages</span>
        </div>
      </div>

      {error ? (
        <div className="flex items-center justify-center h-64 text-red-500 text-sm">{error}</div>
      ) : (
        <EmailList
          emails={emails}
          folder={folder}
          isLoading={loading}
          onRefresh={() => load(query, page)}
        />
      )}

      {/* Pagination */}
      {!loading && total > 50 && !query && (
        <div className="flex justify-center gap-2 p-3 border-t border-gray-100 dark:border-gray-800">
          <button disabled={page === 1} onClick={() => { const p = page - 1; setPage(p); load(query, p); }} className="px-3 py-1 text-sm rounded border border-gray-300 dark:border-gray-600 disabled:opacity-40 hover:bg-gray-50 dark:hover:bg-gray-800">Prev</button>
          <span className="px-3 py-1 text-sm text-gray-500">Page {page}</span>
          <button disabled={page * 50 >= total} onClick={() => { const p = page + 1; setPage(p); load(query, p); }} className="px-3 py-1 text-sm rounded border border-gray-300 dark:border-gray-600 disabled:opacity-40 hover:bg-gray-50 dark:hover:bg-gray-800">Next</button>
        </div>
      )}
    </div>
  );
}
