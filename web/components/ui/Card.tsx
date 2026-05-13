import { cn } from "@/lib/cn";
import { HTMLAttributes, forwardRef } from "react";

export const Card = forwardRef<HTMLDivElement, HTMLAttributes<HTMLDivElement>>(
  ({ className, ...props }, ref) => (
    <div
      ref={ref}
      className={cn(
        "bg-[var(--color-surface)] border border-[var(--color-hairline)] rounded-sm p-6 transition-transform duration-180",
        className,
      )}
      {...props}
    />
  ),
);
Card.displayName = "Card";
