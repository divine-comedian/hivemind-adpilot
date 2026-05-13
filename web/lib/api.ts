"use client";

const BASE = process.env.NEXT_PUBLIC_API_BASE ?? "http://localhost:8000";

export interface WorkspaceState {
  workspace_id: string;
  business: {
    name: string;
    description: string;
    audiences: string[];
    geographies: string[];
    stage: string;
    voice_notes: string;
    focus_notes: string;
  };
  brand: { logo_path: string; accent_hex: string; voice_notes: string };
  hivemind: {
    project_id: string;
    reports: Record<string, { job_id: string; status: string; last_synced_at: string | null }>;
  };
  platforms: {
    linkedin: { account_id: string; org_urn: string };
    facebook: { account_id: string; page_id: string };
  };
  created_at: string;
}

export interface Draft {
  id: string;
  workspace_id: string;
  platform: "linkedin" | "facebook";
  headline: string;
  body: string;
  cta: string;
  image_path: string;
  rationale: string;
  strategist_trace: Record<string, unknown>;
  tier: "A" | "B";
  parent_draft_id: string | null;
  status: "draft" | "pushed" | "discarded" | "superseded";
  created_at: string;
}

async function j<T>(path: string, init?: RequestInit): Promise<T> {
  const r = await fetch(`${BASE}${path}`, {
    headers: { "Content-Type": "application/json", ...(init?.headers ?? {}) },
    ...init,
  });
  if (!r.ok) throw new Error(`${r.status}: ${await r.text()}`);
  return r.json();
}

export const api = {
  createWorkspace: (body: unknown) => j<WorkspaceState>("/workspace", { method: "POST", body: JSON.stringify(body) }),
  getWorkspace: () => j<WorkspaceState | null>("/workspace/me"),
  patchFocus: (focus_notes: string) => j<WorkspaceState>("/workspace", { method: "PATCH", body: JSON.stringify({ focus_notes }) }),
  listDrafts: () => j<Draft[]>("/drafts"),
  getDraft: (id: string) => j<Draft>(`/drafts/${id}`),
  pushDraft: (id: string, body: { platform: "linkedin" | "facebook"; campaign_id?: string }) =>
    j(`/drafts/${id}/push`, { method: "POST", body: JSON.stringify(body) }),
  regenerateDraft: (id: string) => j<Draft>(`/drafts/${id}/regenerate`, { method: "POST" }),
  getAnalytics: (window: string = "30d") => j(`/analytics?window=${window}`),
  acceptDiagnose: (body: unknown) => j("/diagnose/accept", { method: "POST", body: JSON.stringify(body) }),
};

export function subscribeWorkspaceEvents(onEvent: (e: { type: string; [k: string]: unknown }) => void) {
  const src = new EventSource(`${BASE}/workspace/events`);
  ["intelligence_ready", "report_failed"].forEach((t) => {
    src.addEventListener(t, (ev) => onEvent({ type: t, ...JSON.parse((ev as MessageEvent).data) }));
  });
  return () => src.close();
}

export interface ChainStep {
  step: string;
  status: "running" | "complete";
  payload?: Record<string, unknown>;
}

export function streamGenerate(body: unknown, onStep: (s: ChainStep) => void, onResult: (r: { drafts: Draft[] }) => void) {
  const url = new URL(`${BASE}/generate`);
  url.search = new URLSearchParams({ payload: JSON.stringify(body) }).toString();
  const src = new EventSource(url.toString());
  src.addEventListener("chain_step", (e) => onStep(JSON.parse((e as MessageEvent).data)));
  src.addEventListener("result", (e) => { onResult(JSON.parse((e as MessageEvent).data)); src.close(); });
  src.addEventListener("error", () => src.close());
  return () => src.close();
}
