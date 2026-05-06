"use client";

import { useEffect, useState } from "react";
import { Zap } from "lucide-react";
import { aiApi, mailApi } from "../../lib/api";
import { EmailListItem } from "./EmailListItem";
import { useRouter } from "next/navigation";
import type { EmailHeader } from "../../types";

interface PrioritizedEmail extends EmailHeader {
  priority_score: number;
}

export function PriorityInbox() {
  const router = useRouter();
  const [items, setItems] = useState<PrioritizedEmail[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    async function load() {
      try {
        const result = await aiApi.priorityInbox();
        const emailsRaw = await mailApi.getMessages("inbox", 1, 50);
        const scoreMap = new Map(result.items.map((i) => [i.uid, i.priority_score]));
        const prioritized = emailsRaw.items
          .filter((e) => scoreMap.has(e.uid))
          .map((e) => ({ ...e, priority_score: scoreMap.get(e.uid)! }))
          .sort((a, b) => b.priority_score - a.priority_score)
          .slice(0, 10);
        setItems(prioritized);
      } catch {
        setError("Could not load priority inbox.");
      } finally {
        setLoading(false);
      }
    }
    load();
  }, []);

  if (loading) {
    return (
      <div className="p-6 animate-pulse space-y-3">
        {[1, 2, 3].map((i) => (
          <div key={i} className="h-14 bg-gray-100 dark:bg-gray-800 rounded-lg" />
        ))}
      </div>
    );
  }

  if (error) {
    return <div className="p-6 text-sm text-red-500">{error}</div>;
  }

  if (items.length === 0) {
    return (
      <div className="p-6 text-center text-gray-400 dark:text-gray-600">
        <Zap className="w-10 h-10 mx-auto mb-2 opacity-30" />
        <p className="text-sm">No priority emails right now.</p>
      </div>
    );
  }

  return (
    <div>
      <div className="flex items-center gap-2 px-4 py-3 border-b border-gray-100 dark:border-gray-800">
        <Zap className="w-4 h-4 text-yellow-500" />
        <span className="text-sm font-medium text-gray-700 dark:text-gray-300">Priority Inbox</span>
      </div>
      {items.map((email) => (
        <EmailListItem
          key={email.uid}
          email={email}
          onClick={() => router.push(`/mail/inbox/${email.uid}`)}
          onStar={() => undefined}
          onSelect={() => undefined}
        />
      ))}
    </div>
  );
}
