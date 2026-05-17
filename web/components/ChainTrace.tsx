"use client";
import { Check, Loader2 } from "lucide-react";
import { ChainStep } from "@/lib/api";

const STEPS = [
  { id: "strategist", label: "Strategist (genius-strategist)" },
  { id: "ghostwriter", label: "Ghostwriter" },
];

export function ChainTrace({ steps }: { steps: ChainStep[] }) {
  const stateById = new Map(steps.map((s) => [s.step, s]));
  return (
    <ol className="space-y-3">
      {STEPS.map((s) => {
        const state = stateById.get(s.id);
        const status = state?.status ?? "pending";
        return (
          <li key={s.id} className="flex items-center gap-3 text-sm">
            <span className="w-6 h-6 flex items-center justify-center">
              {status === "complete" && <Check className="w-4 h-4 text-[var(--color-positive)]" />}
              {status === "running" && <Loader2 className="w-4 h-4 animate-spin" />}
              {status === "pending" && <span className="w-2 h-2 rounded-full bg-[var(--color-hairline)]" />}
            </span>
            <span className={status === "pending" ? "text-[var(--color-ink-muted)]" : "text-[var(--color-ink)]"}>{s.label}</span>
            {state?.payload && status === "complete" && (
              <span className="font-mono text-xs text-[var(--color-ink-muted)] ml-auto">
                {JSON.stringify(state.payload).slice(0, 60)}
              </span>
            )}
          </li>
        );
      })}
    </ol>
  );
}
