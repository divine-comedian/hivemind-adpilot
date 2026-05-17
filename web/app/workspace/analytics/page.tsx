"use client";
import { Suspense, useEffect, useState } from "react";
import Link from "next/link";
import { useSearchParams } from "next/navigation";
import { MetricCard } from "@/components/MetricCard";
import { AdsTable } from "@/components/AdsTable";
import { Button } from "@/components/ui/Button";
import { api } from "@/lib/api";

interface AnalyticsRow {
  platform: string;
  ad_id?: string;
  ad_name?: string;
  impressions?: number;
  clicks?: number;
  spend?: number;
  ctr?: number;
  cpm?: number;
  conversions?: number;
  status?: string;
  error?: string;
}

interface AnalyticsResponse {
  rows: AnalyticsRow[];
  summary: {
    total_spend?: number;
    total_impressions?: number;
    total_clicks?: number;
    total_conversions?: number;
    avg_ctr?: number;
    avg_cpm?: number;
  };
}

function AnalyticsPageInner() {
  const searchParams = useSearchParams();
  const selectedAd = searchParams.get("ad");
  const selectedPlatform = searchParams.get("platform");
  const [data, setData] = useState<AnalyticsResponse | null>(null);

  useEffect(() => {
    api.getAnalytics("30d").then((d) => setData(d as AnalyticsResponse)).catch(() => setData({ rows: [], summary: {} }));
  }, []);

  if (!data) return <p>Loading…</p>;

  const s = data.summary;
  const errors = data.rows.filter((r) => r.error);
  const valid = data.rows.filter((r) => !r.error);
  const visibleRows = selectedAd
    ? valid.filter((r) => {
        const platformMatches = !selectedPlatform || r.platform === selectedPlatform;
        const adMatches = r.ad_id === selectedAd || r.ad_name === selectedAd;
        return platformMatches && adMatches;
      })
    : valid;

  return (
    <>
      <header className="mb-10">
        <h1 className="font-display text-4xl">Analytics</h1>
        <p className="text-[var(--color-ink-muted)] mt-1">Last 30 days, normalized across LinkedIn + Facebook.</p>
      </header>

      <div className="grid grid-cols-4 gap-4 mb-10">
        <MetricCard label="Spend" value={`$${(s.total_spend ?? 0).toFixed(2)}`} />
        <MetricCard label="Impressions" value={(s.total_impressions ?? 0).toLocaleString()} />
        <MetricCard label="CTR" value={`${((s.avg_ctr ?? 0) * 100).toFixed(2)}%`} />
        <MetricCard label="Conversions" value={(s.total_conversions ?? 0).toLocaleString()} />
      </div>

      {errors.length > 0 && (
        <div className="mb-6 p-4 bg-[var(--color-negative)]/10 border border-[var(--color-negative)]/30 rounded-sm">
          <p className="text-sm font-medium mb-1">Some sources failed:</p>
          <ul className="text-xs text-[var(--color-ink-muted)]">
            {errors.map((e, i) => <li key={i}>{e.platform}: {e.error}</li>)}
          </ul>
        </div>
      )}

      {selectedAd && (
        <div className="mb-6 p-4 bg-[var(--color-accent-soft)] border border-[var(--color-accent)]/30 rounded-sm flex items-center justify-between gap-4">
          <p className="text-sm">
            Showing analytics for <span className="font-mono">{selectedAd}</span>
            {selectedPlatform ? ` on ${selectedPlatform}` : ""}.
          </p>
          <Link href="/workspace/analytics" className="text-sm font-medium hover:text-[var(--color-accent)]">
            Show all ads
          </Link>
        </div>
      )}

      <section className="mb-10">
        <h2 className="font-display text-2xl mb-4">Per-ad performance</h2>
        <AdsTable rows={visibleRows as never} />
      </section>

      <div className="flex justify-end">
        <Link href="/workspace/diagnose">
          <Button size="lg">Diagnose with Strategist →</Button>
        </Link>
      </div>
    </>
  );
}

export default function AnalyticsPage() {
  return (
    <Suspense fallback={<p>Loading...</p>}>
      <AnalyticsPageInner />
    </Suspense>
  );
}
