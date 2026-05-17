"use client";

import { useEffect, useState } from "react";
import { Chip } from "@/components/ui/Chip";
import { ProjectInfoForm } from "@/components/ProjectInfoForm";
import { WorkspaceState, api } from "@/lib/api";

export default function ProjectPage() {
  const [workspace, setWorkspace] = useState<WorkspaceState | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    api.getWorkspace().then(setWorkspace).catch((e) => {
      setError(e instanceof Error ? e.message : "Could not load project");
    });
  }, []);

  return (
    <>
      <header className="flex items-baseline justify-between mb-10">
        <div>
          <h1 className="font-display text-4xl">Project Info</h1>
          <p className="text-[var(--color-ink-muted)] mt-1">{workspace?.hivemind.website_url}</p>
        </div>
        <Chip state={workspace?.hivemind.enrichment_status === "ready" ? "ready" : "brewing"}>
          Project: {workspace?.hivemind.enrichment_status ?? "loading"}
        </Chip>
      </header>

      {error && <p className="text-sm text-[var(--color-negative)]">{error}</p>}
      {workspace && <ProjectInfoForm workspace={workspace} onChange={setWorkspace} />}
    </>
  );
}
