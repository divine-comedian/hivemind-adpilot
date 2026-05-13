import Link from "next/link";

export default function WorkspaceLayout({ children }: { children: React.ReactNode }) {
  return (
    <div className="min-h-screen flex">
      <aside className="w-56 border-r border-[var(--color-hairline)] px-6 py-8 sticky top-0 h-screen">
        <p className="font-mono text-xs uppercase tracking-widest text-[var(--color-ink-muted)] mb-8">AdPilot</p>
        <nav className="space-y-2 text-sm">
          <Link href="/workspace/drafts" className="block hover:text-[var(--color-accent)]">Drafts</Link>
          <Link href="/workspace/analytics" className="block hover:text-[var(--color-accent)]">Analytics</Link>
          <Link href="/workspace/diagnose" className="block hover:text-[var(--color-accent)]">Diagnose</Link>
        </nav>
      </aside>
      <main className="flex-1 px-12 py-12">{children}</main>
    </div>
  );
}
