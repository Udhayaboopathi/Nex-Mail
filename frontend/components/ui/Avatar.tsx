import { Mail } from "lucide-react";
import { cn, colorFromString } from "../../lib/utils";

interface AvatarProps {
  email: string;
  name?: string;
  size?: "sm" | "md" | "lg";
  className?: string;
}

const sizeMap = {
  sm: "w-7 h-7 text-xs",
  md: "w-9 h-9 text-sm",
  lg: "w-12 h-12 text-base",
};

export function Avatar({ email, name, size = "md", className }: AvatarProps) {
  const label = name ?? email;
  const bg = colorFromString(email);
  const iconSize = size === "sm" ? "w-3.5 h-3.5" : size === "md" ? "w-4 h-4" : "w-5 h-5";

  return (
    <span
      className={cn(
        "inline-flex items-center justify-center rounded-full font-semibold text-white shrink-0 select-none",
        bg,
        sizeMap[size],
        className
      )}
      title={label}
      aria-label={label}
    >
      <Mail className={iconSize} />
    </span>
  );
}
