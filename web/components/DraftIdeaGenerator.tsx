"use client";

import { useState } from "react";
import { Lightbulb, Pencil, Trash2, WandSparkles } from "lucide-react";
import { Button } from "@/components/ui/Button";
import { Card } from "@/components/ui/Card";
import { Badge } from "@/components/ui/Badge";
import { ChainTrace } from "@/components/ChainTrace";
import { Input } from "@/components/ui/Input";
import { AngleIdea, ChainStep, Draft, DraftIdeasResponse, api, streamGenerate } from "@/lib/api";

export function DraftIdeaGenerator({
  initialIdeas,
  onComplete,
  onIdeasChange,
}: {
  initialIdeas?: DraftIdeasResponse;
  onComplete: (drafts: Draft[]) => void;
  onIdeasChange?: (ideas: DraftIdeasResponse) => void;
}) {
  const [ideas, setIdeas] = useState<DraftIdeasResponse | undefined>(initialIdeas);
  const [selected, setSelected] = useState<AngleIdea | null>(null);
  const [loadingIdeas, setLoadingIdeas] = useState(false);
  const [generating, setGenerating] = useState(false);
  const [refiningId, setRefiningId] = useState<string | null>(null);
  const [refineOpenId, setRefineOpenId] = useState<string | null>(null);
  const [refineText, setRefineText] = useState("");
  const [steps, setSteps] = useState<ChainStep[]>([]);
  const [error, setError] = useState<string | null>(null);
  const ghostwriterBusy = loadingIdeas || generating || refiningId !== null;

  const updateIdeas = (next: DraftIdeasResponse) => {
    setIdeas(next);
    onIdeasChange?.(next);
  };

  const getIdeas = async () => {
    setLoadingIdeas(true);
    setError(null);
    setSelected(null);
    setSteps([]);
    try {
      updateIdeas(await api.getDraftIdeas());
    } catch (e) {
      setError(e instanceof Error ? e.message : "Could not generate ideas");
    } finally {
      setLoadingIdeas(false);
    }
  };

  const generate = (angle: AngleIdea) => {
    setSelected(angle);
    setGenerating(true);
    setError(null);
    setSteps([]);
    streamGenerate(
      {
        angle_id: angle.id,
        conversation_id: ideas?.conversation_id,
        platforms: ["facebook", "linkedin"],
        ads_per_platform: 3,
      },
      (step) => setSteps((curr) => [...curr.filter((item) => item.step !== step.step), step]),
      (result) => {
        setGenerating(false);
        onComplete(result.drafts);
      },
      (message) => {
        setGenerating(false);
        setError(message);
      },
    );
  };

  const dismiss = async (angleId: string) => {
    setError(null);
    try {
      updateIdeas(await api.dismissDraftIdea(angleId));
      if (selected?.id === angleId) setSelected(null);
      if (refineOpenId === angleId) {
        setRefineOpenId(null);
        setRefineText("");
      }
    } catch (e) {
      setError(e instanceof Error ? e.message : "Could not dismiss angle");
    }
  };

  const refine = async (angle: AngleIdea) => {
    const guidance = refineText.trim();
    if (!guidance) return;
    setRefiningId(angle.id);
    setError(null);
    try {
      updateIdeas(await api.refineDraftIdea({
        angle,
        guidance: `Refine this ad-set angle using this user direction: ${guidance}`,
        conversation_id: ideas?.conversation_id,
      }));
      setRefineOpenId(null);
      setRefineText("");
    } catch (e) {
      setError(e instanceof Error ? e.message : "Could not refine angle");
    } finally {
      setRefiningId(null);
    }
  };

  return (
    <section className="mb-10 space-y-5">
      <div className="flex items-center justify-between gap-4">
        <div>
          <h2 className="font-display text-2xl">Ad set ideas</h2>
          <p className="text-sm text-[var(--color-ink-muted)] mt-1">
            Pick an angle first, then AdPilot drafts three Facebook and three LinkedIn ads around it.
          </p>
        </div>
        <Button onClick={getIdeas} disabled={ghostwriterBusy}>
          <Lightbulb className="w-4 h-4" />
          {loadingIdeas ? "Asking Ghostwriter..." : "Give me some Ideas"}
        </Button>
      </div>

      {error && <p className="text-sm text-[var(--color-negative)]">{error}</p>}

      {ideas?.angles?.length ? (
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
          {ideas.angles.map((idea) => {
            const active = selected?.id === idea.id;
            return (
              <Card key={idea.id} className={active ? "border-[var(--color-accent)]" : ""}>
                {active && (
                  <div className="flex items-start justify-end gap-3">
                    <Badge>selected</Badge>
                  </div>
                )}
                <h3 className="font-display text-xl leading-tight mt-4">{idea.title || idea.angle}</h3>
                <div className="mt-5 space-y-4 text-sm">
                  <div>
                    <p className="font-mono text-[11px] uppercase tracking-widest text-[var(--color-ink-muted)] mb-2">
                      Angle description
                    </p>
                    <p className="text-[var(--color-ink-muted)]">{idea.angle_description || idea.angle}</p>
                  </div>
                  <div>
                    <p className="font-mono text-[11px] uppercase tracking-widest text-[var(--color-ink-muted)] mb-2">
                      Why it fits
                    </p>
                    <p className="text-[var(--color-ink-muted)]">{idea.fit_reason || idea.reasoning}</p>
                  </div>
                </div>
                <div className="mt-5 grid grid-cols-3 gap-2">
                  <Button
                    variant={active ? "secondary" : "primary"}
                    onClick={() => generate(idea)}
                    disabled={ghostwriterBusy}
                  >
                    <WandSparkles className="w-4 h-4" />
                    {active && generating ? "Generating..." : "Use this angle"}
                  </Button>
                  <Button
                    variant="secondary"
                    onClick={() => {
                      setRefineOpenId(refineOpenId === idea.id ? null : idea.id);
                      setRefineText("");
                    }}
                    disabled={ghostwriterBusy}
                  >
                    <Pencil className="w-4 h-4" />
                    Refine
                  </Button>
                  <Button
                    variant="ghost"
                    onClick={() => dismiss(idea.id)}
                    disabled={ghostwriterBusy}
                  >
                    <Trash2 className="w-4 h-4" />
                    Dismiss
                  </Button>
                </div>
                {refineOpenId === idea.id && (
                  <div className="mt-4 space-y-3 border-t border-[var(--color-hairline)] pt-4">
                    <Input
                      value={refineText}
                      onChange={(e) => setRefineText(e.target.value)}
                      placeholder="e.g. make this more CFO-focused, use the $50 offer, avoid fear-based framing"
                      disabled={ghostwriterBusy}
                    />
                    <div className="flex justify-end">
                      <Button
                        size="sm"
                        onClick={() => refine(idea)}
                        disabled={ghostwriterBusy || !refineText.trim()}
                      >
                        <Pencil className="w-4 h-4" />
                        {refiningId === idea.id ? "Refining..." : "Refine angle"}
                      </Button>
                    </div>
                  </div>
                )}
              </Card>
            );
          })}
        </div>
      ) : (
        <Card className="text-sm text-[var(--color-ink-muted)]">
          Ghostwriter has not proposed ad-set angles yet.
        </Card>
      )}

      {steps.length > 0 && (
        <Card>
          <ChainTrace steps={steps} />
        </Card>
      )}
    </section>
  );
}
