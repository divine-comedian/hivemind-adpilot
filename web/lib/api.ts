"use client";

export const API_BASE = process.env.NEXT_PUBLIC_API_BASE ?? "/api/sidecar";

export type EnrichmentStatus = "enriching" | "ready" | "failed";

export interface WorkspaceState {
  workspace_id: string;
  hivemind: {
    project_id: string;
    website_url: string;
    enrichment_status: EnrichmentStatus;
  };
  project?: ProjectInfo;
  business: {
    voice_notes: string;
    focus_notes: string;
  };
  platforms: {
    linkedin?: { account_id: string; org_urn: string };
    facebook?: { account_id: string; page_id: string };
  };
  created_at: string;
  project_approved_at?: string;
  last_angle_ideas?: DraftIdeasResponse;
}

export interface ProjectInfo {
  project_name: string;
  description: string;
  geographics: string[];
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
  source?: string;
  source_angle_id?: string | null;
  tier: "A" | "B";
  parent_draft_id: string | null;
  status: "draft" | "pushed" | "discarded" | "superseded";
  created_at: string;
  published_at?: string | null;
  external_urn?: string | null;
  external_url?: string | null;
}

export interface AngleIdea {
  id: string;
  title?: string;
  angle: string;
  angle_description?: string;
  hivemind_hooks?: string[];
  project_information?: string[];
  fit_reason?: string;
  reasoning: string;
}

export interface DraftIdeasResponse {
  conversation_id?: string | null;
  angles: AngleIdea[];
  tier: "A" | "B";
  created_at?: string;
  updated_at?: string;
}

export interface LinkedInCredentials {
  access_token: string;
  account_id: string;
  org_urn: string;
}

export interface FacebookCredentials {
  access_token: string;
  account_id: string;
  page_id: string;
}

async function j<T>(path: string, init?: RequestInit): Promise<T> {
  let r: Response;
  try {
    r = await fetch(`${API_BASE}${path}`, {
      headers: { "Content-Type": "application/json", ...(init?.headers ?? {}) },
      ...init,
    });
  } catch {
    throw new Error(`Unable to reach the AdPilot API at ${API_BASE}. Start the sidecar server or set NEXT_PUBLIC_API_BASE.`);
  }

  if (!r.ok) {
    const text = await r.text();
    let message = text;
    try {
      const body = JSON.parse(text);
      message = body.error ?? body.detail ?? text;
    } catch {
      // The sidecar can return plain text for FastAPI errors.
    }
    throw new Error(`${r.status}: ${message}`);
  }
  return r.json();
}

export const api = {
  createWorkspace: (body: { website_url: string }) =>
    j<WorkspaceState>("/workspace", { method: "POST", body: JSON.stringify(body) }),
  getWorkspace: () => j<WorkspaceState | null>("/workspace/me"),
  patchProject: (body: ProjectInfo) =>
    j<WorkspaceState>("/workspace/project", { method: "PATCH", body: JSON.stringify(body) }),
  approveProject: () => j<WorkspaceState>("/workspace/project/approve", { method: "POST" }),
  patchVoice: (voice_notes: string, focus_notes: string) =>
    j<WorkspaceState>("/workspace", { method: "PATCH", body: JSON.stringify({ voice_notes, focus_notes }) }),
  patchCredentials: (body: { linkedin?: LinkedInCredentials; facebook?: FacebookCredentials }) =>
    j<WorkspaceState>("/workspace/credentials", { method: "PATCH", body: JSON.stringify(body) }),
  listDrafts: () => j<Draft[]>("/drafts"),
  getDraft: (id: string) => j<Draft>(`/drafts/${id}`),
  pushDraft: (
    id: string,
    body: { platform: "linkedin" | "facebook"; campaign_id?: string; adset_id?: string },
  ) => j<{ external_urn: string; external_url: string }>(`/drafts/${id}/push`, {
    method: "POST",
    body: JSON.stringify(body),
  }),
  regenerateDraft: (id: string) => j<Draft>(`/drafts/${id}/regenerate`, { method: "POST" }),
  refineDraft: (id: string, guidance: string) =>
    j<Draft>(`/drafts/${id}/refine`, { method: "POST", body: JSON.stringify({ guidance }) }),
  deleteDraft: (id: string) => j<{ ok: boolean }>(`/drafts/${id}`, { method: "DELETE" }),
  getDraftIdeas: () => j<DraftIdeasResponse>("/draft-ideas", { method: "POST" }),
  refineDraftIdea: (body: { angle: AngleIdea; guidance: string; conversation_id?: string | null }) =>
    j<DraftIdeasResponse>("/draft-ideas/refine", { method: "POST", body: JSON.stringify(body) }),
  dismissDraftIdea: (angle_id: string) =>
    j<DraftIdeasResponse>("/draft-ideas/dismiss", { method: "POST", body: JSON.stringify({ angle_id }) }),
  getAnalytics: (window: string = "30d") => j(`/analytics?window=${window}`),
  acceptDiagnose: (body: unknown) => j("/diagnose/accept", { method: "POST", body: JSON.stringify(body) }),
};

export function subscribeWorkspaceEvents(onEvent: (e: { type: string; [k: string]: unknown }) => void) {
  const src = new EventSource(`${API_BASE}/workspace/events`);
  ["enrichment_ready", "enrichment_failed"].forEach((t) => {
    src.addEventListener(t, (ev) => onEvent({ type: t, ...JSON.parse((ev as MessageEvent).data) }));
  });
  return () => src.close();
}

export interface ChainStep {
  step: string;
  status: "running" | "complete";
  payload?: Record<string, unknown>;
}

export function streamGenerate(
  body: unknown,
  onStep: (s: ChainStep) => void,
  onResult: (r: { drafts: Draft[]; conversation_id?: string | null }) => void,
  onError?: (message: string) => void,
) {
  const controller = new AbortController();
  let closed = false;
  let src: EventSource | null = null;

  j<{ job_id: string }>("/generate", {
    method: "POST",
    body: JSON.stringify(body),
    signal: controller.signal,
  })
    .then(({ job_id }) => {
      if (closed) return;
      const url = new URL(`${API_BASE}/generate/${job_id}/events`, window.location.origin);
      src = new EventSource(url.toString());
      src.addEventListener("chain_step", (e) => onStep(JSON.parse((e as MessageEvent).data)));
      src.addEventListener("result", (e) => {
        onResult(JSON.parse((e as MessageEvent).data));
        src?.close();
      });
      src.addEventListener("error", (e) => {
        const data = (e as MessageEvent).data;
        if (data && onError) {
          try {
            onError(JSON.parse(data).error ?? "Generation failed");
          } catch {
            onError("Generation failed");
          }
        }
        src?.close();
      });
    })
    .catch((e) => {
      if (closed || e?.name === "AbortError") return;
      onError?.(e instanceof Error ? e.message : "Generation failed");
    });

  return () => {
    closed = true;
    controller.abort();
    src?.close();
  };
}
