"use client";

import { useState, useEffect, useRef } from "react";
import { X, Paperclip, Clock, Send, ChevronDown, Minimize2, Maximize2 } from "lucide-react";
import { mailApi, templatesApi, contactsApi } from "../../lib/api";
import { toast } from "../ui/Toast";
import { cn } from "../../lib/utils";
import type { EmailTemplate, Contact } from "../../types";

interface ComposeModalProps {
  onClose: () => void;
  replyTo?: { from: string; subject: string; message_id: string };
  forwardOf?: { subject: string; body_text?: string; body_html?: string };
}

interface TagInputProps {
  values: string[];
  onChange: (vals: string[]) => void;
  placeholder: string;
  suggestions?: Contact[];
}

function TagInput({ values, onChange, placeholder, suggestions = [] }: TagInputProps) {
  const [input, setInput] = useState("");
  const [showSug, setShowSug] = useState(false);

  function add(val: string) {
    const trimmed = val.trim();
    if (trimmed && !values.includes(trimmed)) onChange([...values, trimmed]);
    setInput("");
    setShowSug(false);
  }

  function remove(val: string) {
    onChange(values.filter((v) => v !== val));
  }

  const filtered = suggestions.filter(
    (c) =>
      input.length > 0 &&
      (c.email.includes(input) || (c.name ?? "").toLowerCase().includes(input.toLowerCase())) &&
      !values.includes(c.email)
  );

  return (
    <div className="relative flex flex-wrap items-center gap-1 min-h-8 px-2 py-1">
      {values.map((v) => (
        <span key={v} className="flex items-center gap-1 px-2 py-0.5 rounded-full bg-indigo-100 dark:bg-indigo-900/40 text-indigo-800 dark:text-indigo-300 text-xs">
          {v}
          <button onClick={() => remove(v)} className="hover:text-red-500 ml-0.5">×</button>
        </span>
      ))}
      <input
        value={input}
        onChange={(e) => { setInput(e.target.value); setShowSug(true); }}
        onKeyDown={(e) => {
          if (e.key === "Enter" || e.key === "," || e.key === "Tab") {
            e.preventDefault();
            add(input);
          }
          if (e.key === "Backspace" && !input && values.length > 0) {
            onChange(values.slice(0, -1));
          }
        }}
        onBlur={() => { if (input) add(input); setShowSug(false); }}
        placeholder={values.length === 0 ? placeholder : ""}
        className="flex-1 min-w-24 outline-none bg-transparent text-sm text-gray-900 dark:text-gray-100 placeholder-gray-400"
      />
      {showSug && filtered.length > 0 && (
        <div className="absolute top-full left-0 mt-1 w-full bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-lg shadow-lg z-50">
          {filtered.slice(0, 5).map((c) => (
            <button
              key={c.id}
              onMouseDown={(e) => { e.preventDefault(); add(c.email); }}
              className="w-full flex items-center gap-2 px-3 py-2 text-sm hover:bg-gray-50 dark:hover:bg-gray-700 text-left"
            >
              <span className="font-medium text-gray-900 dark:text-gray-100">{c.name}</span>
              <span className="text-gray-400">{c.email}</span>
            </button>
          ))}
        </div>
      )}
    </div>
  );
}

export function ComposeModal({ onClose, replyTo, forwardOf }: ComposeModalProps) {
  const [to, setTo] = useState<string[]>(replyTo ? [replyTo.from] : []);
  const [cc, setCc] = useState<string[]>([]);
  const [bcc, setBcc] = useState<string[]>([]);
  const [subject, setSubject] = useState(
    replyTo ? `Re: ${replyTo.subject}` : forwardOf ? `Fwd: ${forwardOf.subject}` : ""
  );
  const [body, setBody] = useState(
    forwardOf ? `\n\n---------- Forwarded message ----------\n${forwardOf.body_text ?? ""}` : ""
  );
  const [bodyHtml, setBodyHtml] = useState(forwardOf?.body_html ?? "");
  const [isHtmlMode, setIsHtmlMode] = useState(false);
  const [showCc, setShowCc] = useState(false);
  const [showBcc, setShowBcc] = useState(false);
  const [minimized, setMinimized] = useState(false);
  const [sending, setSending] = useState(false);
  const [templates, setTemplates] = useState<EmailTemplate[]>([]);
  const [contacts, setContacts] = useState<Contact[]>([]);
  const [scheduleAt, setScheduleAt] = useState("");
  const draftTimer = useRef<ReturnType<typeof setTimeout>>();

  useEffect(() => {
    templatesApi.list().then(setTemplates).catch(() => undefined);
    contactsApi.list().then(setContacts).catch(() => undefined);
    return () => clearTimeout(draftTimer.current);
  }, []);

  function htmlToText(html: string): string {
    return html
      .replace(/<style[\s\S]*?<\/style>/gi, " ")
      .replace(/<script[\s\S]*?<\/script>/gi, " ")
      .replace(/<br\s*\/?>/gi, "\n")
      .replace(/<\/p>/gi, "\n")
      .replace(/<[^>]+>/g, " ")
      .replace(/&nbsp;/gi, " ")
      .replace(/&amp;/gi, "&")
      .replace(/&lt;/gi, "<")
      .replace(/&gt;/gi, ">")
      .replace(/\s+\n/g, "\n")
      .replace(/\n{3,}/g, "\n\n")
      .trim();
  }

  async function handleSend() {
    if (to.length === 0) { toast("Add at least one recipient", "error"); return; }
    if (!subject.trim()) { toast("Subject is required", "error"); return; }
    setSending(true);
    try {
      if (scheduleAt) {
        await mailApi.scheduleEmail({
          to_addresses: to,
          cc_addresses: cc,
          bcc_addresses: bcc,
          subject,
          body_text: isHtmlMode ? htmlToText(bodyHtml) : body,
          body_html: isHtmlMode ? bodyHtml : null,
          send_at: scheduleAt,
        });
        toast("Email scheduled!", "success");
      } else {
        await mailApi.sendEmail({
          to_addresses: to,
          cc_addresses: cc,
          bcc_addresses: bcc,
          subject,
          body_text: isHtmlMode ? htmlToText(bodyHtml) : body,
          body_html: isHtmlMode ? bodyHtml : null,
          reply_to: replyTo?.message_id,
        });
        toast("Email sent!", "success");
      }
      onClose();
    } catch (err) {
      toast((err as Error).message ?? "Failed to send", "error");
    } finally {
      setSending(false);
    }
  }

  if (minimized) {
    return (
      <div className="fixed bottom-0 right-6 z-50 w-72 bg-white dark:bg-gray-900 border border-gray-200 dark:border-gray-700 rounded-t-lg shadow-xl">
        <div className="flex items-center justify-between px-4 py-2 border-b border-gray-100 dark:border-gray-800 cursor-pointer" onClick={() => setMinimized(false)}>
          <span className="text-sm font-medium text-gray-700 dark:text-gray-300 truncate">{subject || "New message"}</span>
          <div className="flex items-center gap-1">
            <Maximize2 className="w-4 h-4 text-gray-400" />
            <X className="w-4 h-4 text-gray-400" onClick={(e) => { e.stopPropagation(); onClose(); }} />
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="fixed inset-0 z-50 flex items-end justify-end md:items-end md:justify-end pointer-events-none">
      <div className="pointer-events-auto w-full max-w-xl mb-0 md:mb-4 md:mr-4 bg-white dark:bg-gray-900 border border-gray-200 dark:border-gray-700 rounded-t-xl md:rounded-xl shadow-2xl flex flex-col max-h-[85vh]">
        {/* Header */}
        <div className="flex items-center justify-between px-4 py-3 border-b border-gray-100 dark:border-gray-800 bg-gray-50 dark:bg-gray-800 rounded-t-xl">
          <span className="text-sm font-semibold text-gray-700 dark:text-gray-200">
            {replyTo ? "Reply" : forwardOf ? "Forward" : "New Message"}
          </span>
          <div className="flex items-center gap-1">
            <button onClick={() => setMinimized(true)} className="p-1.5 rounded hover:bg-gray-200 dark:hover:bg-gray-700">
              <Minimize2 className="w-4 h-4 text-gray-500" />
            </button>
            <button onClick={onClose} className="p-1.5 rounded hover:bg-gray-200 dark:hover:bg-gray-700">
              <X className="w-4 h-4 text-gray-500" />
            </button>
          </div>
        </div>

        {/* Fields */}
        <div className="divide-y divide-gray-100 dark:divide-gray-800">
          <div className="flex items-center gap-2 px-4 py-1">
            <span className="text-xs font-medium text-gray-400 w-8 shrink-0">To</span>
            <TagInput values={to} onChange={setTo} placeholder="Add recipients" suggestions={contacts} />
            <div className="flex gap-2 text-xs text-gray-400 shrink-0">
              {!showCc && <button onClick={() => setShowCc(true)} className="hover:text-indigo-600">Cc</button>}
              {!showBcc && <button onClick={() => setShowBcc(true)} className="hover:text-indigo-600">Bcc</button>}
            </div>
          </div>
          {showCc && (
            <div className="flex items-center gap-2 px-4 py-1">
              <span className="text-xs font-medium text-gray-400 w-8 shrink-0">Cc</span>
              <TagInput values={cc} onChange={setCc} placeholder="" suggestions={contacts} />
            </div>
          )}
          {showBcc && (
            <div className="flex items-center gap-2 px-4 py-1">
              <span className="text-xs font-medium text-gray-400 w-8 shrink-0">Bcc</span>
              <TagInput values={bcc} onChange={setBcc} placeholder="" suggestions={contacts} />
            </div>
          )}
          <div className="flex items-center gap-2 px-4 py-1">
            <span className="text-xs font-medium text-gray-400 w-8 shrink-0">Sub</span>
            <input
              value={subject}
              onChange={(e) => setSubject(e.target.value)}
              placeholder="Subject"
              className="flex-1 text-sm outline-none bg-transparent text-gray-900 dark:text-gray-100 placeholder-gray-400 py-1"
            />
            {templates.length > 0 && (
              <div className="relative">
                <select
                  defaultValue=""
                  onChange={(e) => {
                    const tmpl = templates.find((t) => t.id === e.target.value);
                    if (tmpl) {
                      setSubject(tmpl.subject);
                      setBody(tmpl.body_text ?? "");
                      setBodyHtml(tmpl.body_html ?? "");
                    }
                    e.target.value = "";
                  }}
                  className="text-xs text-gray-400 outline-none bg-transparent cursor-pointer"
                >
                  <option value="" disabled>Template</option>
                  {templates.map((t) => <option key={t.id} value={t.id}>{t.name}</option>)}
                </select>
              </div>
            )}
            <button
              type="button"
              onClick={() => setIsHtmlMode((v) => !v)}
              className="text-xs px-2 py-1 rounded border border-gray-200 dark:border-gray-700 text-gray-500 hover:text-indigo-600"
              title="Switch compose format"
            >
              {isHtmlMode ? "Plain" : "HTML"}
            </button>
          </div>
        </div>

        {/* Body */}
        {isHtmlMode ? (
          <textarea
            value={bodyHtml}
            onChange={(e) => setBodyHtml(e.target.value)}
            placeholder="<p>Write your HTML message…</p>"
            className="flex-1 px-4 py-3 font-mono text-sm resize-none outline-none bg-transparent text-gray-900 dark:text-gray-100 placeholder-gray-400 min-h-32"
          />
        ) : (
          <textarea
            value={body}
            onChange={(e) => setBody(e.target.value)}
            placeholder="Write your message…"
            className="flex-1 px-4 py-3 text-sm resize-none outline-none bg-transparent text-gray-900 dark:text-gray-100 placeholder-gray-400 min-h-32"
          />
        )}

        {/* Footer */}
        <div className="flex items-center gap-2 px-4 py-3 border-t border-gray-100 dark:border-gray-800">
          <button
            onClick={handleSend}
            disabled={sending}
            className="flex items-center gap-2 px-4 py-2 rounded-lg bg-indigo-600 hover:bg-indigo-700 dark:bg-indigo-500 dark:hover:bg-indigo-600 text-white text-sm font-medium transition-colors disabled:opacity-60"
          >
            <Send className="w-4 h-4" />
            {sending ? "Sending…" : scheduleAt ? "Schedule" : "Send"}
          </button>

          <button className="p-2 rounded-lg hover:bg-gray-100 dark:hover:bg-gray-800 text-gray-500" title="Attach file">
            <Paperclip className="w-4 h-4" />
          </button>

          {/* Schedule */}
          <div className="relative ml-auto flex items-center gap-1">
            <Clock className="w-4 h-4 text-gray-400" />
            <select
              value={scheduleAt}
              onChange={(e) => setScheduleAt(e.target.value)}
              className="text-xs text-gray-500 dark:text-gray-400 outline-none bg-transparent cursor-pointer"
            >
              <option value="">Send now</option>
              <option value={new Date(Date.now() + 3600000).toISOString()}>In 1 hour</option>
              <option value={(() => { const d = new Date(); d.setDate(d.getDate() + 1); d.setHours(8, 0, 0, 0); return d.toISOString(); })()}>Tomorrow 8 am</option>
            </select>
            <ChevronDown className="w-3 h-3 text-gray-400" />
          </div>
        </div>
      </div>
    </div>
  );
}
