"use client";

import { useEffect, useState, type ReactNode } from "react";
import { useRouter } from "next/navigation";
import { Sidebar } from "../../components/layout/Sidebar";
import { Topbar } from "../../components/layout/Topbar";
import { MobileSidebar } from "../../components/layout/MobileSidebar";
import { getToken, getRole } from "../../lib/auth";

export default function DomainAdminLayout({ children }: { children: ReactNode }) {
  const router = useRouter();
  const [mobileOpen, setMobileOpen] = useState(false);
  const email = typeof window !== "undefined" ? localStorage.getItem("nex_email") ?? "" : "";

  useEffect(() => {
    if (!getToken() || getRole() !== "domain_admin") router.replace("/login");
  }, [router]);

  return (
    <div className="flex min-h-screen bg-gray-50 dark:bg-gray-950">
      <div className="hidden lg:flex"><Sidebar role="domain_admin" /></div>
      <MobileSidebar open={mobileOpen} onClose={() => setMobileOpen(false)} role="domain_admin" />
      <div className="flex-1 flex flex-col min-w-0">
        <Topbar email={email} onMenuToggle={() => setMobileOpen(true)} />
        <main className="flex-1 p-6 overflow-auto">{children}</main>
      </div>
    </div>
  );
}
