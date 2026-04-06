"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import { DailyReading } from "@/components/DailyReading";
import { AskResult } from "@/components/AskResult";
import { MapExplorer } from "@/components/MapExplorer";
import { getDaily, getDailyArchive, getMap, localCalendarDateIso, postAsk } from "@/lib/api";

const MAX_CHARS = 4000;

const TABS = [
  { id: "ask" as const, label: "Ask" },
  { id: "daily" as const, label: "Daily" },
  { id: "archive" as const, label: "Archive" },
  { id: "map" as const, label: "Map" },
];

export default function Home() {
  const queryClient = useQueryClient();
  const [tab, setTab] = useState<(typeof TABS)[number]["id"]>("ask");
  const [dailyDate, setDailyDate] = useState<string | null>(null);
  const [input, setInput] = useState("");

  const goToTab = (t: (typeof TABS)[number]["id"]) => {
    if (t === "daily") setDailyDate(null);
    setTab(t);
  };

  /** Local calendar day for "today" (not server UTC). */
  const dailyTarget = dailyDate ?? localCalendarDateIso();

  const dailyQ = useQuery({
    queryKey: ["daily", dailyTarget],
    queryFn: () => getDaily(dailyTarget),
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

  const charsLeft = MAX_CHARS - input.length;
  const overLimit = charsLeft < 0;

  return (
    <div className="max-w-3xl mx-auto px-4 py-6 sm:py-10">
      <header className="mb-8 sm:mb-10 border-b border-ink/10 pb-6">
        <h1 className="font-serif text-2xl sm:text-3xl tracking-tight text-ink">Gospel Resonance</h1>
        <p className="text-muted mt-2 text-sm leading-relaxed">
          Bring your inner life to the words of Jesus — canonical Gospels and the Gospel of Thomas (noncanonical).
          All generated commentary is labeled.
        </p>
        <nav className="flex gap-x-6 mt-6 text-sm overflow-x-auto">
          {TABS.map(({ id, label }) => (
            <button
              key={id}
              type="button"
              onClick={() => goToTab(id)}
              className={`border-b-2 pb-1 transition-colors whitespace-nowrap ${
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
          <p className="text-sm text-muted leading-relaxed">
            Write anything — a single word, a question, a journal entry, a fear. The app finds Gospel passages and a
            Thomas saying that resonate with what you wrote, then reflects on them together.
          </p>

          <label className="block">
            <textarea
              className="w-full min-h-[140px] rounded border border-ink/15 bg-white/80 p-4 text-ink placeholder:text-muted/70 focus:border-accent focus:outline-none leading-relaxed"
              placeholder={`Try a single word like "peace" or "anger"\nor a longer thought like "I keep putting off a hard conversation"\nor even a paragraph from your journal`}
              value={input}
              onChange={(e) => setInput(e.target.value)}
              maxLength={MAX_CHARS + 200}
            />
            <span className={`block text-right text-xs mt-1 ${overLimit ? "text-red-700" : "text-muted/60"}`}>
              {overLimit
                ? `${Math.abs(charsLeft)} over limit`
                : charsLeft <= 400
                  ? `${charsLeft} left`
                  : ""}
            </span>
          </label>

          <button
            type="button"
            disabled={!input.trim() || overLimit || askM.isPending}
            onClick={() => askM.mutate()}
            className="rounded bg-accent px-6 py-2.5 sm:py-2 text-sm text-paper disabled:opacity-40 w-full sm:w-auto"
          >
            {askM.isPending ? "Listening…" : "Resonate"}
          </button>

          {askM.isError && (
            <p className="text-sm text-red-800 leading-relaxed">
              {String(askM.error).includes("429")
                ? "Please wait a moment before trying again."
                : `Something went wrong: ${askM.error instanceof Error ? askM.error.message : String(askM.error)}`}
            </p>
          )}

          {askM.data && <AskResult data={askM.data} />}
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
                No published daily for <span className="font-mono text-ink/80">{dailyTarget}</span> yet. The first open
                of a new day usually creates it automatically (may take ~30s). You need ingest once and a valid
                OpenRouter key. Or open <strong className="text-ink font-normal">Archive</strong> for another day.
              </p>
              <button
                type="button"
                onClick={() => queryClient.invalidateQueries({ queryKey: ["daily", dailyTarget] })}
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
            Each dot is a passage or saying. Nearby dots are closer in meaning. Color is by book — use the legend to
            filter. Tap or click any dot to read the passage.
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
    </div>
  );
}
