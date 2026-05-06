"use client";

import { InputHTMLAttributes, forwardRef } from "react";

type Props = InputHTMLAttributes<HTMLInputElement> & {
  label?: string;
  error?: string;
};

const Input = forwardRef<HTMLInputElement, Props>(function Input({ label, error, className = "", ...props }, ref) {
  return (
    <label className="block space-y-1">
      {label ? <span className="text-sm font-medium text-slate-700 dark:text-slate-200">{label}</span> : null}
      <input
        ref={ref}
        className={`w-full rounded-md border border-slate-300 bg-white px-3 py-2 text-slate-900 outline-none ring-indigo-500 focus:ring-2 dark:border-slate-700 dark:bg-slate-900 dark:text-slate-100 ${className}`}
        {...props}
      />
      {error ? <span className="text-xs text-red-600 dark:text-red-400">{error}</span> : null}
    </label>
  );
});

export default Input;
