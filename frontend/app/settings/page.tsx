"use client";

import Link from "next/link";
import { Shield, Key, Webhook, Filter, FileText, Tag, Mail } from "lucide-react";

const sections = [
  { href: "/settings/security", icon: Shield, label: "Security", desc: "2FA, PGP keys, sessions, password" },
  { href: "/settings/api-keys", icon: Key, label: "API Keys", desc: "Programmatic email access" },
  { href: "/settings/webhooks", icon: Webhook, label: "Webhooks", desc: "Event notifications" },
  { href: "/settings/rules", icon: Filter, label: "Rules", desc: "Auto-file incoming email" },
  { href: "/settings/templates", icon: FileText, label: "Templates", desc: "Reusable email templates" },
  { href: "/settings/labels", icon: Tag, label: "Labels", desc: "Organize with color labels" },
  { href: "/settings/autoresponder", icon: Mail, label: "Autoresponder", desc: "Out-of-office reply settings" },
];

export default function SettingsPage() {
  return (
    <div className="max-w-2xl mx-auto p-6 space-y-5">
      <h1 className="text-2xl font-bold text-gray-900 dark:text-white">Settings</h1>
      <div className="space-y-2">
        {sections.map(({ href, icon: Icon, label, desc }) => (
          <Link key={href} href={href} className="flex items-center gap-4 p-4 bg-white dark:bg-gray-900 rounded-xl border border-gray-100 dark:border-gray-800 hover:border-indigo-300 dark:hover:border-indigo-700 transition-colors">
            <div className="p-2.5 rounded-lg bg-indigo-50 dark:bg-indigo-900/20"><Icon className="w-5 h-5 text-indigo-600 dark:text-indigo-400" /></div>
            <div><p className="font-medium text-gray-900 dark:text-white">{label}</p><p className="text-sm text-gray-500 dark:text-gray-400">{desc}</p></div>
          </Link>
        ))}
      </div>
    </div>
  );
}
