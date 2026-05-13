import { Card } from "@/components/ui/Card";

export function MetricCard({ label, value, sub }: { label: string; value: string; sub?: string }) {
  return (
    <Card>
      <p className="text-xs uppercase tracking-widest text-[var(--color-ink-muted)] font-mono mb-3">{label}</p>
      <p className="font-display text-4xl font-mono tabular-nums">{value}</p>
      {sub && <p className="text-xs text-[var(--color-ink-muted)] mt-2">{sub}</p>}
    </Card>
  );
}
