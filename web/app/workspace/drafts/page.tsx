"use client";
import { useEffect, useState } from "react";
import { Chip } from "@/components/ui/Chip";
import { api, Draft, WorkspaceState, subscribeWorkspaceEvents } from "@/lib/api";
import { DraftCard } from "@/components/DraftCard";
import { GeneratePanel } from "@/components/GeneratePanel";
import { RefinePanel } from "@/components/RefinePanel";

export default function DraftsPage() {
  const [ws, setWs] = useState<WorkspaceState | null>(null);
  const [drafts, setDrafts] = useState<Draft[]>([]);
  const [banner, setBanner] = useState<string | null>(null);

  const reload = async () => {
    setWs(await api.getWorkspace());
    setDrafts(await api.listDrafts());
  };

  useEffect(() => { reload(); }, []);

  useEffect(() => {
    const unsub = subscribeWorkspaceEvents((e) => {
      if (e.type === "intelligence_ready") {
        setBanner(`Market intelligence is ready — drafts can be enhanced.`);
        reload();
      }
    });
    return unsub;
  }, []);

  const intelligenceReady = !!ws && Object.values(ws.hivemind.reports || {}).some(
    (r) => ["completed", "completed_partial", "completed_healed"].includes(r.status),
  );

  return (
    <>
      <header className="flex items-baseline justify-between mb-10">
        <div>
          <h1 className="font-display text-4xl">Drafts</h1>
          <p className="text-[var(--color-ink-muted)] mt-1">{ws?.business.name}</p>
        </div>
        <div className="flex items-center gap-3">
          <Chip state={intelligenceReady ? "ready" : "brewing"}>
            Market intelligence: {intelligenceReady ? "ready" : "brewing"}
          </Chip>
          <GeneratePanel onComplete={reload} />
        </div>
      </header>

      {banner && (
        <div className="mb-6 p-4 bg-[var(--color-accent-soft)] border border-[var(--color-accent)]/30 rounded-sm flex justify-between">
          <p className="text-sm">{banner}</p>
          <button onClick={() => setBanner(null)} className="text-sm font-medium">Dismiss</button>
        </div>
      )}

      {ws && <RefinePanel initial={ws.business.focus_notes} onSave={(v) => api.patchFocus(v).catch(() => {})} />}

      <div className="grid grid-cols-2 lg:grid-cols-3 gap-6">
        {drafts.map((d) => <DraftCard key={d.id} draft={d} intelligenceReady={intelligenceReady} onChange={reload} />)}
        {drafts.length === 0 && (
          <p className="text-[var(--color-ink-muted)] col-span-full">No drafts yet. Click <strong>Generate drafts</strong> to start.</p>
        )}
      </div>
    </>
  );
}
