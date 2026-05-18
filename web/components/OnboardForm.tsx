"use client";

import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import { useRouter, useSearchParams } from "next/navigation";
import { useEffect, useState } from "react";
import { Button } from "@/components/ui/Button";
import { Card } from "@/components/ui/Card";
import { Input } from "@/components/ui/Input";
import { ProjectInfoForm } from "@/components/ProjectInfoForm";
import { WorkspaceState, api } from "@/lib/api";

const schema = z.object({
  website_url: z.string().url("Needs to be a full URL like https://example.com"),
});

type FormValues = z.infer<typeof schema>;

export function OnboardForm() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const demoMode = searchParams.get("demo") === "1";
  const [submitting, setSubmitting] = useState(false);
  const [loadingExisting, setLoadingExisting] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [workspace, setWorkspace] = useState<WorkspaceState | null>(null);

  const { register, handleSubmit, formState: { errors } } = useForm<FormValues>({
    resolver: zodResolver(schema),
  });

  useEffect(() => {
    if (demoMode) {
      setLoadingExisting(false);
      return;
    }
    let active = true;
    api.getWorkspace()
      .then((existing) => {
        if (active && existing) setWorkspace(existing);
      })
      .catch(() => {})
      .finally(() => {
        if (active) setLoadingExisting(false);
      });
    return () => {
      active = false;
    };
  }, [demoMode]);

  const onSubmit = async (values: FormValues) => {
    setSubmitting(true);
    setError(null);
    try {
      if (demoMode) {
        await new Promise((r) => setTimeout(r, 1200));
        const existing = await api.getWorkspace();
        if (existing) {
          setWorkspace(existing);
          return;
        }
      }
      setWorkspace(await api.createWorkspace({ website_url: values.website_url }));
    } catch (e) {
      setError(e instanceof Error ? e.message : "Submit failed");
    } finally {
      setSubmitting(false);
    }
  };

  if (loadingExisting) {
    return (
      <div className="max-w-2xl mx-auto">
        <Card className="space-y-2">
          <p className="font-mono text-xs uppercase tracking-widest text-[var(--color-ink-muted)]">AdPilot</p>
          <p className="font-display text-2xl">Checking for an existing project...</p>
        </Card>
      </div>
    );
  }

  if (workspace) {
    return (
      <div className="max-w-5xl mx-auto">
        <ProjectInfoForm
          workspace={workspace}
          onChange={setWorkspace}
          onApproved={() => router.push("/workspace/drafts")}
          showApprove
        />
      </div>
    );
  }

  return (
    <form onSubmit={handleSubmit(onSubmit)} className="max-w-2xl mx-auto">
      <Card className="space-y-5">
        <div className="space-y-1.5">
          <label className="text-sm font-medium">Website</label>
          <Input
            {...register("website_url")}
            placeholder="https://aurevon.ca"
            autoComplete="url"
            autoFocus
          />
          {errors.website_url?.message && (
            <p className="text-xs text-[var(--color-negative)]">{errors.website_url.message}</p>
          )}
          <p className="text-xs text-[var(--color-ink-muted)] mt-2">
            Hivemind reads your site, extracts audiences and stage, and runs competitive
            intelligence in the background. Takes a few minutes — you can start generating
            drafts immediately.
          </p>
        </div>

        {error && <p className="text-[var(--color-negative)] text-sm">{error}</p>}

        <div className="flex justify-end">
          <Button type="submit" size="lg" disabled={submitting}>
            {submitting ? "Creating project..." : "Continue"}
          </Button>
        </div>
      </Card>

      <p className="text-xs text-[var(--color-ink-muted)] mt-6 text-center">
        You&rsquo;ll connect LinkedIn and Facebook ad accounts the first time you push a draft.
      </p>
    </form>
  );
}
