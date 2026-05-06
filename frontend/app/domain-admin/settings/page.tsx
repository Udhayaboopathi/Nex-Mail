"use client";

import Link from "next/link";
import { Shield, Tag, Globe, FileText, Users } from "lucide-react";

const links = [
  { href: "/domain-admin/whitelabel", icon: Tag, label: "Whitelabel", desc: "Company name, logo, and brand color" },
  { href: "/domain-admin/retention", icon: FileText, label: "Retention", desc: "Auto-delete emails after N days" },
  { href: "/domain-admin/dns", icon: Globe, label: "DNS", desc: "Verify and configure DNS records" },
  { href: "/domain-admin/shared", icon: Users, label: "Shared Mailboxes", desc: "Manage shared team inboxes" },
  { href: "/domain-admin/ediscovery", icon: Shield, label: "eDiscovery", desc: "Compliance search and export" },
];

export default function DomainAdminSettings() {
  return (
    <div className="space-y-6 max-w-2xl">
      <h1 className="text-2xl font-bold text-gray-900 dark:text-white">Settings</h1>
      <div className="space-y-3">
        {links.map(({ href, icon: Icon, label, desc }) => (
          <Link key={href} href={href} className="flex items-center gap-4 p-4 bg-white dark:bg-gray-900 rounded-xl border border-gray-100 dark:border-gray-800 hover:border-indigo-300 dark:hover:border-indigo-700 transition-colors">
            <div className="p-2.5 rounded-lg bg-indigo-50 dark:bg-indigo-900/20"><Icon className="w-5 h-5 text-indigo-600 dark:text-indigo-400" /></div>
            <div><p className="font-medium text-gray-900 dark:text-white">{label}</p><p className="text-sm text-gray-500 dark:text-gray-400">{desc}</p></div>
          </Link>
        ))}
      </div>
    </div>
  );
}
