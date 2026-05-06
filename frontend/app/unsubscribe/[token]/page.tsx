"use client";

import { useState } from "react";
import { useParams } from "next/navigation";
import { CheckCircle, XCircle, Mail } from "lucide-react";

export default function UnsubscribePage() {
  const { token } = useParams<{ token: string }>();
  const [status, setStatus] = useState<"idle" | "loading" | "done" | "error">("idle");

  async function handleUnsubscribe() {
    setStatus("loading");
    try {
      const res = await fetch(`/api/unsubscribe/${token}`, { method: "POST" });
      if (res.ok) setStatus("done");
      else setStatus("error");
    } catch { setStatus("error"); }
  }

  return (
    <div className="min-h-screen bg-gray-50 dark:bg-gray-950 flex items-center justify-center p-4">
      <div className="bg-white dark:bg-gray-900 rounded-2xl shadow-lg border border-gray-100 dark:border-gray-800 p-10 max-w-sm w-full text-center">
        <Mail className="w-12 h-12 text-indigo-500 mx-auto mb-4" />
        {status === "idle" && (
          <>
            <h1 className="text-xl font-bold text-gray-900 dark:text-white mb-2">Unsubscribe</h1>
            <p className="text-sm text-gray-500 dark:text-gray-400 mb-6">You will no longer receive emails from this sender.</p>
            <button onClick={handleUnsubscribe} className="w-full py-2.5 rounded-lg bg-red-600 hover:bg-red-700 text-white font-medium">Unsubscribe</button>
          </>
        )}
        {status === "loading" && <div className="w-8 h-8 border-2 border-indigo-600 border-t-transparent rounded-full animate-spin mx-auto" />}
        {status === "done" && (
          <>
            <CheckCircle className="w-12 h-12 text-green-500 mx-auto mb-3" />
            <p className="font-medium text-gray-900 dark:text-white">You&apos;ve been unsubscribed.</p>
            <p className="text-sm text-gray-500 dark:text-gray-400 mt-1">You won&apos;t receive further emails from this sender.</p>
          </>
        )}
        {status === "error" && (
          <>
            <XCircle className="w-12 h-12 text-red-500 mx-auto mb-3" />
            <p className="font-medium text-gray-900 dark:text-white">Something went wrong.</p>
            <p className="text-sm text-gray-500 dark:text-gray-400 mt-1">This link may be expired or invalid.</p>
          </>
        )}
      </div>
    </div>
  );
}
