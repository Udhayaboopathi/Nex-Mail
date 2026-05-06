"use client";

import { useState } from "react";
import { Sun, Moon, Bell, LogOut, Search as SearchIcon, Menu } from "lucide-react";
import { useRouter } from "next/navigation";
import { clearToken } from "../../lib/auth";
import { Avatar } from "../ui/Avatar";

interface TopbarProps {
  email: string;
  onMenuToggle?: () => void;
  onSearchChange?: (q: string) => void;
  onThemeToggle?: () => void;
  isDark?: boolean;
}

export function Topbar({ email, onMenuToggle, onSearchChange, onThemeToggle, isDark }: TopbarProps) {
  const router = useRouter();
  const [query, setQuery] = useState("");

  function handleSearch(e: React.FormEvent) {
    e.preventDefault();
    onSearchChange?.(query);
  }

  function handleLogout() {
    clearToken();
    router.push("/login");
  }

  return (
    <header className="h-14 flex items-center gap-3 px-4 bg-white dark:bg-gray-900 border-b border-gray-200 dark:border-gray-800 sticky top-0 z-30">
      {/* Mobile menu toggle */}
      {onMenuToggle && (
        <button
          onClick={onMenuToggle}
          className="lg:hidden p-1.5 rounded-md text-gray-600 dark:text-gray-400 hover:bg-gray-100 dark:hover:bg-gray-800"
          aria-label="Toggle sidebar"
        >
          <Menu className="w-5 h-5" />
        </button>
      )}

      {/* Search */}
      {onSearchChange && (
        <form onSubmit={handleSearch} className="flex-1 max-w-md">
          <div className="relative">
            <SearchIcon className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-400" />
            <input
              value={query}
              onChange={(e) => {
                setQuery(e.target.value);
                if (!e.target.value) onSearchChange("");
              }}
              placeholder="Search mail…"
              className="w-full pl-9 pr-3 py-1.5 text-sm rounded-lg bg-gray-100 dark:bg-gray-800 border border-transparent focus:border-indigo-400 dark:focus:border-indigo-500 focus:outline-none text-gray-900 dark:text-gray-100"
            />
          </div>
        </form>
      )}

      <div className="flex items-center gap-1 ml-auto">
        {/* Notifications placeholder */}
        <button className="p-2 rounded-md text-gray-600 dark:text-gray-400 hover:bg-gray-100 dark:hover:bg-gray-800">
          <Bell className="w-5 h-5" />
        </button>

        {/* Dark mode toggle */}
        {onThemeToggle && (
          <button
            onClick={onThemeToggle}
            className="p-2 rounded-md text-gray-600 dark:text-gray-400 hover:bg-gray-100 dark:hover:bg-gray-800"
            aria-label="Toggle theme"
          >
            {isDark ? <Sun className="w-5 h-5" /> : <Moon className="w-5 h-5" />}
          </button>
        )}

        {/* User avatar */}
        <Avatar email={email} size="sm" className="cursor-default mx-1" />

        {/* Logout */}
        <button
          onClick={handleLogout}
          className="p-2 rounded-md text-gray-600 dark:text-gray-400 hover:bg-gray-100 dark:hover:bg-gray-800"
          aria-label="Logout"
        >
          <LogOut className="w-5 h-5" />
        </button>
      </div>
    </header>
  );
}
