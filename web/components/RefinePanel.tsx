"use client";
import { useState } from "react";
import { Card } from "@/components/ui/Card";
import { Textarea } from "@/components/ui/Textarea";
import { ChevronDown, ChevronUp } from "lucide-react";

export function RefinePanel({ initial, onSave }: { initial: string; onSave: (v: string) => void }) {
  const [open, setOpen] = useState(false);
  const [value, setValue] = useState(initial);
  return (
    <Card className="mb-8">
      <button className="flex items-center justify-between w-full text-left" onClick={() => setOpen(!open)}>
        <span className="text-sm font-medium">Refine your angle</span>
        {open ? <ChevronUp className="w-4 h-4" /> : <ChevronDown className="w-4 h-4" />}
      </button>
      {open && (
        <div className="mt-4 space-y-2">
          <p className="text-xs text-[var(--color-ink-muted)]">This context feeds into every generation.</p>
          <Textarea value={value} onChange={(e) => setValue(e.target.value)} onBlur={() => onSave(value)} />
        </div>
      )}
    </Card>
  );
}
