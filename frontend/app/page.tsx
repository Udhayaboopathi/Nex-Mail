"use client";

import { useEffect } from "react";
import { useRouter } from "next/navigation";
import { getRole, isAuthenticated } from "../lib/auth";

export default function HomePage() {
  const router = useRouter();

  useEffect(() => {
    if (!isAuthenticated()) {
      router.replace("/login");
      return;
    }
    const role = getRole();
    if (role === "super_admin") router.replace("/super-admin");
    else if (role === "domain_admin") router.replace("/domain-admin");
    else router.replace("/mail/inbox");
  }, [router]);

  return (
    <div className="min-h-screen flex items-center justify-center bg-gray-50 dark:bg-gray-950">
      <div className="w-8 h-8 border-2 border-indigo-600 border-t-transparent rounded-full animate-spin" />
    </div>
  );
}
