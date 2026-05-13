"use client";
import { useState } from "react";
import { Button } from "@/components/ui/Button";
import { Textarea } from "@/components/ui/Textarea";
import { ChainTrace } from "./ChainTrace";
import { streamGenerate, ChainStep, Draft } from "@/lib/api";

export function GeneratePanel({ onComplete }: { onComplete: (drafts: Draft[]) => void }) {
  const [open, setOpen] = useState(false);
  const [platforms, setPlatforms] = useState<("linkedin" | "facebook")[]>(["linkedin", "facebook"]);
  const [count, setCount] = useState(5);
  const [focus, setFocus] = useState("");
  const [steps, setSteps] = useState<ChainStep[]>([]);
  const [running, setRunning] = useState(false);

  const submit = () => {
    setRunning(true); setSteps([]);
    streamGenerate(
      { platforms, count, focus_note: focus },
      (step) => setSteps((s) => [...s.filter((x) => x.step !== step.step), step]),
      (result) => { setRunning(false); onComplete(result.drafts); setOpen(false); },
    );
  };

  return (
    <>
      <Button onClick={() => setOpen(true)}>Generate drafts</Button>
      {open && (
        <div className="fixed inset-0 bg-black/30 flex justify-end z-50" onClick={() => !running && setOpen(false)}>
          <div className="w-[440px] h-full bg-[var(--color-surface)] p-8 overflow-y-auto" onClick={(e) => e.stopPropagation()}>
            <h2 className="font-display text-2xl mb-6">Generate</h2>
            <div className="space-y-5">
              <label className="block">
                <span className="text-sm font-medium">Platforms</span>
                <div className="flex gap-2 mt-2">
                  {(["linkedin", "facebook"] as const).map((p) => (
                    <button key={p} type="button" onClick={() => setPlatforms((curr) => curr.includes(p) ? curr.filter((x) => x !== p) : [...curr, p])}
                      className={`px-3 h-9 text-sm border rounded-sm ${platforms.includes(p) ? "bg-[var(--color-ink)] text-[var(--color-paper)] border-[var(--color-ink)]" : "border-[var(--color-hairline)]"}`}>
                      {p}
                    </button>
                  ))}
                </div>
              </label>
              <label className="block">
                <span className="text-sm font-medium">Angles ({count})</span>
                <input type="range" min={3} max={8} value={count} onChange={(e) => setCount(parseInt(e.target.value))} className="w-full mt-2" />
              </label>
              <label className="block">
                <span className="text-sm font-medium">Focus (optional)</span>
                <Textarea value={focus} onChange={(e) => setFocus(e.target.value)} placeholder="e.g. enterprise buyers, competitor X just launched feature Y" />
              </label>
              {steps.length > 0 && <ChainTrace steps={steps} />}
              <Button onClick={submit} disabled={running} className="w-full" size="lg">
                {running ? "Running Strategist Chain…" : "Run"}
              </Button>
            </div>
          </div>
        </div>
      )}
    </>
  );
}
