"use client";

import { useState, useRef } from "react";
import { Search, X } from "lucide-react";
import { cn } from "../../lib/utils";

interface SearchBarProps {
  value: string;
  onChange: (q: string) => void;
  onSubmit?: (q: string) => void;
  placeholder?: string;
  className?: string;
}

export function SearchBar({ value, onChange, onSubmit, placeholder = "Search…", className }: SearchBarProps) {
  const [focused, setFocused] = useState(false);
  const inputRef = useRef<HTMLInputElement>(null);

  return (
    <form
      onSubmit={(e) => { e.preventDefault(); onSubmit?.(value); }}
      className={cn("relative flex items-center", className)}
    >
      <Search className="absolute left-3 w-4 h-4 text-gray-400 pointer-events-none" />
      <input
        ref={inputRef}
        value={value}
        onChange={(e) => onChange(e.target.value)}
        onFocus={() => setFocused(true)}
        onBlur={() => setFocused(false)}
        placeholder={placeholder}
        className={cn(
          "w-full pl-9 pr-8 py-1.5 text-sm rounded-lg bg-gray-100 dark:bg-gray-800 border",
          "focus:outline-none focus:ring-2 focus:ring-indigo-400 dark:focus:ring-indigo-500",
          focused ? "border-indigo-300 dark:border-indigo-600" : "border-transparent",
          "text-gray-900 dark:text-gray-100 placeholder-gray-400 dark:placeholder-gray-500"
        )}
      />
      {value && (
        <button
          type="button"
          onClick={() => { onChange(""); inputRef.current?.focus(); }}
          className="absolute right-2 p-0.5 text-gray-400 hover:text-gray-600 dark:hover:text-gray-200"
          aria-label="Clear search"
        >
          <X className="w-3.5 h-3.5" />
        </button>
      )}
    </form>
  );
}
