"use client";

import { useSearchParams, useRouter } from "next/navigation";
import { Suspense, useState } from "react";
import { Button } from "@/components/ui/Button";
import { Input } from "@/components/ui/Input";

function DemoLoginInner() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const next = searchParams.get("next") || "/onboard";
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  const submit = async (event: React.FormEvent) => {
    event.preventDefault();
    setSubmitting(true);
    setError(null);
    const response = await fetch("/api/demo-login", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ password }),
    });
    if (!response.ok) {
      setError("That password did not work.");
      setSubmitting(false);
      return;
    }
    router.replace(next);
  };

  return (
    <main className="min-h-screen flex items-center justify-center px-6">
      <form onSubmit={submit} className="w-full max-w-sm bg-[var(--color-surface)] border border-[var(--color-hairline)] rounded-sm p-8 space-y-5">
        <div>
          <p className="font-mono text-xs uppercase tracking-widest text-[var(--color-ink-muted)] mb-3">AdPilot Demo</p>
          <h1 className="font-display text-3xl">Enter demo password</h1>
          <p className="text-sm text-[var(--color-ink-muted)] mt-2">
            This demo uses live Hivemind calls and demo ad data behind a lightweight access gate.
          </p>
        </div>
        <Input
          type="password"
          value={password}
          onChange={(event) => setPassword(event.target.value)}
          placeholder="Password"
          autoFocus
          required
        />
        {error && <p className="text-sm text-[var(--color-negative)]">{error}</p>}
        <Button type="submit" disabled={submitting} className="w-full">
          {submitting ? "Checking..." : "Enter"}
        </Button>
      </form>
    </main>
  );
}

export default function DemoLoginPage() {
  return (
    <Suspense fallback={<p>Loading...</p>}>
      <DemoLoginInner />
    </Suspense>
  );
}
