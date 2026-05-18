"use client";
import { Sparkles, Send, ImageIcon } from "lucide-react";
import { Card } from "@/components/ui/Card";
import { Badge } from "@/components/ui/Badge";
import { Button } from "@/components/ui/Button";
import { Draft, api } from "@/lib/api";
import { useState } from "react";

interface Props {
  draft: Draft;
  enrichmentReady: boolean;
  credentialsConnected: { linkedin: boolean; facebook: boolean };
  onRequestCredentials: (platform: "linkedin" | "facebook") => void;
  onChange: () => void;
}

export function DraftCard({ draft, enrichmentReady, credentialsConnected, onRequestCredentials, onChange }: Props) {
  const [busy, setBusy] = useState<string | null>(null);
  const [imageError, setImageError] = useState<string | null>(null);
  const canEnhance = enrichmentReady && draft.tier === "A" && draft.status === "draft";
  const superseded = draft.status === "superseded";
  const hasImage = Boolean(draft.image_path);

  const push = async (platform: "linkedin" | "facebook") => {
    if (!credentialsConnected[platform]) {
      onRequestCredentials(platform);
      return;
    }
    setBusy(platform);
    try { await api.pushDraft(draft.id, { platform }); onChange(); } finally { setBusy(null); }
  };
  const enhance = async () => {
    setBusy("enhance");
    try { await api.regenerateDraft(draft.id); onChange(); } finally { setBusy(null); }
  };
  const regenerateImage = async () => {
    setBusy("image");
    setImageError(null);
    try {
      await api.regenerateDraftImage(draft.id);
      onChange();
    } catch (e) {
      setImageError(e instanceof Error ? e.message : "Image generation failed");
    } finally {
      setBusy(null);
    }
  };

  return (
    <Card className={`flex flex-col gap-4 hover:-translate-y-0.5 ${superseded ? "opacity-50" : ""}`}>
      {hasImage ? (
        <div className="aspect-[5/4] bg-[var(--color-paper)] overflow-hidden">
          {/* eslint-disable-next-line @next/next/no-img-element */}
          <img src={`/api/image?p=${encodeURIComponent(draft.image_path)}`} alt="" className="w-full h-full object-cover" />
        </div>
      ) : (
        !superseded && draft.status === "draft" && (
          <div className="aspect-[5/4] bg-[var(--color-paper)] border border-dashed border-[var(--color-hairline)] flex flex-col items-center justify-center gap-3 p-4 text-center">
            <ImageIcon className="w-8 h-8 text-[var(--color-ink-muted)]" />
            <p className="text-xs text-[var(--color-ink-muted)]">
              Image generation didn&apos;t complete for this draft.
            </p>
            <Button variant="secondary" size="sm" onClick={regenerateImage} disabled={busy !== null}>
              {busy === "image" ? "Generating…" : "Generate image"}
            </Button>
            {imageError && <p className="text-xs text-[var(--color-danger,red)]">{imageError}</p>}
          </div>
        )
      )}
      <h3 className="font-display text-xl leading-tight">{draft.headline}</h3>
      <p className="text-sm text-[var(--color-ink-muted)]">{draft.body}</p>
      <div className="flex items-center gap-2 flex-wrap">
        <Badge>{draft.platform}</Badge>
        <Badge>{draft.cta}</Badge>
        {draft.status === "pushed" && <Badge tone="positive">pushed</Badge>}
        {superseded && <Badge>superseded</Badge>}
      </div>
      {draft.rationale && <p className="text-xs italic font-display text-[var(--color-ink-muted)] border-t border-[var(--color-hairline)] pt-3">{draft.rationale}</p>}
      {!superseded && draft.status === "draft" && (
        <div className="flex flex-col gap-2 pt-2">
          {canEnhance && (
            <Button variant="secondary" size="sm" onClick={enhance} disabled={busy !== null}>
              <Sparkles className="w-4 h-4" />
              {busy === "enhance" ? "Enhancing…" : "Enhance with market intelligence"}
            </Button>
          )}
          <div className="flex gap-2">
            <Button size="sm" onClick={() => push(draft.platform)} disabled={busy !== null || !hasImage} className="flex-1">
              <Send className="w-4 h-4" />
              {busy === draft.platform
                ? "Pushing…"
                : !hasImage
                  ? "Generate image first"
                  : credentialsConnected[draft.platform]
                    ? `Push to ${draft.platform}`
                    : `Connect ${draft.platform} to push`}
            </Button>
          </div>
        </div>
      )}
    </Card>
  );
}
