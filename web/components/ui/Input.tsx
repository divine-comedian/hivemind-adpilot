import { cn } from "@/lib/cn";
import { InputHTMLAttributes, forwardRef } from "react";

export const Input = forwardRef<HTMLInputElement, InputHTMLAttributes<HTMLInputElement>>(
  ({ className, ...props }, ref) => (
    <input
      ref={ref}
      className={cn(
        "h-10 w-full border border-[var(--color-hairline)] bg-[var(--color-surface)] px-3 text-[15px] text-[var(--color-ink)] placeholder:text-[var(--color-ink-muted)] rounded-sm",
        className,
      )}
      {...props}
    />
  ),
);
Input.displayName = "Input";
