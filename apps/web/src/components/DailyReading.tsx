import type { DailyEntry } from "@/lib/api";

export function DailyReading({ data }: { data: DailyEntry }) {
  return (
    <article className="space-y-8">
      <p className="text-sm text-muted">{data.entry_date}</p>
      <h2 className="font-serif text-2xl capitalize">{data.theme_label}</h2>

      <p className="text-sm italic text-ink/90 leading-relaxed border-l-2 border-accent/40 pl-4">
        <span className="font-sans not-italic text-xs uppercase tracking-wide text-muted block mb-1">
          A short note on this theme
        </span>
        {data.daily_rationale_ai_assisted}{" "}
        <span className="text-xs not-italic text-muted">(AI-assisted)</span>
      </p>

      <div className="space-y-8 border-t border-ink/10 pt-8">
        <h3 className="text-sm font-medium text-ink">Readings (from the sources)</h3>
        {data.canonical && (
          <div>
            <h4 className="text-xs uppercase tracking-widest text-muted">Gospels (Matthew, Mark, Luke, or John)</h4>
            {data.canonical.ref_label && <p className="text-xs text-muted mt-1">{data.canonical.ref_label}</p>}
            <p className="font-serif mt-3 leading-relaxed">{data.canonical.primary_text}</p>
            <p className="text-xs text-muted mt-2">Published Bible translation — not written by AI.</p>
          </div>
        )}
        {data.thomas && (
          <div>
            <h4 className="text-xs uppercase tracking-widest text-muted">
              Gospel of Thomas (ancient text, not in the Bible)
            </h4>
            {data.thomas.ref_label && <p className="text-xs text-muted mt-1">{data.thomas.ref_label}</p>}
            <p className="font-serif mt-3 leading-relaxed">{data.thomas.primary_text}</p>
            <p className="text-xs text-muted mt-2">Published translation — not written by AI.</p>
          </div>
        )}
      </div>

      <div className="space-y-6 border-t border-ink/10 pt-8">
        <div>
          <h3 className="text-sm font-medium text-ink">Help to reflect</h3>
          <p className="text-xs text-muted mt-1 leading-relaxed">
            The notes below are computer-assisted reflections to connect the readings with the theme. They are not
            scripture and not religious authority.
          </p>
        </div>

        {data.why_matched_ai_assisted && (
          <div>
            <h4 className="text-xs uppercase tracking-widest text-muted">Why these two readings together</h4>
            <p className="mt-2 leading-relaxed text-sm">{data.why_matched_ai_assisted}</p>
          </div>
        )}
        {data.plain_reading_ai_assisted && (
          <div>
            <h4 className="text-xs uppercase tracking-widest text-muted">This Gospel passage and the theme</h4>
            <p className="mt-2 leading-relaxed text-sm">{data.plain_reading_ai_assisted}</p>
          </div>
        )}
        {data.deeper_reading_ai_assisted && (
          <div>
            <h4 className="text-xs uppercase tracking-widest text-muted">This Thomas saying and the theme</h4>
            <p className="mt-2 leading-relaxed text-sm">{data.deeper_reading_ai_assisted}</p>
          </div>
        )}
        <div>
          <h4 className="text-xs uppercase tracking-widest text-muted">Reading them side by side</h4>
          <p className="mt-2 leading-relaxed text-sm">{data.interpretation_ai_assisted}</p>
        </div>
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
              {data.reflection_questions_ai_assisted.map((q: string) => (
                <li key={q}>{q}</li>
              ))}
            </ul>
          </div>
        )}
      </div>

      {(data.generation_model || data.generation_prompt_version) && (
        <p className="text-[11px] text-muted/90 pt-4 border-t border-ink/10 leading-relaxed">
          {data.generation_model && (
            <>
              Reflections generated with <span className="font-mono">{data.generation_model}</span>
            </>
          )}
          {data.generation_prompt_version && (
            <>
              {data.generation_model ? " · " : ""}
              prompt <span className="font-mono">{data.generation_prompt_version}</span>
            </>
          )}
        </p>
      )}
    </article>
  );
}
