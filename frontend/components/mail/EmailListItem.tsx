import { Star, Paperclip } from "lucide-react";
import { cn, formatDate, truncate } from "../../lib/utils";
import { Avatar } from "../ui/Avatar";
import type { EmailHeader } from "../../types";

interface EmailListItemProps {
  email: EmailHeader;
  selected?: boolean;
  onClick: () => void;
  onStar: () => void;
  onSelect: (checked: boolean) => void;
  isChecked?: boolean;
}

export function EmailListItem({
  email,
  selected = false,
  onClick,
  onStar,
  onSelect,
  isChecked = false,
}: EmailListItemProps) {
  return (
    <div
      onClick={onClick}
      className={cn(
        "flex items-start gap-3 px-4 py-3 cursor-pointer border-b border-gray-100 dark:border-gray-800 transition-colors select-none group",
        selected
          ? "bg-indigo-50 dark:bg-indigo-900/20"
          : email.is_read
          ? "bg-white dark:bg-gray-900 hover:bg-gray-50 dark:hover:bg-gray-800/50"
          : "bg-blue-50/30 dark:bg-gray-800/60 hover:bg-blue-50/60 dark:hover:bg-gray-800"
      )}
    >
      {/* Checkbox */}
      <input
        type="checkbox"
        checked={isChecked}
        onChange={(e) => { e.stopPropagation(); onSelect(e.target.checked); }}
        onClick={(e) => e.stopPropagation()}
        className="mt-1 accent-indigo-600 shrink-0"
      />

      {/* Avatar */}
      <Avatar email={email.from} size="sm" className="mt-0.5 shrink-0" />

      {/* Content */}
      <div className="flex-1 min-w-0">
        <div className="flex items-center justify-between gap-2">
          <span className={cn("text-sm truncate", !email.is_read && "font-semibold text-gray-900 dark:text-white")}>
            {email.from}
          </span>
          <span className="text-xs text-gray-400 dark:text-gray-500 shrink-0">
            {formatDate(email.date)}
          </span>
        </div>
        <p className={cn("text-sm truncate", !email.is_read ? "font-medium text-gray-800 dark:text-gray-100" : "text-gray-600 dark:text-gray-400")}>
          {email.subject || "(no subject)"}
        </p>
        <p className="text-xs text-gray-400 dark:text-gray-500 truncate">
          {truncate(email.preview, 80)}
        </p>

        {/* Labels */}
        {(email.labels ?? []).length > 0 && (
          <div className="flex flex-wrap gap-1 mt-1">
            {(email.labels ?? []).map((l) => (
              <span
                key={l.id}
                className="px-1.5 py-0.5 rounded text-xs text-white"
                style={{ background: l.color }}
              >
                {l.name}
              </span>
            ))}
          </div>
        )}
      </div>

      {/* Actions */}
      <div className="flex flex-col items-end gap-1 shrink-0">
        <button
          onClick={(e) => { e.stopPropagation(); onStar(); }}
          className={cn(
            "p-0.5 transition-colors",
            email.is_flagged
              ? "text-yellow-400"
              : "text-gray-300 dark:text-gray-600 opacity-0 group-hover:opacity-100 hover:text-yellow-400"
          )}
          aria-label={email.is_flagged ? "Unstar" : "Star"}
        >
          <Star className="w-4 h-4" fill={email.is_flagged ? "currentColor" : "none"} />
        </button>
        {email.has_attachments && (
          <Paperclip className="w-3.5 h-3.5 text-gray-400" />
        )}
      </div>
    </div>
  );
}
