import { cn } from "../../lib/utils";

interface ProgressBarProps {
  value: number; // 0–100
  max?: number;
  label?: string;
  showPercent?: boolean;
  colorClass?: string;
  className?: string;
}

export function ProgressBar({
  value,
  max = 100,
  label,
  showPercent = false,
  colorClass,
  className,
}: ProgressBarProps) {
  const pct = Math.min(100, Math.round((value / max) * 100));
  const color = colorClass ?? (pct >= 90 ? "bg-red-500" : pct >= 70 ? "bg-yellow-500" : "bg-indigo-500");

  return (
    <div className={cn("w-full", className)}>
      {(label || showPercent) && (
        <div className="flex justify-between text-xs mb-1 text-gray-600 dark:text-gray-400">
          {label && <span>{label}</span>}
          {showPercent && <span>{pct}%</span>}
        </div>
      )}
      <div className="w-full h-2 rounded-full bg-gray-200 dark:bg-gray-700 overflow-hidden">
        <div
          className={cn("h-full rounded-full transition-all duration-300", color)}
          style={{ width: `${pct}%` }}
          role="progressbar"
          aria-valuenow={pct}
          aria-valuemin={0}
          aria-valuemax={100}
        />
      </div>
    </div>
  );
}
