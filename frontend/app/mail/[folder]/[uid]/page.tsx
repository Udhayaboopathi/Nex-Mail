"use client";

import { useEffect, useState } from "react";
import { useParams } from "next/navigation";
import { mailApi } from "../../../../lib/api";
import { EmailReader } from "../../../../components/mail/EmailReader";
import { ComposeModal } from "../../../../components/mail/ComposeModal";
import type { EmailFull } from "../../../../types";

export default function EmailPage() {
  const { folder, uid } = useParams<{ folder: string; uid: string }>();
  const [email, setEmail] = useState<EmailFull | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [replyOpen, setReplyOpen] = useState(false);
  const [forwardOpen, setForwardOpen] = useState(false);

  useEffect(() => {
    setLoading(true);
    mailApi.getMessage(folder, uid)
      .then((e) => {
        setEmail(e);
        if (!e.is_read) {
          mailApi.updateFlags(folder, uid, ["\\Seen"], true).catch(() => undefined);
        }
      })
      .catch((e) => setError(e.message))
      .finally(() => setLoading(false));
  }, [folder, uid]);

  if (loading) {
    return (
      <div className="p-6 space-y-4 animate-pulse">
        <div className="h-8 bg-gray-100 dark:bg-gray-800 rounded w-2/3" />
        <div className="h-4 bg-gray-100 dark:bg-gray-800 rounded w-1/3" />
        <div className="h-48 bg-gray-100 dark:bg-gray-800 rounded-xl mt-6" />
      </div>
    );
  }

  if (error || !email) {
    return (
      <div className="flex items-center justify-center h-64 text-red-500 text-sm">
        {error || "Email not found."}
      </div>
    );
  }

  return (
    <>
      <EmailReader
        email={email}
        folder={folder}
        onReply={() => setReplyOpen(true)}
        onForward={() => setForwardOpen(true)}
      />
      {replyOpen && (
        <ComposeModal
          onClose={() => setReplyOpen(false)}
          replyTo={{ from: email.from, subject: email.subject, message_id: email.message_id }}
        />
      )}
      {forwardOpen && (
        <ComposeModal
          onClose={() => setForwardOpen(false)}
          forwardOf={{ subject: email.subject, body_text: email.body_text, body_html: email.body_html }}
        />
      )}
    </>
  );
}
