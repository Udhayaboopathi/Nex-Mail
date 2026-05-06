"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { Trash2, Archive, Mail, MailOpen, Flag, AlertTriangle } from "lucide-react";
import { EmailListItem } from "./EmailListItem";
import { toast } from "../ui/Toast";
import { mailApi } from "../../lib/api";
import type { EmailHeader } from "../../types";

interface EmailListProps {
  emails: EmailHeader[];
  folder: string;
  isLoading?: boolean;
  onRefresh?: () => void;
}

const skeletonRows = Array.from({ length: 8 });

export function EmailList({ emails, folder, isLoading = false, onRefresh }: EmailListProps) {
  const router = useRouter();
  const [selected, setSelected] = useState<Set<string>>(new Set());
  const [allChecked, setAllChecked] = useState(false);

  function toggleAll(checked: boolean) {
    setAllChecked(checked);
    setSelected(checked ? new Set(emails.map((e) => e.uid)) : new Set());
  }

  function toggleOne(uid: string, checked: boolean) {
    setSelected((prev) => {
      const next = new Set(prev);
      checked ? next.add(uid) : next.delete(uid);
      return next;
    });
  }

  async function bulkAction(action: "delete" | "archive" | "read" | "unread" | "spam") {
    if (selected.size === 0) return;
    const uids = Array.from(selected);

    try {
      await Promise.all(
        uids.map((uid) => {
          if (action === "delete") return mailApi.deleteMessage(folder, uid);
          if (action === "archive") return mailApi.moveMessage(folder, uid, "archive");
          if (action === "spam") return mailApi.moveMessage(folder, uid, "spam");
          if (action === "read") return mailApi.updateFlags(folder, uid, ["\\Seen"], true);
          return mailApi.updateFlags(folder, uid, ["\\Seen"], false);
        })
      );
      toast(`${uids.length} email(s) ${action === "delete" ? "deleted" : action === "archive" ? "archived" : "updated"}`, "success");
      setSelected(new Set());
      setAllChecked(false);
      onRefresh?.();
    } catch {
      toast("Action failed, please retry", "error");
    }
  }

  if (isLoading) {
    return (
      <div className="divide-y divide-gray-100 dark:divide-gray-800">
        {skeletonRows.map((_, i) => (
          <div key={i} className="flex items-start gap-3 px-4 py-3 animate-pulse">
            <div className="w-4 h-4 bg-gray-200 dark:bg-gray-700 rounded mt-1" />
            <div className="w-8 h-8 bg-gray-200 dark:bg-gray-700 rounded-full shrink-0 mt-0.5" />
            <div className="flex-1 space-y-2">
              <div className="h-3 bg-gray-200 dark:bg-gray-700 rounded w-2/5" />
              <div className="h-3 bg-gray-200 dark:bg-gray-700 rounded w-3/5" />
              <div className="h-2 bg-gray-100 dark:bg-gray-800 rounded w-4/5" />
            </div>
          </div>
        ))}
      </div>
    );
  }

  if (emails.length === 0) {
    return (
      <div className="flex flex-col items-center justify-center h-64 text-gray-400 dark:text-gray-600">
        <Mail className="w-16 h-16 mb-4 opacity-30" />
        <p className="text-lg font-medium">No messages</p>
        <p className="text-sm mt-1">This folder is empty.</p>
      </div>
    );
  }

  return (
    <div className="flex flex-col h-full">
      {/* Bulk toolbar */}
      <div className="flex items-center gap-2 px-4 py-2 border-b border-gray-100 dark:border-gray-800 bg-white dark:bg-gray-900">
        <input
          type="checkbox"
          checked={allChecked}
          onChange={(e) => toggleAll(e.target.checked)}
          className="accent-indigo-600"
          aria-label="Select all"
        />
        {selected.size > 0 && (
          <>
            <span className="text-xs text-gray-500 dark:text-gray-400 mr-1">{selected.size} selected</span>
            <button onClick={() => bulkAction("read")} title="Mark read" className="p-1.5 rounded hover:bg-gray-100 dark:hover:bg-gray-800">
              <MailOpen className="w-4 h-4 text-gray-600 dark:text-gray-400" />
            </button>
            <button onClick={() => bulkAction("unread")} title="Mark unread" className="p-1.5 rounded hover:bg-gray-100 dark:hover:bg-gray-800">
              <Mail className="w-4 h-4 text-gray-600 dark:text-gray-400" />
            </button>
            <button onClick={() => bulkAction("archive")} title="Archive" className="p-1.5 rounded hover:bg-gray-100 dark:hover:bg-gray-800">
              <Archive className="w-4 h-4 text-gray-600 dark:text-gray-400" />
            </button>
            <button onClick={() => bulkAction("spam")} title="Mark spam" className="p-1.5 rounded hover:bg-gray-100 dark:hover:bg-gray-800">
              <AlertTriangle className="w-4 h-4 text-yellow-500" />
            </button>
            <button onClick={() => bulkAction("delete")} title="Delete" className="p-1.5 rounded hover:bg-gray-100 dark:hover:bg-gray-800">
              <Trash2 className="w-4 h-4 text-red-500" />
            </button>
          </>
        )}
      </div>

      {/* List */}
      <div className="flex-1 overflow-y-auto">
        {emails.map((email) => (
          <EmailListItem
            key={email.uid}
            email={email}
            isChecked={selected.has(email.uid)}
            onClick={() => router.push(`/mail/${folder}/${email.uid}`)}
            onStar={() => {
              mailApi.updateFlags(folder, email.uid, ["\\Flagged"], !email.is_flagged)
                .then(onRefresh)
                .catch(() => toast("Failed to update star", "error"));
            }}
            onSelect={(checked) => toggleOne(email.uid, checked)}
          />
        ))}
      </div>
    </div>
  );
}
