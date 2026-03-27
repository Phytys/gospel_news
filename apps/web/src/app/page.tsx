"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import { DailyReading } from "@/components/DailyReading";
import { MapExplorer } from "@/components/MapExplorer";
import { getDaily, getDailyArchive, getMap, postAsk } from "@/lib/api";

const CHIPS = ["anxiety", "peace", "forgiveness", "conflict", "loneliness", "discernment", "wholeness", "distraction"];

const TABS = [
  { id: "ask" as const, label: "Ask" },
  { id: "daily" as const, label: "Daily" },
  { id: "archive" as const, label: "Past days" },
  { id: "map" as const, label: "Map / Explore" },
  { id: "saved" as const, label: "Saved" },
];

export default function Home() {
  const queryClient = useQueryClient();
  const [tab, setTab] = useState<(typeof TABS)[number]["id"]>("ask");
  /** `null` = today’s daily on the server */
  const [dailyDate, setDailyDate] = useState<string | null>(null);
  const [input, setInput] = useState("");

  const goToTab = (t: (typeof TABS)[number]["id"]) => {
    if (t === "daily") setDailyDate(null);
    setTab(t);
  };

  const dailyQ = useQuery({
    queryKey: ["daily", dailyDate ?? "today"],
    queryFn: () => getDaily(dailyDate ?? undefined),
    enabled: tab === "daily",
  });

  const archiveQ = useQuery({
    queryKey: ["daily-archive"],
    queryFn: getDailyArchive,
    enabled: tab === "archive",
  });

  const mapQ = useQuery({
    queryKey: ["map"],
    queryFn: () => getMap("all"),
    enabled: tab === "map",
  });

  const askM = useMutation({
    mutationFn: () => postAsk(input),
  });

  return (
    <div className="max-w-3xl mx-auto px-4 py-10">
      <header className="mb-10 border-b border-ink/10 pb-6">
        <h1 className="font-serif text-3xl tracking-tight text-ink">Gospel Resonance</h1>
        <p className="text-muted mt-2 text-sm leading-relaxed">
          Bring your inner life to the words of Jesus — canonical Gospels and the Gospel of Thomas (noncanonical).
          All generated commentary is labeled.
        </p>
        <nav className="flex flex-wrap gap-x-6 gap-y-2 mt-6 text-sm">
          {TABS.map(({ id, label }) => (
            <button
              key={id}
              type="button"
              onClick={() => goToTab(id)}
              className={`border-b-2 pb-1 transition-colors ${
                tab === id ? "border-accent text-ink" : "border-transparent text-muted hover:text-ink"
              }`}
            >
              {label}
            </button>
          ))}
        </nav>
      </header>

      {tab === "ask" && (
        <section className="space-y-6">
          <label className="block">
            <span className="text-sm text-muted">Your words</span>
            <textarea
              className="mt-2 w-full min-h-[160px] rounded border border-ink/15 bg-white/80 p-4 text-ink placeholder:text-muted focus:border-accent focus:outline-none"
              placeholder="A question, journal fragment, fear, or situation…"
              value={input}
              onChange={(e) => setInput(e.target.value)}
            />
          </label>
          <div className="flex flex-wrap gap-2">
            {CHIPS.map((c) => (
              <button
                key={c}
                type="button"
                className="rounded-full border border-ink/10 px-3 py-1 text-xs text-muted hover:border-accent hover:text-ink"
                onClick={() => setInput((prev) => (prev ? prev + " " : "") + c)}
              >
                {c}
              </button>
            ))}
          </div>
          <button
            type="button"
            disabled={!input.trim() || askM.isPending}
            onClick={() => askM.mutate()}
            className="rounded bg-accent px-5 py-2 text-sm text-paper disabled:opacity-40"
          >
            {askM.isPending ? "Listening…" : "Resonate"}
          </button>

          {askM.isError && (
            <pre className="text-sm text-red-800 whitespace-pre-wrap">{String(askM.error)}</pre>
          )}

          {askM.data && (
            <article className="space-y-8 border-t border-ink/10 pt-8 mt-8">
              {askM.data.canonical?.map((c: { id: string; ref_label: string; primary_text: string }, i: number) => (
                <div key={c.id}>
                  <h3 className="text-xs uppercase tracking-widest text-muted">Primary Text — Canonical Gospel · #{i + 1}</h3>
                  <p className="font-serif text-lg mt-2 leading-relaxed">{c.primary_text}</p>
                  <p className="text-xs text-muted mt-1">{c.ref_label}</p>
                </div>
              ))}
              {askM.data.thomas && (
                <div>
                  <h3 className="text-xs uppercase tracking-widest text-muted">
                    Primary Text — Gospel of Thomas (noncanonical)
                  </h3>
                  <p className="font-serif text-lg mt-2 leading-relaxed">{askM.data.thomas.primary_text}</p>
                  <p className="text-xs text-muted mt-1">{askM.data.thomas.ref_label}</p>
                </div>
              )}
              <details className="group rounded border border-ink/10 bg-white/40 p-4">
                <summary className="cursor-pointer text-sm font-medium text-ink">Explain (AI-assisted)</summary>
                <div className="mt-4 space-y-4 text-sm">
                  <div>
                    <h4 className="text-xs uppercase text-muted">Plain reading</h4>
                    <p className="mt-1 leading-relaxed">{askM.data.plain_reading_ai_assisted}</p>
                  </div>
                  <div>
                    <h4 className="text-xs uppercase text-muted">Deeper reading</h4>
                    <p className="mt-1 leading-relaxed">{askM.data.deeper_reading_ai_assisted}</p>
                  </div>
                  <div>
                    <h4 className="text-xs uppercase text-muted">Why this matched</h4>
                    <p className="mt-1 leading-relaxed">{askM.data.why_matched_ai_assisted}</p>
                  </div>
                  {askM.data.tension_ai_assisted && (
                    <div>
                      <h4 className="text-xs uppercase text-muted">Tension / Caveat</h4>
                      <p className="mt-1 leading-relaxed">{askM.data.tension_ai_assisted}</p>
                    </div>
                  )}
                </div>
              </details>
              <div>
                <h3 className="text-xs uppercase tracking-widest text-muted">Interpretation (AI-assisted)</h3>
                <p className="mt-2 leading-relaxed">{askM.data.interpretation_ai_assisted}</p>
              </div>
              <div>
                <h3 className="text-xs uppercase tracking-widest text-muted">Reflection Questions (AI-assisted)</h3>
                <ul className="mt-2 list-disc pl-5 space-y-1">
                  {askM.data.reflection_questions_ai_assisted?.map((q: string) => (
                    <li key={q}>{q}</li>
                  ))}
                </ul>
              </div>
            </article>
          )}
        </section>
      )}

      {tab === "daily" && (
        <section>
          {dailyDate && (
            <div className="flex flex-wrap items-center justify-between gap-2 mb-6 text-sm">
              <p className="text-muted">
                Viewing{" "}
                <time dateTime={dailyDate}>
                  {new Date(dailyDate + "T12:00:00").toLocaleDateString(undefined, {
                    weekday: "long",
                    year: "numeric",
                    month: "long",
                    day: "numeric",
                  })}
                </time>
              </p>
              <button
                type="button"
                onClick={() => setDailyDate(null)}
                className="text-accent underline underline-offset-2 hover:text-ink"
              >
                Jump to today
              </button>
            </div>
          )}

          {dailyQ.isLoading && <p className="text-muted">Loading…</p>}
          {dailyQ.isError && (
            <p className="text-red-800 whitespace-pre-wrap">
              Could not load daily: {dailyQ.error instanceof Error ? dailyQ.error.message : String(dailyQ.error)}
            </p>
          )}
          {!dailyQ.isLoading && !dailyQ.isError && dailyQ.data === null && (
            <div className="space-y-3 text-muted leading-relaxed text-sm">
              <p>
                No daily for {dailyDate ? "this date" : "today"} yet. The app creates one automatically after the API and
                worker start (and after scripture is ingested once).{" "}
                <strong className="text-ink font-normal">Rebuild-map is only for the Map tab,</strong> not required here.
              </p>
              <p>
                If this is a new server, run <code className="text-ink/90">ingest_pipeline</code> once (README), then
                wait a minute or use{" "}
                <code className="text-ink/90">POST /api/v1/admin/generate-daily</code> with your admin token.
              </p>
              <button
                type="button"
                onClick={() =>
                  queryClient.invalidateQueries({ queryKey: ["daily", dailyDate ?? "today"] })
                }
                className="rounded border border-ink/20 px-3 py-1.5 text-xs text-ink hover:bg-white/60"
              >
                Check again
              </button>
            </div>
          )}
          {dailyQ.data && <DailyReading data={dailyQ.data} />}
        </section>
      )}

      {tab === "archive" && (
        <section className="space-y-4">
          <p className="text-muted text-sm leading-relaxed">
            Every published daily is stored on the server. Pick a date to open that day&apos;s theme and readings.
          </p>
          {archiveQ.isLoading && <p className="text-muted">Loading…</p>}
          {archiveQ.isError && (
            <p className="text-red-800 text-sm">
              {archiveQ.error instanceof Error ? archiveQ.error.message : String(archiveQ.error)}
            </p>
          )}
          {archiveQ.data && archiveQ.data.entries.length === 0 && (
            <p className="text-muted text-sm">No past dailies yet.</p>
          )}
          {archiveQ.data && archiveQ.data.entries.length > 0 && (
            <ul className="divide-y divide-ink/10 rounded border border-ink/10 bg-white/40">
              {archiveQ.data.entries.map((row) => (
                <li key={row.entry_date}>
                  <button
                    type="button"
                    onClick={() => {
                      setDailyDate(row.entry_date);
                      setTab("daily");
                    }}
                    className="w-full text-left px-4 py-3 hover:bg-white/80 transition-colors flex flex-wrap justify-between gap-2 gap-y-1"
                  >
                    <span className="font-mono text-sm text-muted">{row.entry_date}</span>
                    <span className="font-serif text-ink capitalize">{row.theme_label}</span>
                  </button>
                </li>
              ))}
            </ul>
          )}
        </section>
      )}

      {tab === "map" && (
        <section className="space-y-4">
          <p className="text-muted text-sm leading-relaxed">
            Each dot is a passage or saying. Position comes from the same embedding model used elsewhere: nearby dots
            are closer in meaning (UMAP of vectors). Dot color shows a layout region (K-means on those coordinates—purely
            from the data, not hand-labeled themes). Thomas sayings are slightly larger with a stronger outline; Gospel
            passages are smaller.
          </p>
          {mapQ.isLoading && <p className="text-muted">Loading…</p>}
          {mapQ.isError && (
            <p className="text-red-800 text-sm">
              Could not load the map: {mapQ.error instanceof Error ? mapQ.error.message : String(mapQ.error)}
            </p>
          )}
          {mapQ.data && <MapExplorer points={mapQ.data.points || []} />}
        </section>
      )}

      {tab === "saved" && (
        <section>
          <p className="text-muted text-sm">Saved sessions and notes require account setup (MVP placeholder).</p>
        </section>
      )}
    </div>
  );
}

