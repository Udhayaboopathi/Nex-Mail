"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import {
  Inbox, Send, Archive, Trash2, Star, Tag, Settings, Calendar,
  CheckSquare, StickyNote, Users, Globe, FileText, Shield,
  BarChart2, RefreshCcw, Search, Mail,
} from "lucide-react";
import { cn } from "../../lib/utils";
import { ProgressBar } from "../ui/ProgressBar";
import type { FolderInfo, Label } from "../../types";

interface SidebarProps {
  role: "user" | "domain_admin" | "super_admin";
  folders?: FolderInfo[];
  labels?: Label[];
  usedMb?: number;
  quotaMb?: number;
  onCompose?: () => void;
}

const userNav = [
  { href: "/mail/inbox",   icon: Inbox,   label: "Inbox",   folder: "inbox" },
  { href: "/mail/sent",    icon: Send,    label: "Sent",    folder: "sent" },
  { href: "/mail/drafts",  icon: FileText, label: "Drafts", folder: "drafts" },
  { href: "/mail/starred", icon: Star,    label: "Starred", folder: "starred" },
  { href: "/mail/spam",    icon: Shield,  label: "Spam",    folder: "spam" },
  { href: "/mail/trash",   icon: Trash2,  label: "Trash",   folder: "trash" },
  { href: "/mail/archive", icon: Archive, label: "Archive", folder: "archive" },
];

const domainAdminNav = [
  { href: "/domain-admin",             icon: BarChart2,   label: "Dashboard" },
  { href: "/domain-admin/mailboxes",   icon: Mail,        label: "Mailboxes" },
  { href: "/domain-admin/aliases",     icon: RefreshCcw,  label: "Aliases" },
  { href: "/domain-admin/dns",         icon: Globe,       label: "DNS" },
  { href: "/domain-admin/shared",      icon: Users,       label: "Shared" },
  { href: "/domain-admin/backup",      icon: Archive,     label: "Backup" },
  { href: "/domain-admin/whitelabel",  icon: Tag,         label: "Whitelabel" },
  { href: "/domain-admin/ediscovery",  icon: Search,      label: "eDiscovery" },
  { href: "/domain-admin/retention",   icon: FileText,    label: "Retention" },
  { href: "/domain-admin/audit",       icon: Shield,      label: "Audit Logs" },
  { href: "/domain-admin/settings",    icon: Settings,    label: "Settings" },
];

const superAdminNav = [
  { href: "/super-admin",              icon: BarChart2,   label: "Dashboard" },
  { href: "/super-admin/domains",      icon: Globe,       label: "Domains" },
  { href: "/super-admin/backups",      icon: Archive,     label: "Backups" },
  { href: "/super-admin/audit-logs",   icon: Shield,      label: "Audit Logs" },
  { href: "/super-admin/settings",     icon: Settings,    label: "Settings" },
];

export function Sidebar({ role, folders = [], labels = [], usedMb = 0, quotaMb = 1024, onCompose }: SidebarProps) {
  const pathname = usePathname();
  const nav = role === "super_admin" ? superAdminNav : role === "domain_admin" ? domainAdminNav : userNav;
  const unreadMap = Object.fromEntries(folders.map((f) => [f.name, f.unread]));

  return (
    <aside className="w-60 min-h-screen bg-white dark:bg-gray-900 border-r border-gray-200 dark:border-gray-800 flex flex-col">
      {/* Logo */}
      <div className="px-5 py-4 flex items-center gap-2 border-b border-gray-200 dark:border-gray-800">
        <Mail className="w-6 h-6 text-indigo-600 dark:text-indigo-400" />
        <span className="font-bold text-lg text-gray-900 dark:text-white">Nex Mail</span>
      </div>

      {/* Compose (user only) */}
      {role === "user" && onCompose && (
        <div className="px-4 pt-4">
          <button
            onClick={onCompose}
            className="w-full py-2 rounded-lg bg-indigo-600 hover:bg-indigo-700 dark:bg-indigo-500 dark:hover:bg-indigo-600 text-white text-sm font-medium transition-colors"
          >
            + Compose
          </button>
        </div>
      )}

      {/* Navigation */}
      <nav className="flex-1 overflow-y-auto px-2 py-3 space-y-0.5">
        {nav.map(({ href, icon: Icon, label, folder }: { href: string; icon: React.ElementType; label: string; folder?: string }) => {
          const active = pathname === href || pathname.startsWith(href + "/");
          const unread = folder ? unreadMap[folder] : 0;
          return (
            <Link
              key={href}
              href={href}
              className={cn(
                "flex items-center gap-3 px-3 py-2 rounded-md text-sm transition-colors",
                active
                  ? "bg-indigo-50 dark:bg-indigo-900/30 text-indigo-700 dark:text-indigo-300 font-medium"
                  : "text-gray-700 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-800"
              )}
            >
              <Icon className="w-4 h-4 shrink-0" />
              <span className="flex-1">{label}</span>
              {unread > 0 && (
                <span className="text-xs bg-indigo-600 dark:bg-indigo-500 text-white rounded-full min-w-[20px] h-5 flex items-center justify-center px-1">
                  {unread > 99 ? "99+" : unread}
                </span>
              )}
            </Link>
          );
        })}

        {/* User: extra nav */}
        {role === "user" && (
          <>
            <hr className="my-2 border-gray-200 dark:border-gray-800" />
            {[
              { href: "/calendar", icon: Calendar, label: "Calendar" },
              { href: "/tasks",    icon: CheckSquare, label: "Tasks" },
              { href: "/notes",    icon: StickyNote, label: "Notes" },
              { href: "/settings", icon: Settings,   label: "Settings" },
            ].map(({ href, icon: Icon, label }) => (
              <Link
                key={href}
                href={href}
                className={cn(
                  "flex items-center gap-3 px-3 py-2 rounded-md text-sm transition-colors",
                  pathname.startsWith(href)
                    ? "bg-indigo-50 dark:bg-indigo-900/30 text-indigo-700 dark:text-indigo-300 font-medium"
                    : "text-gray-700 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-800"
                )}
              >
                <Icon className="w-4 h-4 shrink-0" />
                <span>{label}</span>
              </Link>
            ))}

            {/* Labels */}
            {labels.length > 0 && (
              <>
                <hr className="my-2 border-gray-200 dark:border-gray-800" />
                <p className="px-3 text-xs font-medium text-gray-500 dark:text-gray-500 uppercase tracking-wider mb-1">Labels</p>
                {labels.map((l) => (
                  <Link
                    key={l.id}
                    href={`/mail/label/${l.id}`}
                    className="flex items-center gap-3 px-3 py-1.5 rounded-md text-sm text-gray-700 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-800 transition-colors"
                  >
                    <span className="w-3 h-3 rounded-full shrink-0" style={{ background: l.color }} />
                    <span>{l.name}</span>
                  </Link>
                ))}
              </>
            )}
          </>
        )}
      </nav>

      {/* Storage bar (user / domain-admin) */}
      {role !== "super_admin" && (
        <div className="px-4 py-4 border-t border-gray-200 dark:border-gray-800">
          <ProgressBar
            value={usedMb}
            max={quotaMb}
            label={`${(usedMb / 1024).toFixed(1)} / ${(quotaMb / 1024).toFixed(1)} GB`}
            showPercent
          />
        </div>
      )}
    </aside>
  );
}
