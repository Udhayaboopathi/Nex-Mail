"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { Mail, Users, Globe, Archive, CheckCircle } from "lucide-react";
import { domainAdminApi } from "../../lib/api";
import { ProgressBar } from "../../components/ui/ProgressBar";
import type { DomainAdminStats } from "../../types";

export default function DomainAdminDashboard() {
  const [stats, setStats] = useState<DomainAdminStats | null>(null);
  const [onboarding, setOnboarding] = useState<Record<string, boolean>>({});
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    Promise.all([
      domainAdminApi.getStats(),
      domainAdminApi.getOnboarding(),
    ]).then(([s, o]) => {
      setStats(s as DomainAdminStats);
      setOnboarding(o as Record<string, boolean>);
    }).catch(() => undefined)
      .finally(() => setLoading(false));
  }, []);

  const onboardingSteps = [
    { key: "dns_verified", label: "DNS Verified", href: "/domain-admin/dns" },
    { key: "mailbox_created", label: "Mailbox Created", href: "/domain-admin/mailboxes" },
    { key: "dkim_added", label: "DKIM Added", href: "/domain-admin/dns" },
  ];

  const allDone = onboardingSteps.every((s) => onboarding[s.key]);

  if (loading) {
    return <div className="grid grid-cols-2 gap-4">{[1,2,3,4].map((i) => <div key={i} className="h-28 bg-white dark:bg-gray-900 rounded-xl animate-pulse" />)}</div>;
  }

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-gray-900 dark:text-white">Dashboard</h1>
        <p className="text-sm text-gray-500 dark:text-gray-400 mt-0.5">Domain overview</p>
      </div>

      {/* Onboarding checklist */}
      {!allDone && (
        <div className="bg-indigo-50 dark:bg-indigo-900/20 border border-indigo-200 dark:border-indigo-800 rounded-xl p-5">
          <p className="font-semibold text-indigo-800 dark:text-indigo-300 mb-3">Setup checklist</p>
          <div className="space-y-2">
            {onboardingSteps.map((s) => (
              <Link key={s.key} href={s.href} className="flex items-center gap-3 text-sm hover:underline">
                <CheckCircle className={`w-5 h-5 shrink-0 ${onboarding[s.key] ? "text-green-500" : "text-gray-300 dark:text-gray-600"}`} />
                <span className={onboarding[s.key] ? "line-through text-gray-400" : "text-indigo-700 dark:text-indigo-300"}>{s.label}</span>
              </Link>
            ))}
          </div>
        </div>
      )}

      {/* Stats */}
      {stats && (
        <>
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
            {[
              { label: "Mailboxes", value: stats.total_mailboxes, icon: Mail },
              { label: "Active", value: stats.active_mailboxes, icon: Users },
              { label: "Messages Today", value: stats.messages_today, icon: Archive },
              { label: "Storage Used", value: `${stats.used_storage_gb.toFixed(1)} GB`, icon: Globe },
            ].map(({ label, value, icon: Icon }) => (
              <div key={label} className="bg-white dark:bg-gray-900 rounded-xl p-4 border border-gray-100 dark:border-gray-800">
                <Icon className="w-5 h-5 text-indigo-500 mb-2" />
                <p className="text-xl font-bold text-gray-900 dark:text-white">{value}</p>
                <p className="text-xs text-gray-500 dark:text-gray-400 mt-0.5">{label}</p>
              </div>
            ))}
          </div>
          <div className="bg-white dark:bg-gray-900 rounded-xl p-5 border border-gray-100 dark:border-gray-800 max-w-md">
            <ProgressBar value={stats.used_storage_gb} max={stats.storage_quota_gb} label="Storage" showPercent />
          </div>
        </>
      )}
    </div>
  );
}
