"use client";

import { useState, useEffect } from "react";
import type { ReactNode } from "react";
import { useRouter } from "next/navigation";
import { Sidebar } from "../../components/layout/Sidebar";
import { Topbar } from "../../components/layout/Topbar";
import { MobileSidebar } from "../../components/layout/MobileSidebar";
import { ComposeModal } from "../../components/mail/ComposeModal";
import { getToken, getRole } from "../../lib/auth";
import { mailApi, labelsApi } from "../../lib/api";
import type { FolderInfo, Label } from "../../types";

export default function MailLayout({ children }: { children: ReactNode }) {
  const router = useRouter();
  const [mobileOpen, setMobileOpen] = useState(false);
  const [composeOpen, setComposeOpen] = useState(false);
  const [isDark, setIsDark] = useState(false);
  const [folders, setFolders] = useState<FolderInfo[]>([]);
  const [labels, setLabels] = useState<Label[]>([]);
  const email = typeof window !== "undefined" ? localStorage.getItem("nex_email") ?? "" : "";

  useEffect(() => {
    if (!getToken() || getRole() !== "user") {
      router.replace("/login");
      return;
    }
    mailApi.getFolders().then((f) => setFolders(
      f.map((item) => ({ name: item.folder, unread: item.unread, total: item.total }))
    )).catch(() => undefined);
    labelsApi.list().then(setLabels).catch(() => undefined);
  }, [router]);

  function toggleTheme() {
    const next = !isDark;
    setIsDark(next);
    document.documentElement.classList.toggle("dark", next);
  }

  return (
    <div className="flex min-h-screen bg-gray-50 dark:bg-gray-950">
      {/* Desktop sidebar */}
      <div className="hidden lg:flex">
        <Sidebar
          role="user"
          folders={folders}
          labels={labels}
          onCompose={() => setComposeOpen(true)}
        />
      </div>

      {/* Mobile sidebar */}
      <MobileSidebar
        open={mobileOpen}
        onClose={() => setMobileOpen(false)}
        role="user"
        folders={folders}
        labels={labels}
        onCompose={() => setComposeOpen(true)}
      />

      <div className="flex-1 flex flex-col min-w-0">
        <Topbar
          email={email}
          onMenuToggle={() => setMobileOpen(true)}
          onThemeToggle={toggleTheme}
          isDark={isDark}
        />
        <main className="flex-1 overflow-auto">{children}</main>
      </div>

      {composeOpen && <ComposeModal onClose={() => setComposeOpen(false)} />}
    </div>
  );
}
