import { cn } from "@/lib/cn";
import { HTMLAttributes } from "react";

type State = "brewing" | "ready" | "neutral";
const states: Record<State, string> = {
  brewing: "bg-[var(--color-highlight)]/20 text-[var(--color-ink)] border-[var(--color-highlight)]",
  ready: "bg-[var(--color-positive)]/15 text-[var(--color-positive)] border-[var(--color-positive)]/40",
  neutral: "bg-[var(--color-surface)] text-[var(--color-ink-muted)] border-[var(--color-hairline)]",
};

export function Chip({ state = "neutral", className, children, ...p }: HTMLAttributes<HTMLSpanElement> & { state?: State }) {
  return (
    <span className={cn("inline-flex items-center gap-2 h-7 px-3 text-xs border rounded-full font-medium", states[state], className)} {...p}>
      {state === "brewing" && <span className="w-1.5 h-1.5 bg-current rounded-full animate-pulse" />}
      {children}
    </span>
  );
}
