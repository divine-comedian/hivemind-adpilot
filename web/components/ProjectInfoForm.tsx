"use client";

import { useEffect, useState } from "react";
import { Save, CheckCircle2 } from "lucide-react";
import { Button } from "@/components/ui/Button";
import { Card } from "@/components/ui/Card";
import { Input } from "@/components/ui/Input";
import { Textarea } from "@/components/ui/Textarea";
import { ProjectInfo, WorkspaceState, api } from "@/lib/api";

function fallbackProject(ws: WorkspaceState): ProjectInfo {
  return {
    project_name: ws.project?.project_name || ws.hivemind.website_url,
    description: ws.project?.description || "",
    geographics: ws.project?.geographics || [],
    audiences: ws.project?.audiences || [],
  };
}

export function ProjectInfoForm({
  workspace,
  onChange,
  onApproved,
  showApprove = false,
}: {
  workspace: WorkspaceState;
  onChange: (workspace: WorkspaceState) => void;
  onApproved?: () => void;
  showApprove?: boolean;
}) {
  const [value, setValue] = useState<ProjectInfo>(fallbackProject(workspace));
  const [geoText, setGeoText] = useState(value.geographics.join(", "));
  const [audiencesText, setAudiencesText] = useState(value.audiences.join("\n"));
  const [saving, setSaving] = useState(false);
  const [approving, setApproving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [saved, setSaved] = useState(false);

  useEffect(() => {
    const next = fallbackProject(workspace);
    setValue(next);
    setGeoText(next.geographics.join(", "));
    setAudiencesText(next.audiences.join("\n"));
  }, [workspace]);

  const save = async () => {
    setSaving(true);
    setError(null);
    setSaved(false);
    try {
      const payload: ProjectInfo = {
        ...value,
        geographics: geoText.split(",").map((s) => s.trim()).filter(Boolean),
        audiences: audiencesText.split("\n").map((s) => s.trim()).filter(Boolean),
      };
      const updated = await api.patchProject(payload);
      onChange(updated);
      setSaved(true);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Save failed");
    } finally {
      setSaving(false);
    }
  };

  const approve = async () => {
    setApproving(true);
    setError(null);
    try {
      const updated = await api.approveProject();
      onChange(updated);
      onApproved?.();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Approval failed");
    } finally {
      setApproving(false);
    }
  };

  return (
    <Card className="space-y-6 p-8">
      <div>
        <p className="font-mono text-xs uppercase tracking-widest text-[var(--color-ink-muted)]">Project Info</p>
        <h2 className="font-display text-2xl mt-1">Review what Hivemind found</h2>
      </div>

      <label className="block space-y-2">
        <span className="text-sm font-medium">Title</span>
        <Input
          value={value.project_name}
          onChange={(e) => setValue((curr) => ({ ...curr, project_name: e.target.value }))}
        />
      </label>

      <label className="block space-y-2">
        <span className="text-sm font-medium">Description</span>
        <Textarea
          className="min-h-[234px]"
          value={value.description}
          onChange={(e) => setValue((curr) => ({ ...curr, description: e.target.value }))}
          placeholder="Short project description from the site scrape."
        />
      </label>

      <label className="block space-y-2">
        <span className="text-sm font-medium">Geographics</span>
        <Input
          value={geoText}
          onChange={(e) => setGeoText(e.target.value)}
          placeholder="Canada, United States"
        />
      </label>

      <label className="block space-y-2">
        <span className="text-sm font-medium">Audiences</span>
        <Textarea
          className="min-h-[80px]"
          value={audiencesText}
          onChange={(e) => setAudiencesText(e.target.value)}
          placeholder="One audience per line — e.g. Canadian SMB owners"
        />
        {(() => {
          const overlong = audiencesText
            .split("\n")
            .map((s) => s.trim())
            .filter(Boolean)
            .filter((s) => s.length > 25);
          if (overlong.length === 0) {
            return (
              <p className="text-xs text-[var(--color-ink-muted)]">
                One per line. Max 25 characters each.
              </p>
            );
          }
          return (
            <p className="text-xs text-[var(--color-negative)]">
              Too long (25 char max): {overlong.map((s) => `"${s}"`).join(", ")}
            </p>
          );
        })()}
      </label>

      {error && <p className="text-sm text-[var(--color-negative)]">{error}</p>}
      {saved && <p className="text-sm text-[var(--color-positive)]">Project info saved.</p>}

      <div className="flex flex-wrap justify-end gap-3">
        <Button
          type="button"
          variant="secondary"
          onClick={save}
          disabled={
            saving ||
            !value.project_name.trim() ||
            audiencesText.split("\n").some((s) => s.trim().length > 25)
          }
        >
          <Save className="w-4 h-4" />
          {saving ? "Saving..." : "Save"}
        </Button>
        {showApprove && (
          <Button type="button" onClick={approve} disabled={approving || saving}>
            <CheckCircle2 className="w-4 h-4" />
            {approving ? "Approving..." : "Approve and draft"}
          </Button>
        )}
      </div>
    </Card>
  );
}
