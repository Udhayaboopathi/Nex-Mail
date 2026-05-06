"use client";

import { useEffect, useState } from "react";
import { Users } from "lucide-react";
import { domainAdminApi } from "../../../lib/api";
import { toast } from "../../../components/ui/Toast";
import type { SharedMailbox } from "../../../types";

export default function SharedMailboxesPage() {
  const [mailboxes, setMailboxes] = useState<SharedMailbox[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    domainAdminApi.getSharedMailboxes().then(setMailboxes).catch((e) => toast(e.message, "error")).finally(() => setLoading(false));
  }, []);

  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-bold text-gray-900 dark:text-white">Shared Mailboxes</h1>
      {loading ? <div className="h-24 bg-white dark:bg-gray-900 rounded-xl animate-pulse" /> : mailboxes.length === 0 ? (
        <div className="text-center py-16 bg-white dark:bg-gray-900 rounded-xl border border-gray-100 dark:border-gray-800">
          <Users className="w-12 h-12 text-gray-300 dark:text-gray-600 mx-auto mb-3" />
          <p className="text-gray-500 text-sm">No shared mailboxes yet.</p>
        </div>
      ) : (
        <div className="space-y-4">
          {mailboxes.map((mb) => (
            <div key={mb.id} className="bg-white dark:bg-gray-900 rounded-xl border border-gray-100 dark:border-gray-800 p-4">
              <div className="flex items-center justify-between mb-3">
                <div className="flex items-center gap-2"><Users className="w-4 h-4 text-indigo-500" /><span className="font-medium text-gray-900 dark:text-white">{mb.display_name}</span></div>
                <span className="text-xs text-gray-400">{mb.members.length} member(s)</span>
              </div>
              <div className="space-y-1">
                {mb.members.map((m) => (
                  <div key={m.user_id} className="flex items-center justify-between text-sm text-gray-600 dark:text-gray-400 pl-6">
                    <span>{m.email}</span>
                    <span className="text-xs bg-gray-100 dark:bg-gray-800 px-2 py-0.5 rounded capitalize">{m.permission.replace("_", " ")}</span>
                  </div>
                ))}
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
