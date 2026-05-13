import { cn } from "@/lib/cn";
import { TextareaHTMLAttributes, forwardRef } from "react";

export const Textarea = forwardRef<HTMLTextAreaElement, TextareaHTMLAttributes<HTMLTextAreaElement>>(
  ({ className, ...props }, ref) => (
    <textarea
      ref={ref}
      className={cn(
        "w-full border border-[var(--color-hairline)] bg-[var(--color-surface)] px-3 py-2 text-[15px] text-[var(--color-ink)] placeholder:text-[var(--color-ink-muted)] rounded-sm min-h-[120px]",
        className,
      )}
      {...props}
    />
  ),
);
Textarea.displayName = "Textarea";
