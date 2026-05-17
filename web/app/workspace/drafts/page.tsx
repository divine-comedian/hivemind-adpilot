"use client";
import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { Chip } from "@/components/ui/Chip";
import { api, WorkspaceState, subscribeWorkspaceEvents } from "@/lib/api";
import { DraftIdeaGenerator } from "@/components/DraftIdeaGenerator";

export default function DraftsPage() {
  const router = useRouter();
  const [ws, setWs] = useState<WorkspaceState | null>(null);
  const [banner, setBanner] = useState<string | null>(null);
  const [hasGeneratedIdeas, setHasGeneratedIdeas] = useState(false);

  const reload = async () => {
    setWs(await api.getWorkspace());
  };

  useEffect(() => { reload(); }, []);

  useEffect(() => {
    if (ws?.last_angle_ideas) setHasGeneratedIdeas(true);
  }, [ws]);

  useEffect(() => {
    const unsub = subscribeWorkspaceEvents((e) => {
      if (e.type === "enrichment_ready") {
        setBanner("Project enrichment is ready — drafts can be enhanced with market intelligence.");
        reload();
      } else if (e.type === "enrichment_failed") {
        setBanner("Project enrichment failed. Drafts will still run in tier A.");
        reload();
      }
    });
    return unsub;
  }, []);

  const enrichmentReady = ws?.hivemind.enrichment_status === "ready";
  return (
    <>
      <header className="flex items-baseline justify-between mb-10">
        <div>
          <h1 className="font-display text-4xl">Drafts</h1>
          <p className="text-[var(--color-ink-muted)] mt-1">{ws?.hivemind.website_url}</p>
        </div>
        <div className="flex items-center gap-3">
          <Chip state={enrichmentReady ? "ready" : "brewing"}>
            Project: {ws?.hivemind.enrichment_status ?? "enriching"}
          </Chip>
        </div>
      </header>

      {banner && (
        <div className="mb-6 p-4 bg-[var(--color-accent-soft)] border border-[var(--color-accent)]/30 rounded-sm flex justify-between">
          <p className="text-sm">{banner}</p>
          <button onClick={() => setBanner(null)} className="text-sm font-medium">Dismiss</button>
        </div>
      )}

      {ws && (
        <DraftIdeaGenerator
          initialIdeas={ws.last_angle_ideas}
          onComplete={() => router.push("/workspace/ads")}
          onIdeasChange={(ideas) => {
            setHasGeneratedIdeas(true);
            setWs((curr) => curr ? { ...curr, last_angle_ideas: ideas } : curr);
          }}
        />
      )}

      {!hasGeneratedIdeas && (
        <p className="text-[var(--color-ink-muted)]">No draft ideas yet. Click <strong>Give me some Ideas</strong> to start.</p>
      )}
    </>
  );
}
