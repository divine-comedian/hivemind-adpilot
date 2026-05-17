"use client";

import { useState } from "react";
import { X } from "lucide-react";
import { Button } from "@/components/ui/Button";
import { Input } from "@/components/ui/Input";
import { api, WorkspaceState } from "@/lib/api";

type Platform = "linkedin" | "facebook";

interface Props {
  platform: Platform;
  onClose: () => void;
  onSaved: (ws: WorkspaceState) => void;
}

export function CredentialsPanel({ platform, onClose, onSaved }: Props) {
  const [accessToken, setAccessToken] = useState("");
  const [accountId, setAccountId] = useState("");
  const [orgUrn, setOrgUrn] = useState("");
  const [pageId, setPageId] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const submit = async (e: React.FormEvent) => {
    e.preventDefault();
    setSubmitting(true);
    setError(null);
    try {
      const body =
        platform === "linkedin"
          ? { linkedin: { access_token: accessToken, account_id: accountId, org_urn: orgUrn } }
          : { facebook: { access_token: accessToken, account_id: accountId, page_id: pageId } };
      const ws = await api.patchCredentials(body);
      onSaved(ws);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Save failed");
    } finally {
      setSubmitting(false);
    }
  };

  const label = platform === "linkedin" ? "LinkedIn" : "Facebook";

  return (
    <div className="fixed inset-0 z-40 flex justify-end" role="dialog" aria-modal="true">
      <div
        className="absolute inset-0 bg-[var(--color-ink)]/30"
        onClick={onClose}
        aria-hidden="true"
      />
      <aside className="relative h-full w-full max-w-md bg-[var(--color-surface)] border-l border-[var(--color-hairline)] p-8 overflow-y-auto">
        <div className="flex items-baseline justify-between mb-6">
          <h2 className="font-display text-2xl">Connect {label}</h2>
          <button
            onClick={onClose}
            aria-label="Close"
            className="text-[var(--color-ink-muted)] hover:text-[var(--color-ink)]"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        <p className="text-sm text-[var(--color-ink-muted)] mb-6">
          Tokens are validated on save and persisted locally in{" "}
          <span className="font-mono">workspace/.tokens.env</span> (gitignored).
        </p>

        <form onSubmit={submit} className="space-y-5">
          <div className="space-y-1.5">
            <label className="text-sm font-medium">Access token</label>
            <Input
              type="password"
              value={accessToken}
              onChange={(e) => setAccessToken(e.target.value)}
              autoComplete="off"
              required
              minLength={10}
            />
          </div>

          <div className="space-y-1.5">
            <label className="text-sm font-medium">Ad account ID</label>
            <Input
              value={accountId}
              onChange={(e) => setAccountId(e.target.value)}
              placeholder={platform === "linkedin" ? "510884436" : "22243234"}
              required
            />
          </div>

          {platform === "linkedin" ? (
            <div className="space-y-1.5">
              <label className="text-sm font-medium">Organization URN</label>
              <Input
                value={orgUrn}
                onChange={(e) => setOrgUrn(e.target.value)}
                placeholder="urn:li:organization:112708829"
                pattern="^urn:li:organization:\d+$"
                required
              />
            </div>
          ) : (
            <div className="space-y-1.5">
              <label className="text-sm font-medium">Facebook Page ID</label>
              <Input
                value={pageId}
                onChange={(e) => setPageId(e.target.value)}
                required
              />
            </div>
          )}

          {error && <p className="text-sm text-[var(--color-negative)]">{error}</p>}

          <div className="flex justify-end gap-2 pt-2">
            <Button type="button" variant="secondary" onClick={onClose} disabled={submitting}>
              Cancel
            </Button>
            <Button type="submit" disabled={submitting}>
              {submitting ? "Validating…" : `Save ${label}`}
            </Button>
          </div>
        </form>
      </aside>
    </div>
  );
}
