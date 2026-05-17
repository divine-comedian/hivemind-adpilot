"use client";

import { useEffect, useMemo, useState } from "react";
import Link from "next/link";
import { AdOperationsCard } from "@/components/AdOperationsCard";
import { CredentialsPanel } from "@/components/CredentialsPanel";
import { Button } from "@/components/ui/Button";
import { Draft, WorkspaceState, api } from "@/lib/api";

export default function AdsPage() {
  const [ws, setWs] = useState<WorkspaceState | null>(null);
  const [drafts, setDrafts] = useState<Draft[]>([]);
  const [credentialsPlatform, setCredentialsPlatform] = useState<"linkedin" | "facebook" | null>(null);
  const [loading, setLoading] = useState(true);

  const reload = async () => {
    setLoading(true);
    const [workspace, nextDrafts] = await Promise.all([api.getWorkspace(), api.listDrafts()]);
    setWs(workspace);
    setDrafts(nextDrafts);
    setLoading(false);
  };

  useEffect(() => { reload(); }, []);

  const activeAds = useMemo(
    () => drafts
      .filter((draft) => draft.status !== "discarded" && draft.status !== "superseded")
      .sort((a, b) => new Date(b.created_at).getTime() - new Date(a.created_at).getTime()),
    [drafts],
  );

  const grouped = {
    facebook: activeAds.filter((draft) => draft.platform === "facebook"),
    linkedin: activeAds.filter((draft) => draft.platform === "linkedin"),
  };

  const credentialsConnected = {
    linkedin: !!ws?.platforms.linkedin,
    facebook: !!ws?.platforms.facebook,
  };

  if (loading) return <p>Loading...</p>;

  return (
    <>
      <header className="flex items-start justify-between gap-6 mb-10">
        <div>
          <h1 className="font-display text-4xl">Ads</h1>
          <p className="text-[var(--color-ink-muted)] mt-1">
            Generated ad inventory, grouped by platform and sorted by newest first.
          </p>
        </div>
        <Link href="/workspace/drafts">
          <Button variant="secondary">Generate more</Button>
        </Link>
      </header>

      {activeAds.length === 0 && (
        <div className="border border-[var(--color-hairline)] bg-[var(--color-surface)] p-6 rounded-sm">
          <p className="text-sm text-[var(--color-ink-muted)]">No generated ads yet.</p>
          <Link href="/workspace/drafts" className="inline-block mt-4">
            <Button>Start from Drafts</Button>
          </Link>
        </div>
      )}

      {(["facebook", "linkedin"] as const).map((platform) => (
        grouped[platform].length > 0 && (
          <section key={platform} className="mb-12">
            <div className="flex items-baseline justify-between mb-4">
              <h2 className="font-display text-2xl capitalize">{platform}</h2>
              <p className="text-sm text-[var(--color-ink-muted)]">{grouped[platform].length} ads</p>
            </div>
            <div className="grid grid-cols-1 xl:grid-cols-2 2xl:grid-cols-3 gap-5">
              {grouped[platform].map((draft) => (
                <AdOperationsCard
                  key={draft.id}
                  draft={draft}
                  credentialsConnected={credentialsConnected}
                  onRequestCredentials={setCredentialsPlatform}
                  onChange={reload}
                />
              ))}
            </div>
          </section>
        )
      ))}

      {credentialsPlatform && (
        <CredentialsPanel
          platform={credentialsPlatform}
          onClose={() => setCredentialsPlatform(null)}
          onSaved={(updated) => {
            setWs(updated);
            setCredentialsPlatform(null);
          }}
        />
      )}
    </>
  );
}
