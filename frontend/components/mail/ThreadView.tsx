"use client";

import { useState } from "react";
import { ChevronDown, ChevronUp } from "lucide-react";
import { Avatar } from "../ui/Avatar";
import { AttachmentViewer } from "./AttachmentViewer";
import { formatDate } from "../../lib/utils";
import type { EmailFull } from "../../types";

interface ThreadViewProps {
  messages: EmailFull[];
}

export function ThreadView({ messages }: ThreadViewProps) {
  const [expandedIds, setExpandedIds] = useState<Set<string>>(
    new Set([messages[messages.length - 1]?.uid])
  );

  function toggle(uid: string) {
    setExpandedIds((prev) => {
      const next = new Set(prev);
      next.has(uid) ? next.delete(uid) : next.add(uid);
      return next;
    });
  }

  if (messages.length === 0) return null;

  return (
    <div className="mt-6 border-t border-gray-200 dark:border-gray-700">
      <p className="text-xs font-semibold text-gray-500 dark:text-gray-400 uppercase tracking-wider px-1 py-3">
        Thread ({messages.length})
      </p>
      <div className="space-y-2">
        {messages.map((msg) => {
          const expanded = expandedIds.has(msg.uid);
          return (
            <div
              key={msg.uid}
              className="border border-gray-200 dark:border-gray-700 rounded-lg overflow-hidden"
            >
              {/* Header (always visible) */}
              <button
                onClick={() => toggle(msg.uid)}
                className="w-full flex items-center gap-3 px-4 py-3 bg-gray-50 dark:bg-gray-800/50 hover:bg-gray-100 dark:hover:bg-gray-800 transition-colors text-left"
              >
                <Avatar email={msg.from} size="sm" />
                <div className="flex-1 min-w-0">
                  <p className="text-sm font-medium text-gray-800 dark:text-gray-200 truncate">{msg.from}</p>
                  {!expanded && (
                    <p className="text-xs text-gray-400 truncate">{msg.preview}</p>
                  )}
                </div>
                <span className="text-xs text-gray-400 shrink-0">{formatDate(msg.date)}</span>
                {expanded ? (
                  <ChevronUp className="w-4 h-4 text-gray-400 shrink-0" />
                ) : (
                  <ChevronDown className="w-4 h-4 text-gray-400 shrink-0" />
                )}
              </button>

              {/* Body */}
              {expanded && (
                <div className="px-4 py-4 bg-white dark:bg-gray-900">
                  {msg.body_html ? (
                    <iframe
                      srcDoc={`<!DOCTYPE html><html><body style="font-family:sans-serif;font-size:14px;line-height:1.6;color:#1f2937;">${msg.body_html}</body></html>`}
                      sandbox="allow-same-origin"
                      className="w-full border-0 min-h-32"
                      style={{ height: "auto" }}
                      onLoad={(e) => {
                        const el = e.currentTarget;
                        el.style.height = el.contentDocument?.body.scrollHeight + "px";
                      }}
                      title={`Message from ${msg.from}`}
                    />
                  ) : (
                    <pre className="whitespace-pre-wrap text-sm text-gray-700 dark:text-gray-300">
                      {msg.body_text}
                    </pre>
                  )}
                  {(msg.attachments ?? []).length > 0 && (
                    <AttachmentViewer attachments={msg.attachments ?? []} />
                  )}
                </div>
              )}
            </div>
          );
        })}
      </div>
    </div>
  );
}
