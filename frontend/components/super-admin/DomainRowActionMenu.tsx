"use client";

import { useEffect, useRef } from "react";
import { createPortal } from "react-dom";

export type DomainMenuItem = { label: string; fn: () => void };

type Props = {
  open: boolean;
  anchorRect: DOMRect | null;
  items: DomainMenuItem[];
  onClose: () => void;
};

const MENU_WIDTH = 192;
const MENU_MAX_H = 280;

/** Renders row actions in a portal so scroll/overflow on <main> does not clip the menu. */
export function DomainRowActionMenu({ open, anchorRect, items, onClose }: Props) {
  const menuRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!open) return;
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") onClose();
    };
    document.addEventListener("keydown", onKey);
    let docHandler: ((e: MouseEvent) => void) | null = null;
    const t = window.setTimeout(() => {
      docHandler = (e: MouseEvent) => {
        const el = menuRef.current;
        if (!el?.contains(e.target as Node)) onClose();
      };
      document.addEventListener("mousedown", docHandler);
    }, 0);
    return () => {
      window.clearTimeout(t);
      if (docHandler) document.removeEventListener("mousedown", docHandler);
      document.removeEventListener("keydown", onKey);
    };
  }, [open, onClose]);

  useEffect(() => {
    if (!open) return;
    const onScroll = () => onClose();
    window.addEventListener("scroll", onScroll, true);
    return () => window.removeEventListener("scroll", onScroll, true);
  }, [open, onClose]);

  if (!open || !anchorRect || typeof document === "undefined") return null;

  const approxH = Math.min(items.length * 40 + 8, MENU_MAX_H);
  let top = anchorRect.bottom + 4;
  if (top + approxH > window.innerHeight - 8) {
    top = Math.max(8, anchorRect.top - approxH - 4);
  }
  let left = anchorRect.right - MENU_WIDTH;
  left = Math.max(8, Math.min(left, window.innerWidth - MENU_WIDTH - 8));

  return createPortal(
    <div
      ref={menuRef}
      className="fixed z-[200] w-48 max-h-[min(280px,calc(100vh-16px))] overflow-y-auto rounded-lg border border-gray-200 bg-white py-1 shadow-lg dark:border-gray-700 dark:bg-gray-800"
      style={{ top, left, minWidth: MENU_WIDTH }}
      role="menu"
    >
      {items.map(({ label, fn }) => (
        <button
          key={label}
          type="button"
          role="menuitem"
          onClick={() => {
            fn();
            onClose();
          }}
          className="w-full px-4 py-2 text-left text-sm text-gray-700 hover:bg-gray-50 dark:text-gray-300 dark:hover:bg-gray-700"
        >
          {label}
        </button>
      ))}
    </div>,
    document.body
  );
}
