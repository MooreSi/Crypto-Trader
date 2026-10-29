import { useEffect, useState } from "react";
import clsx from "clsx";
import type { JournalDraft, JournalEntry } from "@/api/types";
import { Button, inputCls } from "@/components/shared/ui";

const MOODS = [1, 2, 3, 4, 5];

/** "a, b ,, a" -> ["a", "b"]. Order kept, blanks and repeats dropped. */
export function parseTags(text: string): string[] {
  return [...new Set(text.split(",").map((t) => t.trim()).filter(Boolean))];
}

/**
 * The day's journal: a note, tags and a 1-5 mood. Kept per account (paper,
 * testnet and mainnet notes never mix). Saved on the button, not as you type.
 * Saving a blank day clears it.
 */
export function DayJournal({ day, entry, onSave }: {
  day: string; entry: JournalEntry | null; onSave: (day: string, draft: JournalDraft) => Promise<void>;
}) {
  const [note, setNote] = useState(entry?.note ?? "");
  const [tags, setTags] = useState((entry?.tags ?? []).join(", "));
  const [mood, setMood] = useState<number | null>(entry?.mood ?? null);
  const [state, setState] = useState<"idle" | "saving" | "saved" | "failed">("idle");
  useEffect(() => {
    setNote(entry?.note ?? "");
    setTags((entry?.tags ?? []).join(", "));
    setMood(entry?.mood ?? null);
    setState("idle");
  }, [day, entry]);

  const save = async () => {
    setState("saving");
    try {
      await onSave(day, { note, tags: parseTags(tags), mood });
      setState("saved");
    } catch {
      setState("failed");
    }
  };

  return (
    <section className="space-y-1.5" data-testid="day-journal">
      <p className="text-[10px] uppercase tracking-wider text-dim">Journal</p>
      <textarea aria-label="Journal note" value={note} maxLength={4000} rows={3}
        onChange={(e) => setNote(e.target.value)} placeholder="What happened, what you would do differently"
        className={clsx(inputCls, "w-full text-xs")} />
      <input aria-label="Tags" value={tags} onChange={(e) => setTags(e.target.value)}
        placeholder="Tags, comma separated (e.g. overtraded, CPI day)" className={clsx(inputCls, "w-full text-xs")} />
      <div className="flex items-center gap-1">
        <span className="mr-1 text-[11px] text-dim">Mood</span>
        {MOODS.map((m) => (
          <button key={m} type="button" aria-pressed={mood === m} aria-label={`Mood ${m} of 5`}
            onClick={() => setMood(mood === m ? null : m)}
            className={clsx("num h-6 w-6 rounded border text-[11px]",
              mood === m ? "border-accent bg-accent/15 text-text" : "border-line text-dim")}>
            {m}
          </button>
        ))}
        <span className="ml-auto mr-2 text-[11px] text-dim" role="status">
          {state === "saved" ? "Saved" : state === "failed" ? "Could not save" : ""}
        </span>
        <Button size="sm" onClick={() => void save()} disabled={state === "saving"}>
          {state === "saving" ? "Saving" : "Save"}
        </Button>
      </div>
    </section>
  );
}
