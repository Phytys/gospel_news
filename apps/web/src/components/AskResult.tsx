import { useState } from "react";
import { ReadingCard } from "./ReadingCard";

type CanonicalHit = { id: string; ref_label: string; primary_text: string; book?: string };

export type AskResultData = {
  session_id?: string;
  canonical?: CanonicalHit[];
  thomas?: { id: string; ref_label: string; primary_text: string };
  theme_labels?: string[];
  interpretation_ai_assisted?: string;
  plain_reading_ai_assisted?: string;
  deeper_reading_ai_assisted?: string;
  why_matched_ai_assisted?: string;
  tension_ai_assisted?: string | null;
  reflection_questions_ai_assisted?: string[];
  generation_model?: string;
};

function buildShareText(data: AskResultData): string {
  const lines: string[] = ["Gospel Resonance", ""];
  data.canonical?.forEach((c) => {
    lines.push(`${c.ref_label}:`);
    lines.push(c.primary_text);
    lines.push("");
  });
  if (data.thomas) {
    lines.push(`${data.thomas.ref_label} (noncanonical):`);
    lines.push(data.thomas.primary_text);
    lines.push("");
  }
  if (data.interpretation_ai_assisted) {
    lines.push("Side by side (AI-assisted):");
    lines.push(data.interpretation_ai_assisted);
    lines.push("");
  }
  if (data.reflection_questions_ai_assisted?.length) {
    lines.push("Questions to sit with:");
    data.reflection_questions_ai_assisted.forEach((q) => lines.push(`  • ${q}`));
  }
  return lines.join("\n");
}

export function AskResult({ data }: { data: AskResultData }) {
  const [copied, setCopied] = useState(false);

  const handleShare = async () => {
    const text = buildShareText(data);
    if (navigator.share) {
      try {
        await navigator.share({ title: "Gospel Resonance", text });
        return;
      } catch {}
    }
    await navigator.clipboard.writeText(text);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  return (
    <article className="space-y-8 border-t border-ink/10 pt-8 mt-8">
      <div className="flex flex-wrap items-center justify-between gap-2">
        {data.theme_labels && data.theme_labels.length > 0 && (
          <div className="flex flex-wrap gap-2">
            {data.theme_labels.map((t) => (
            <span
              key={t}
              className="rounded-full border border-accent/30 bg-accent/5 px-3 py-0.5 text-xs text-accent capitalize"
            >
              {t}
            </span>
          ))}
        </div>
        )}
        <button
          type="button"
          onClick={handleShare}
          className="rounded border border-ink/15 px-3 py-1.5 text-xs text-muted hover:text-ink hover:bg-white/60 transition-colors"
        >
          {copied ? "Copied" : "Share"}
        </button>
      </div>

      <div className="space-y-8">
        <h3 className="text-sm font-medium text-ink">Readings (from the sources)</h3>
        {data.canonical?.map((c) => (
          <ReadingCard key={c.id} tradition="canonical" refLabel={c.ref_label} text={c.primary_text} />
        ))}
        {data.thomas && (
          <ReadingCard tradition="thomas" refLabel={data.thomas.ref_label} text={data.thomas.primary_text} />
        )}
      </div>

      <div className="space-y-6 border-t border-ink/10 pt-8">
        <div>
          <h3 className="text-sm font-medium text-ink">Help to reflect</h3>
          <p className="text-xs text-muted mt-1 leading-relaxed">
            The notes below are computer-assisted reflections connecting these readings with your words. They are not
            scripture and not religious authority.
          </p>
        </div>

        {data.why_matched_ai_assisted && (
          <div>
            <h4 className="text-xs uppercase tracking-widest text-muted">Why these readings</h4>
            <p className="mt-2 leading-relaxed text-sm">{data.why_matched_ai_assisted}</p>
          </div>
        )}
        {data.plain_reading_ai_assisted && (
          <div>
            <h4 className="text-xs uppercase tracking-widest text-muted">These Gospel passages</h4>
            <p className="mt-2 leading-relaxed text-sm">{data.plain_reading_ai_assisted}</p>
          </div>
        )}
        {data.deeper_reading_ai_assisted && (
          <div>
            <h4 className="text-xs uppercase tracking-widest text-muted">This Thomas saying</h4>
            <p className="mt-2 leading-relaxed text-sm">{data.deeper_reading_ai_assisted}</p>
          </div>
        )}
        {data.interpretation_ai_assisted && (
          <div>
            <h4 className="text-xs uppercase tracking-widest text-muted">Reading them side by side</h4>
            <p className="mt-2 leading-relaxed text-sm">{data.interpretation_ai_assisted}</p>
          </div>
        )}
        {data.tension_ai_assisted && (
          <div>
            <h4 className="text-xs uppercase tracking-widest text-muted">A tension or caveat</h4>
            <p className="mt-2 leading-relaxed text-sm">{data.tension_ai_assisted}</p>
          </div>
        )}
        {data.reflection_questions_ai_assisted && data.reflection_questions_ai_assisted.length > 0 && (
          <div>
            <h4 className="text-xs uppercase tracking-widest text-muted">Questions to sit with</h4>
            <ul className="mt-2 list-disc pl-5 space-y-2 text-sm">
              {data.reflection_questions_ai_assisted.map((q) => (
                <li key={q}>{q}</li>
              ))}
            </ul>
          </div>
        )}
      </div>

      {data.generation_model && (
        <p className="text-[11px] text-muted/90 pt-4 border-t border-ink/10 leading-relaxed break-words">
          Reflections generated with <span className="font-mono break-all">{data.generation_model}</span>
        </p>
      )}
    </article>
  );
}
