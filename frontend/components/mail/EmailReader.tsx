"use client";

import { useState } from "react";
import {
  Reply, Forward, Archive, Trash2, ChevronLeft, Tag,
  Lock, Unlock, ChevronDown, ChevronUp, AlertTriangle,
} from "lucide-react";
import { Avatar } from "../ui/Avatar";
import { Badge } from "../ui/Badge";
import { AttachmentViewer } from "./AttachmentViewer";
import { ThreadView } from "./ThreadView";
import { aiApi, mailApi, pgpApi } from "../../lib/api";
import { toast } from "../ui/Toast";
import { formatDate } from "../../lib/utils";
import { useRouter } from "next/navigation";
import type { EmailFull } from "../../types";

interface EmailReaderProps {
  email: EmailFull;
  folder: string;
  threadMessages?: EmailFull[];
  onReply?: () => void;
  onForward?: () => void;
}

export function EmailReader({ email, folder, threadMessages = [], onReply, onForward }: EmailReaderProps) {
  const router = useRouter();
  const [imagesBlocked, setImagesBlocked] = useState(true);
  const [aiOpen, setAiOpen] = useState(false);
  const [summary, setSummary] = useState("");
  const [smartReplies, setSmartReplies] = useState<string[]>([]);
  const [aiLoading, setAiLoading] = useState(false);
  const [decrypted, setDecrypted] = useState<string | null>(null);
  const [headerExpanded, setHeaderExpanded] = useState(false);
  const toList = Array.isArray(email.to) ? email.to : [];
  const ccList = Array.isArray(email.cc) ? email.cc : [];
  const fromText = typeof email.from === "string" ? email.from : "";

  const iframeSrc = imagesBlocked
    ? `<!DOCTYPE html><html><head><style>img,iframe,embed{display:none!important}</style></head><body style="font-family:sans-serif;font-size:14px;line-height:1.6;color:#1f2937;">${email.body_html ?? ""}</body></html>`
    : `<!DOCTYPE html><html><body style="font-family:sans-serif;font-size:14px;line-height:1.6;color:#1f2937;">${email.body_html ?? ""}</body></html>`;

  async function loadAi() {
    if (aiLoading) return;
    setAiLoading(true);
    try {
      const [sumRes, srRes] = await Promise.all([
        email.thread_id ? aiApi.summarize(email.thread_id) : Promise.resolve({ summary: "" }),
        aiApi.smartReply(email.message_id),
      ]);
      setSummary(sumRes.summary);
      setSmartReplies(srRes.suggestions);
    } catch {
      toast("AI features unavailable", "error");
    } finally {
      setAiLoading(false);
    }
  }

  async function handleDelete() {
    if (!confirm("Delete this message?")) return;
    await mailApi.deleteMessage(folder, email.uid).catch(() => toast("Delete failed", "error"));
    router.push(`/mail/${folder}`);
  }

  async function handleArchive() {
    await mailApi.moveMessage(folder, email.uid, "archive").catch(() => toast("Archive failed", "error"));
    router.push(`/mail/${folder}`);
  }

  async function handleDecrypt() {
    try {
      const res = await pgpApi.lookupKey(fromText) as { plaintext?: string };
      setDecrypted(res.plaintext ?? "(decryption failed)");
    } catch {
      toast("Could not decrypt message", "error");
    }
  }

  return (
    <div className="flex flex-col h-full bg-white dark:bg-gray-900">
      {/* Toolbar */}
      <div className="flex items-center gap-1 px-4 py-3 border-b border-gray-200 dark:border-gray-700">
        <button
          onClick={() => router.push(`/mail/${folder}`)}
          className="p-2 rounded-md hover:bg-gray-100 dark:hover:bg-gray-800 mr-2"
          aria-label="Back"
        >
          <ChevronLeft className="w-5 h-5 text-gray-600 dark:text-gray-400" />
        </button>
        <button onClick={onReply} title="Reply" className="p-2 rounded-md hover:bg-gray-100 dark:hover:bg-gray-800">
          <Reply className="w-4 h-4 text-gray-600 dark:text-gray-400" />
        </button>
        <button onClick={onForward} title="Forward" className="p-2 rounded-md hover:bg-gray-100 dark:hover:bg-gray-800">
          <Forward className="w-4 h-4 text-gray-600 dark:text-gray-400" />
        </button>
        <button onClick={handleArchive} title="Archive" className="p-2 rounded-md hover:bg-gray-100 dark:hover:bg-gray-800">
          <Archive className="w-4 h-4 text-gray-600 dark:text-gray-400" />
        </button>
        <button onClick={handleDelete} title="Delete" className="p-2 rounded-md hover:bg-gray-100 dark:hover:bg-gray-800">
          <Trash2 className="w-4 h-4 text-red-500" />
        </button>

        {email.is_pgp_encrypted && (
          <button
            onClick={handleDecrypt}
            title="Decrypt PGP"
            className="ml-auto flex items-center gap-1.5 px-3 py-1.5 rounded-md bg-indigo-50 dark:bg-indigo-900/30 text-indigo-700 dark:text-indigo-300 text-sm hover:bg-indigo-100"
          >
            {decrypted ? <Unlock className="w-4 h-4" /> : <Lock className="w-4 h-4" />}
            {decrypted ? "Decrypted" : "Decrypt"}
          </button>
        )}

        {/* AI Toggle */}
        <button
          onClick={() => { setAiOpen((o) => !o); if (!aiOpen) loadAi(); }}
          className="ml-auto flex items-center gap-1.5 px-3 py-1.5 rounded-md bg-yellow-50 dark:bg-yellow-900/20 text-yellow-700 dark:text-yellow-400 text-sm hover:bg-yellow-100"
        >
          ✦ AI
          {aiOpen ? <ChevronUp className="w-4 h-4" /> : <ChevronDown className="w-4 h-4" />}
        </button>
      </div>

      <div className="flex-1 overflow-y-auto px-6 py-4">
        {/* AI panel */}
        {aiOpen && (
          <div className="mb-4 rounded-xl border border-yellow-200 dark:border-yellow-800 bg-yellow-50/50 dark:bg-yellow-900/10 p-4">
            {aiLoading ? (
              <div className="animate-pulse space-y-2">
                <div className="h-3 bg-yellow-100 dark:bg-yellow-900/30 rounded w-3/4" />
                <div className="h-3 bg-yellow-100 dark:bg-yellow-900/30 rounded w-1/2" />
              </div>
            ) : (
              <>
                {summary && (
                  <p className="text-sm text-gray-700 dark:text-gray-300 mb-3">{summary}</p>
                )}
                {smartReplies.length > 0 && (
                  <div className="flex flex-wrap gap-2">
                    {smartReplies.map((r, i) => (
                      <button
                        key={i}
                        onClick={onReply}
                        className="px-3 py-1.5 rounded-full border border-yellow-300 dark:border-yellow-700 text-xs text-yellow-800 dark:text-yellow-300 bg-white dark:bg-gray-900 hover:bg-yellow-50 transition-colors"
                      >
                        {r}
                      </button>
                    ))}
                  </div>
                )}
              </>
            )}
          </div>
        )}

        {/* Images blocked banner */}
        {imagesBlocked && email.body_html && (
          <div className="flex items-center gap-3 mb-3 p-3 rounded-lg bg-amber-50 dark:bg-amber-900/20 border border-amber-200 dark:border-amber-800 text-sm">
            <AlertTriangle className="w-4 h-4 text-amber-600 shrink-0" />
            <span className="text-amber-700 dark:text-amber-400 flex-1">Remote images are blocked.</span>
            <button
              onClick={() => setImagesBlocked(false)}
              className="text-indigo-600 dark:text-indigo-400 font-medium hover:underline shrink-0"
            >
              Load images
            </button>
          </div>
        )}

        {/* Subject + sender */}
        <h1 className="text-xl font-semibold text-gray-900 dark:text-white mb-4">
          {email.subject || "(no subject)"}
        </h1>

        <div className="flex items-start gap-3 mb-4">
          <Avatar email={fromText} />
          <div className="flex-1 min-w-0">
            <div className="flex items-center gap-2 flex-wrap">
              <span className="font-medium text-gray-900 dark:text-white text-sm">{fromText}</span>
              {email.labels?.map((l) => (
                <span key={l.id} className="px-1.5 py-0.5 rounded text-xs text-white" style={{ background: l.color }}>
                  {l.name}
                </span>
              ))}
            </div>
            <button
              onClick={() => setHeaderExpanded((o) => !o)}
              className="flex items-center gap-1 text-xs text-gray-400 mt-0.5 hover:text-gray-600 dark:hover:text-gray-300"
            >
              to {toList.join(", ").slice(0, 50)}
              {ccList.length ? `, cc ${ccList.join(", ")}` : ""}
              {headerExpanded ? <ChevronUp className="w-3 h-3" /> : <ChevronDown className="w-3 h-3" />}
            </button>
            {headerExpanded && (
              <div className="mt-2 text-xs text-gray-500 dark:text-gray-400 space-y-0.5">
                <p><span className="font-medium">From:</span> {fromText}</p>
                <p><span className="font-medium">To:</span> {toList.join(", ")}</p>
                {ccList.length ? <p><span className="font-medium">CC:</span> {ccList.join(", ")}</p> : null}
                <p><span className="font-medium">Date:</span> {formatDate(email.date, { dateStyle: "long", timeStyle: "short" })}</p>
                <p><span className="font-medium">Message-ID:</span> {email.message_id}</p>
              </div>
            )}
          </div>
          <span className="text-xs text-gray-400 shrink-0">{formatDate(email.date)}</span>
        </div>

        {/* Status badges */}
        <div className="flex flex-wrap gap-2 mb-4">
          {!email.is_read && <Badge variant="info">Unread</Badge>}
          {email.is_flagged && <Badge variant="warning">Starred</Badge>}
          {email.is_pgp_encrypted && <Badge variant="purple">PGP Encrypted</Badge>}
          {email.read_receipt_token && <Badge>Read receipt</Badge>}
        </div>

        {/* Body */}
        <div className="rounded-lg border border-gray-200 dark:border-gray-700 overflow-hidden">
          {decrypted ? (
            <pre className="p-4 whitespace-pre-wrap text-sm text-gray-700 dark:text-gray-300">{decrypted}</pre>
          ) : email.body_html ? (
            <iframe
              srcDoc={iframeSrc}
              sandbox="allow-same-origin"
              className="w-full border-0 min-h-64 bg-white"
              style={{ height: "auto" }}
              onLoad={(e) => {
                const el = e.currentTarget;
                el.style.height = (el.contentDocument?.body?.scrollHeight ?? 400) + 32 + "px";
              }}
              title={`Email from ${fromText}`}
            />
          ) : (
            <pre className="p-4 whitespace-pre-wrap text-sm text-gray-700 dark:text-gray-300">
              {email.body_text}
            </pre>
          )}
        </div>

        {/* Attachments */}
        {(email.attachments ?? []).length > 0 && (
          <AttachmentViewer attachments={email.attachments ?? []} />
        )}

        {/* Thread */}
        {threadMessages.length > 1 && (
          <ThreadView messages={threadMessages} />
        )}
      </div>
    </div>
  );
}
