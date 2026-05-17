"use client";

import Link from "next/link";
import { BarChart3, ExternalLink, Pencil, Send, Trash2 } from "lucide-react";
import { useState } from "react";
import { Badge } from "@/components/ui/Badge";
import { Button } from "@/components/ui/Button";
import { Card } from "@/components/ui/Card";
import { Textarea } from "@/components/ui/Textarea";
import { Draft, api } from "@/lib/api";

interface Props {
  draft: Draft;
  credentialsConnected: { linkedin: boolean; facebook: boolean };
  onRequestCredentials: (platform: "linkedin" | "facebook") => void;
  onChange: () => void;
}

function formatDate(value?: string | null) {
  if (!value) return "Not published";
  return new Intl.DateTimeFormat(undefined, { month: "short", day: "numeric", year: "numeric" }).format(new Date(value));
}

function analyticsTarget(draft: Draft) {
  const external = draft.external_urn?.startsWith("fb:") ? draft.external_urn.slice(3) : draft.external_urn;
  return `/workspace/analytics?ad=${encodeURIComponent(external || draft.id)}&platform=${draft.platform}`;
}

export function AdOperationsCard({ draft, credentialsConnected, onRequestCredentials, onChange }: Props) {
  const [busy, setBusy] = useState<string | null>(null);
  const [refineOpen, setRefineOpen] = useState(false);
  const [guidance, setGuidance] = useState("");
  const [error, setError] = useState<string | null>(null);
  const isPublished = draft.status === "pushed" || !!draft.published_at;
  const canPublish = !isPublished && draft.status === "draft";

  const publish = async () => {
    if (!credentialsConnected[draft.platform]) {
      onRequestCredentials(draft.platform);
      return;
    }
    setBusy("publish");
    setError(null);
    try {
      await api.pushDraft(draft.id, { platform: draft.platform });
      onChange();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Could not publish ad");
    } finally {
      setBusy(null);
    }
  };

  const refine = async () => {
    const text = guidance.trim();
    if (!text) return;
    setBusy("refine");
    setError(null);
    try {
      await api.refineDraft(draft.id, text);
      setGuidance("");
      setRefineOpen(false);
      onChange();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Could not refine ad copy");
    } finally {
      setBusy(null);
    }
  };

  const remove = async () => {
    if (!window.confirm("Delete this ad from the workspace?")) return;
    setBusy("delete");
    setError(null);
    try {
      await api.deleteDraft(draft.id);
      onChange();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Could not delete ad");
    } finally {
      setBusy(null);
    }
  };

  return (
    <Card className="flex flex-col gap-5">
      {draft.image_path && (
        <div className="aspect-[5/4] bg-[var(--color-paper)] overflow-hidden">
          {/* eslint-disable-next-line @next/next/no-img-element */}
          <img src={`/api/image?p=${encodeURIComponent(draft.image_path)}`} alt="" className="w-full h-full object-cover" />
        </div>
      )}

      <div className="flex items-center justify-between gap-3">
        <div className="flex items-center gap-2 flex-wrap">
          <Badge>{draft.platform}</Badge>
          {isPublished ? <Badge tone="positive">published</Badge> : <Badge>draft</Badge>}
        </div>
        {draft.external_url && (
          <a href={draft.external_url} target="_blank" rel="noreferrer" className="text-[var(--color-ink-muted)] hover:text-[var(--color-accent)]">
            <ExternalLink className="w-4 h-4" />
          </a>
        )}
      </div>

      <div className="space-y-4 text-sm">
        <div>
          <p className="font-mono text-[11px] uppercase tracking-widest text-[var(--color-ink-muted)] mb-2">Ad title</p>
          <h3 className="font-display text-xl leading-tight">{draft.headline}</h3>
        </div>
        <div>
          <p className="font-mono text-[11px] uppercase tracking-widest text-[var(--color-ink-muted)] mb-2">Ad subheader</p>
          <p className="text-[var(--color-ink-muted)]">{draft.body}</p>
        </div>
        <div>
          <p className="font-mono text-[11px] uppercase tracking-widest text-[var(--color-ink-muted)] mb-2">CTA button text</p>
          <p className="font-medium">{draft.cta}</p>
        </div>
      </div>

      <dl className="grid grid-cols-2 gap-3 border-t border-[var(--color-hairline)] pt-4 text-xs">
        <div>
          <dt className="font-mono uppercase tracking-widest text-[var(--color-ink-muted)]">Generated</dt>
          <dd className="mt-1">{formatDate(draft.created_at)}</dd>
        </div>
        <div>
          <dt className="font-mono uppercase tracking-widest text-[var(--color-ink-muted)]">Published</dt>
          <dd className="mt-1">{formatDate(draft.published_at)}</dd>
        </div>
      </dl>

      {error && <p className="text-sm text-[var(--color-negative)]">{error}</p>}

      {refineOpen && !isPublished && (
        <div className="space-y-3">
          <Textarea
            value={guidance}
            onChange={(e) => setGuidance(e.target.value)}
            placeholder="e.g. make the title more concrete, emphasize ROI, keep the CTA softer"
            disabled={busy !== null}
          />
          <div className="flex justify-end">
            <Button size="sm" onClick={refine} disabled={busy !== null || !guidance.trim()}>
              <Pencil className="w-4 h-4" />
              {busy === "refine" ? "Refining..." : "Refine copy"}
            </Button>
          </div>
        </div>
      )}

      <div className="grid grid-cols-[1fr_1fr_auto] gap-2 mt-auto">
        {canPublish ? (
          <Button size="sm" onClick={publish} disabled={busy !== null}>
            <Send className="w-4 h-4" />
            {busy === "publish"
              ? "Publishing..."
              : credentialsConnected[draft.platform]
                ? "Publish"
                : "Connect"}
          </Button>
        ) : (
          <Button size="sm" variant="secondary" disabled>
            Published
          </Button>
        )}

        {isPublished ? (
          <Link href={analyticsTarget(draft)}>
            <Button size="sm" variant="secondary" className="w-full">
              <BarChart3 className="w-4 h-4" />
              Analytics
            </Button>
          </Link>
        ) : (
          <Button size="sm" variant="secondary" onClick={() => setRefineOpen((open) => !open)} disabled={busy !== null}>
            <Pencil className="w-4 h-4" />
            Refine
          </Button>
        )}

        <Button size="sm" variant="ghost" onClick={remove} disabled={busy !== null}>
          <Trash2 className="w-4 h-4" />
        </Button>
      </div>
    </Card>
  );
}
