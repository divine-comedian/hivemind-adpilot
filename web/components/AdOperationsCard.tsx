"use client";

import Link from "next/link";
import { BarChart3, ExternalLink, Pencil, Save, Send, Trash2, X } from "lucide-react";
import { useState } from "react";
import { Badge } from "@/components/ui/Badge";
import { Button } from "@/components/ui/Button";
import { Card } from "@/components/ui/Card";
import { Input } from "@/components/ui/Input";
import { Textarea } from "@/components/ui/Textarea";
import { Draft, api } from "@/lib/api";

interface Props {
  draft: Draft;
  credentialsConnected: { linkedin: boolean; facebook: boolean };
  onRequestCredentials: (platform: "linkedin" | "facebook") => void;
  onChange: () => void;
}

const CTA_OPTIONS = [
  "LEARN_MORE",
  "SIGN_UP",
  "REGISTER",
  "DOWNLOAD",
  "APPLY",
  "SUBSCRIBE",
  "GET_QUOTE",
] as const;

function normalizeCta(value: string) {
  return CTA_OPTIONS.includes(value as (typeof CTA_OPTIONS)[number]) ? value : "LEARN_MORE";
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
  const [editing, setEditing] = useState(false);
  const [guidance, setGuidance] = useState("");
  const [headline, setHeadline] = useState(draft.headline);
  const [body, setBody] = useState(draft.body);
  const [cta, setCta] = useState(normalizeCta(draft.cta));
  const [error, setError] = useState<string | null>(null);
  const isPublished = draft.status === "pushed" || !!draft.published_at;
  const canPublish = !isPublished && draft.status === "draft";

  const resetEdit = () => {
    setHeadline(draft.headline);
    setBody(draft.body);
    setCta(normalizeCta(draft.cta));
    setEditing(false);
  };

  const saveEdit = async () => {
    const nextHeadline = headline.trim();
    const nextBody = body.trim();
    if (!nextHeadline || !nextBody) {
      setError("Ad title and subheader are required");
      return;
    }
    setBusy("edit");
    setError(null);
    try {
      await api.updateDraft(draft.id, { headline: nextHeadline, body: nextBody, cta });
      setEditing(false);
      onChange();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Could not save ad copy");
    } finally {
      setBusy(null);
    }
  };

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
        <div className="flex items-center gap-2">
          {!isPublished && !editing && (
            <button
              onClick={() => {
                setRefineOpen(false);
                setEditing(true);
              }}
              aria-label="Edit ad copy"
              className="text-[var(--color-ink-muted)] hover:text-[var(--color-accent)]"
            >
              <Pencil className="w-4 h-4" />
            </button>
          )}
          {draft.external_url && (
            <a href={draft.external_url} target="_blank" rel="noreferrer" className="text-[var(--color-ink-muted)] hover:text-[var(--color-accent)]">
              <ExternalLink className="w-4 h-4" />
            </a>
          )}
        </div>
      </div>

      {editing ? (
        <div className="space-y-4 text-sm">
          <div>
            <label className="font-mono text-[11px] uppercase tracking-widest text-[var(--color-ink-muted)] mb-2 block">Ad title</label>
            <Input value={headline} onChange={(e) => setHeadline(e.target.value)} maxLength={70} disabled={busy !== null} />
          </div>
          <div>
            <label className="font-mono text-[11px] uppercase tracking-widest text-[var(--color-ink-muted)] mb-2 block">Ad subheader</label>
            <Textarea
              value={body}
              onChange={(e) => setBody(e.target.value)}
              maxLength={150}
              disabled={busy !== null}
              className="min-h-[96px]"
            />
          </div>
          <div>
            <label className="font-mono text-[11px] uppercase tracking-widest text-[var(--color-ink-muted)] mb-2 block">CTA button text</label>
            <select
              value={cta}
              onChange={(e) => setCta(e.target.value)}
              disabled={busy !== null}
              className="h-10 w-full border border-[var(--color-hairline)] bg-[var(--color-surface)] px-3 text-[15px] text-[var(--color-ink)] rounded-sm"
            >
              {CTA_OPTIONS.map((option) => (
                <option key={option} value={option}>{option}</option>
              ))}
            </select>
          </div>
          <div className="flex justify-end gap-2">
            <Button size="sm" variant="secondary" onClick={resetEdit} disabled={busy !== null}>
              <X className="w-4 h-4" />
              Cancel
            </Button>
            <Button size="sm" onClick={saveEdit} disabled={busy !== null}>
              <Save className="w-4 h-4" />
              {busy === "edit" ? "Saving..." : "Save"}
            </Button>
          </div>
        </div>
      ) : (
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
      )}

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

      {refineOpen && !isPublished && !editing && (
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
          <Button size="sm" onClick={publish} disabled={busy !== null || editing}>
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
          <Button
            size="sm"
            variant="secondary"
            onClick={() => {
              setEditing(false);
              setRefineOpen((open) => !open);
            }}
            disabled={busy !== null || editing}
          >
            <Pencil className="w-4 h-4" />
            Refine
          </Button>
        )}

        <Button size="sm" variant="ghost" onClick={remove} disabled={busy !== null || editing}>
          <Trash2 className="w-4 h-4" />
        </Button>
      </div>
    </Card>
  );
}
