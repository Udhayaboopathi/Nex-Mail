"use client";

import { ButtonHTMLAttributes } from "react";

type Props = ButtonHTMLAttributes<HTMLButtonElement> & {
  busy?: boolean;
};

export default function Button({ busy = false, className = "", children, disabled, ...props }: Props): JSX.Element {
  return (
    <button
      className={`rounded-md bg-indigo-600 px-3 py-2 text-sm font-semibold text-white transition hover:bg-indigo-500 disabled:cursor-not-allowed disabled:bg-slate-400 dark:bg-indigo-500 dark:hover:bg-indigo-400 ${className}`}
      disabled={disabled || busy}
      {...props}
    >
      {busy ? "Working..." : children}
    </button>
  );
}
