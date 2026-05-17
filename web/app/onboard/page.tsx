import { OnboardForm } from "@/components/OnboardForm";

export default function OnboardPage() {
  return (
    <main className="min-h-screen px-12 py-16">
      <header className="max-w-5xl mx-auto mb-12">
        <p className="font-mono text-xs uppercase tracking-widest text-[var(--color-ink-muted)] mb-3">AdPilot</p>
        <h1 className="font-display text-5xl leading-tight">Paste a URL.</h1>
        <p className="font-display italic text-2xl text-[var(--color-ink-muted)] mt-2">Hivemind reads your site. AdPilot takes it from there.</p>
      </header>
      <OnboardForm />
    </main>
  );
}
