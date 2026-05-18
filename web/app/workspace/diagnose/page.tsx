"use client";
import { useEffect, useState } from "react";
import { Card } from "@/components/ui/Card";
import { Badge } from "@/components/ui/Badge";
import { Button } from "@/components/ui/Button";
import { ChainTrace } from "@/components/ChainTrace";
import { API_BASE, ChainStep, api } from "@/lib/api";

interface DiagnoseResult {
  diagnose_id: string;
  summary: string;
  kill_recommendations: { target_id: string; platform: string; reasoning: string; framework_cited: string | null }[];
  replacement_drafts: { draft_id: string; headline: string; body: string; rationale: string }[];
  tier: "A" | "B";
  created_at?: string;
}

export default function DiagnosePage() {
  const [steps, setSteps] = useState<ChainStep[]>([]);
  const [running, setRunning] = useState(false);
  const [result, setResult] = useState<DiagnoseResult | null>(null);
  const [killed, setKilled] = useState<Set<string>>(new Set());

  useEffect(() => {
    api.getLatestDiagnosis().then((latest) => {
      if (latest) setResult(latest);
    }).catch(() => {});
  }, []);

  const run = () => {
    setRunning(true);
    setSteps([]);
    setResult(null);
    const src = new EventSource(`${API_BASE}/diagnose`);
    src.addEventListener("chain_step", (e) => {
      const s = JSON.parse((e as MessageEvent).data);
      setSteps((arr) => [...arr.filter((x) => x.step !== s.step), s]);
    });
    src.addEventListener("result", (e) => {
      setResult(JSON.parse((e as MessageEvent).data));
      setRunning(false);
      src.close();
    });
    src.addEventListener("error", () => {
      setRunning(false);
      src.close();
    });
  };

  const acceptKill = async (target_id: string, platform: string) => {
    try {
      await api.acceptDiagnose({ action: "kill", target_id, platform });
      setKilled((prev) => new Set([...prev, target_id]));
    } catch (e) {
      console.error("Failed to kill", e);
    }
  };

  return (
    <>
      <header className="mb-10 flex items-center justify-between">
        <div>
          <h1 className="font-display text-4xl">Diagnose</h1>
          <p className="text-[var(--color-ink-muted)] mt-1">Strategist reviews recent performance.</p>
        </div>
        <Button onClick={run} disabled={running} size="lg">
          {running ? "Running…" : "Run diagnosis"}
        </Button>
      </header>

      {steps.length > 0 && !result && (
        <Card><ChainTrace steps={steps} /></Card>
      )}

      {result && (
        <div className="space-y-10">
          <Card className="space-y-3">
            <p className="font-mono text-xs uppercase tracking-widest text-[var(--color-ink-muted)]">Diagnosis</p>
            <p className="font-display text-xl leading-relaxed whitespace-pre-line">{result.summary}</p>
          </Card>

          {result.kill_recommendations.length > 0 && (
            <section>
              <h2 className="font-display text-2xl mb-4">Pause these</h2>
              <div className="space-y-3">
                {result.kill_recommendations.map((k) => {
                  const isKilled = killed.has(k.target_id);
                  return (
                    <Card key={k.target_id} className="flex items-start gap-4">
                      <div className="flex-1">
                        <p className="font-mono text-xs text-[var(--color-ink-muted)]">{k.target_id}</p>
                        <p className="mt-2">{k.reasoning}</p>
                        {k.framework_cited && <Badge tone="highlight" className="mt-2">{k.framework_cited}</Badge>}
                      </div>
                      <Button
                        variant={isKilled ? "secondary" : "danger"}
                        onClick={() => acceptKill(k.target_id, k.platform)}
                        disabled={isKilled}
                      >
                        {isKilled ? "Paused ✓" : "Approve pause"}
                      </Button>
                    </Card>
                  );
                })}
              </div>
            </section>
          )}

          {result.replacement_drafts.length > 0 && (
            <section>
              <h2 className="font-display text-2xl mb-4">Replacement angles</h2>
              <p className="text-sm text-[var(--color-ink-muted)] mb-4">Already in your drafts — review and push when ready.</p>
              <div className="grid grid-cols-2 gap-4">
                {result.replacement_drafts.map((r) => (
                  <Card key={r.draft_id}>
                    <h3 className="font-display text-xl mb-2">{r.headline}</h3>
                    <p className="text-sm text-[var(--color-ink-muted)] mb-3">{r.body}</p>
                    <p className="text-xs italic font-display border-t border-[var(--color-hairline)] pt-3">{r.rationale}</p>
                  </Card>
                ))}
              </div>
            </section>
          )}
        </div>
      )}
    </>
  );
}
