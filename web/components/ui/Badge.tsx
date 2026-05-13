import { cn } from "@/lib/cn";
import { HTMLAttributes } from "react";

type Tone = "neutral" | "positive" | "negative" | "highlight";
const tones: Record<Tone, string> = {
  neutral: "bg-[var(--color-hairline)] text-[var(--color-ink)]",
  positive: "bg-[var(--color-positive)]/15 text-[var(--color-positive)]",
  negative: "bg-[var(--color-negative)]/15 text-[var(--color-negative)]",
  highlight: "bg-[var(--color-highlight)]/25 text-[var(--color-ink)]",
};

export function Badge({ tone = "neutral", className, ...p }: HTMLAttributes<HTMLSpanElement> & { tone?: Tone }) {
  return <span className={cn("inline-flex items-center px-2 h-6 text-xs uppercase tracking-wide rounded-sm font-medium", tones[tone], className)} {...p} />;
}
