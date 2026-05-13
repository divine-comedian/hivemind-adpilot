"use client";

import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import { useRouter } from "next/navigation";
import { useState } from "react";
import { Button } from "@/components/ui/Button";
import { Card } from "@/components/ui/Card";
import { Input } from "@/components/ui/Input";
import { Textarea } from "@/components/ui/Textarea";
import { api } from "@/lib/api";

const schema = z.object({
  business: z.object({
    name: z.string().min(1),
    website: z.string().url(),
    description: z.string().min(20).max(2000),
    audiences_csv: z.string().min(1),
    geographies_csv: z.string().min(1),
    stage: z.enum(["seed", "growth", "mature"]),
  }),
  brand: z.object({
    accent_hex: z.string().regex(/^#[0-9A-Fa-f]{6}$/),
    voice_notes: z.string(),
  }),
  linkedin: z.object({
    access_token: z.string().min(10),
    account_id: z.string().min(1),
    org_urn: z.string().regex(/^urn:li:organization:\d+$/),
  }),
  facebook: z.object({
    access_token: z.string().min(10),
    account_id: z.string().min(1),
    page_id: z.string().min(1),
  }),
});

type FormValues = z.infer<typeof schema>;

export function OnboardForm() {
  const router = useRouter();
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const { register, handleSubmit, formState: { errors } } = useForm<FormValues>({
    resolver: zodResolver(schema),
    defaultValues: { business: { stage: "seed" }, brand: { accent_hex: "#BE3A2C", voice_notes: "" } },
  });

  const onSubmit = async (values: FormValues) => {
    setSubmitting(true); setError(null);
    try {
      await api.createWorkspace({
        business: {
          ...values.business,
          audiences: values.business.audiences_csv.split(",").map((s) => s.trim()).filter(Boolean),
          geographies: values.business.geographies_csv.split(",").map((s) => s.trim()).filter(Boolean),
        },
        brand: values.brand,
        linkedin: values.linkedin,
        facebook: values.facebook,
      });
      router.push("/workspace/drafts");
    } catch (e) {
      setError(e instanceof Error ? e.message : "Submit failed");
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <form onSubmit={handleSubmit(onSubmit)} className="space-y-10 max-w-3xl mx-auto">
      <Section title="A · The business">
        <Field label="Name" error={errors.business?.name?.message}>
          <Input {...register("business.name")} placeholder="Aurevon Intelligence" />
        </Field>
        <Field label="Website" error={errors.business?.website?.message}>
          <Input {...register("business.website")} placeholder="https://aurevon.ca" />
        </Field>
        <Field label="One paragraph description (20-2000 chars)" error={errors.business?.description?.message}>
          <Textarea {...register("business.description")} placeholder="Plain-language summary of what the business sells, who it serves, what makes it different." />
        </Field>
        <Field label="Audiences (comma-separated, up to 5)" error={errors.business?.audiences_csv?.message}>
          <Input {...register("business.audiences_csv")} placeholder="sports-bettors, data-curious" />
        </Field>
        <Field label="Geographies (comma-separated, up to 5)" error={errors.business?.geographies_csv?.message}>
          <Input {...register("business.geographies_csv")} placeholder="CA, US" />
        </Field>
        <Field label="Stage">
          <select {...register("business.stage")} className="h-10 w-full border border-[var(--color-hairline)] bg-[var(--color-surface)] px-3 rounded-sm">
            <option value="seed">Seed</option>
            <option value="growth">Growth</option>
            <option value="mature">Mature</option>
          </select>
        </Field>
      </Section>

      <Section title="B · The brand">
        <Field label="Accent color (hex)" error={errors.brand?.accent_hex?.message}>
          <Input type="color" {...register("brand.accent_hex")} className="h-12 p-1" />
        </Field>
        <Field label="Voice notes (optional)">
          <Textarea {...register("brand.voice_notes")} placeholder="One paragraph. Tone, words you use, words you don't." />
        </Field>
      </Section>

      <Section title="C · Ad platform access">
        <p className="text-sm text-[var(--color-ink-muted)]">
          Tokens are validated on submit. Stored locally in <span className="font-mono">workspace/.tokens.env</span>, gitignored.
        </p>
        <Field label="LinkedIn access token" error={errors.linkedin?.access_token?.message}>
          <Input type="password" {...register("linkedin.access_token")} />
        </Field>
        <Field label="LinkedIn ad account ID" error={errors.linkedin?.account_id?.message}>
          <Input {...register("linkedin.account_id")} placeholder="510884436" />
        </Field>
        <Field label="LinkedIn organization URN" error={errors.linkedin?.org_urn?.message}>
          <Input {...register("linkedin.org_urn")} placeholder="urn:li:organization:112708829" />
        </Field>
        <Field label="Facebook access token" error={errors.facebook?.access_token?.message}>
          <Input type="password" {...register("facebook.access_token")} />
        </Field>
        <Field label="Facebook ad account ID" error={errors.facebook?.account_id?.message}>
          <Input {...register("facebook.account_id")} />
        </Field>
        <Field label="Facebook Page ID" error={errors.facebook?.page_id?.message}>
          <Input {...register("facebook.page_id")} />
        </Field>
      </Section>

      {error && <p className="text-[var(--color-negative)] text-sm">{error}</p>}
      <div className="flex justify-end">
        <Button type="submit" size="lg" disabled={submitting}>
          {submitting ? "Creating project…" : "Create workspace"}
        </Button>
      </div>
    </form>
  );
}

function Section({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <section className="space-y-6">
      <h2 className="font-display text-2xl">{title}</h2>
      <Card className="space-y-5">{children}</Card>
    </section>
  );
}

function Field({ label, error, children }: { label: string; error?: string; children: React.ReactNode }) {
  return (
    <div className="space-y-1.5">
      <label className="text-sm font-medium">{label}</label>
      {children}
      {error && <p className="text-xs text-[var(--color-negative)]">{error}</p>}
    </div>
  );
}
