"use client";

import { useEffect } from "react";
import { X } from "lucide-react";
import { Sidebar } from "./Sidebar";
import type { FolderInfo, Label } from "../../types";
import type { Role } from "../../types";
import { cn } from "../../lib/utils";

interface MobileSidebarProps {
  open: boolean;
  onClose: () => void;
  role: Role;
  folders?: FolderInfo[];
  labels?: Label[];
  usedMb?: number;
  quotaMb?: number;
  onCompose?: () => void;
}

export function MobileSidebar({
  open,
  onClose,
  role,
  folders,
  labels,
  usedMb,
  quotaMb,
  onCompose,
}: MobileSidebarProps) {
  useEffect(() => {
    if (open) {
      document.body.style.overflow = "hidden";
    } else {
      document.body.style.overflow = "";
    }
    return () => { document.body.style.overflow = ""; };
  }, [open]);

  return (
    <>
      {/* Backdrop */}
      <div
        className={cn(
          "fixed inset-0 z-40 bg-black/50 transition-opacity lg:hidden",
          open ? "opacity-100 pointer-events-auto" : "opacity-0 pointer-events-none"
        )}
        onClick={onClose}
        aria-hidden="true"
      />

      {/* Drawer */}
      <div
        className={cn(
          "fixed inset-y-0 left-0 z-50 flex flex-col bg-white dark:bg-gray-900 shadow-xl transition-transform duration-200 lg:hidden",
          open ? "translate-x-0" : "-translate-x-full"
        )}
        aria-modal="true"
        role="dialog"
      >
        <div className="flex justify-end px-4 py-3 border-b border-gray-200 dark:border-gray-800">
          <button
            onClick={onClose}
            className="p-1.5 rounded-md text-gray-600 dark:text-gray-400 hover:bg-gray-100 dark:hover:bg-gray-800"
            aria-label="Close navigation"
          >
            <X className="w-5 h-5" />
          </button>
        </div>
        <Sidebar
          role={role}
          folders={folders}
          labels={labels}
          usedMb={usedMb}
          quotaMb={quotaMb}
          onCompose={() => { onClose(); onCompose?.(); }}
        />
      </div>
    </>
  );
}
