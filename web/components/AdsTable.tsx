"use client";
import { useState, useMemo } from "react";
import { Badge } from "@/components/ui/Badge";

interface Row {
  platform: string;
  ad_id: string;
  ad_name: string;
  impressions: number;
  clicks: number;
  spend: number;
  ctr: number;
  cpm: number;
  conversions: number;
  status: string;
}

export function AdsTable({ rows }: { rows: Row[] }) {
  const [sortKey, setSortKey] = useState<keyof Row>("spend");
  const sorted = useMemo(
    () => [...rows].sort((a, b) => (b[sortKey] as number) - (a[sortKey] as number)),
    [rows, sortKey],
  );
  const ctrValues = rows.map((r) => r.ctr).sort((a, b) => a - b);
  const lowDecile = ctrValues[Math.floor(ctrValues.length * 0.1)] || 0;
  const highDecile = ctrValues[Math.floor(ctrValues.length * 0.9)] || Infinity;

  const headers: [string, keyof Row][] = [
    ["Ad", "ad_name"],
    ["Platform", "platform"],
    ["Impressions", "impressions"],
    ["Clicks", "clicks"],
    ["CTR", "ctr"],
    ["Spend", "spend"],
    ["CPM", "cpm"],
    ["Conversions", "conversions"],
  ];

  return (
    <div className="overflow-x-auto border border-[var(--color-hairline)] rounded-sm">
      <table className="w-full text-sm">
        <thead className="bg-[var(--color-paper)]">
          <tr>
            {headers.map(([label, key]) => (
              <th
                key={label}
                className="text-left p-3 font-medium cursor-pointer hover:text-[var(--color-accent)]"
                onClick={() => setSortKey(key)}
              >
                {label}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {sorted.map((r) => (
            <tr
              key={`${r.platform}-${r.ad_id}`}
              className={`border-t border-[var(--color-hairline)] ${
                r.ctr >= highDecile
                  ? "bg-[var(--color-positive)]/5"
                  : r.ctr <= lowDecile && r.spend > 5
                  ? "bg-[var(--color-negative)]/5"
                  : ""
              }`}
            >
              <td className="p-3 max-w-xs truncate">{r.ad_name || r.ad_id}</td>
              <td className="p-3"><Badge>{r.platform}</Badge></td>
              <td className="p-3 font-mono tabular-nums">{r.impressions.toLocaleString()}</td>
              <td className="p-3 font-mono tabular-nums">{r.clicks.toLocaleString()}</td>
              <td className="p-3 font-mono tabular-nums">{(r.ctr * 100).toFixed(2)}%</td>
              <td className="p-3 font-mono tabular-nums">${r.spend.toFixed(2)}</td>
              <td className="p-3 font-mono tabular-nums">${r.cpm.toFixed(2)}</td>
              <td className="p-3 font-mono tabular-nums">{r.conversions}</td>
            </tr>
          ))}
          {sorted.length === 0 && (
            <tr>
              <td colSpan={headers.length} className="p-6 text-center text-[var(--color-ink-muted)]">
                No ad performance data yet for this window.
              </td>
            </tr>
          )}
        </tbody>
      </table>
    </div>
  );
}
