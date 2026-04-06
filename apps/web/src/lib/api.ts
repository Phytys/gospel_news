/**
 * API base URL:
 * - Local dev: set NEXT_PUBLIC_API_URL=http://localhost:8000 (browser calls API on another port; CORS on API).
 * - Production behind nginx (same host): leave empty or unset → requests use same origin, e.g. /api/v1/ask
 * - Production split hosts: set NEXT_PUBLIC_API_URL=https://api.yourdomain.com
 */
function apiPrefix(): string {
  const b = (process.env.NEXT_PUBLIC_API_URL ?? "").trim();
  if (!b) return "";
  return b.replace(/\/$/, "");
}

function apiUrl(path: string): string {
  const p = path.startsWith("/") ? path : `/${path}`;
  const prefix = apiPrefix();
  if (!prefix) return p;
  return `${prefix}${p}`;
}

export async function postAsk(text: string, savePrompt = false) {
  const r = await fetch(apiUrl("/api/v1/ask"), {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      text,
      timezone: Intl.DateTimeFormat().resolvedOptions().timeZone,
      save_prompt: savePrompt,
    }),
  });
  if (!r.ok) throw new Error(await r.text());
  return r.json();
}

export type DailyArchiveRow = {
  entry_date: string;
  theme_label: string;
};

export async function getDailyArchive(): Promise<{ entries: DailyArchiveRow[] }> {
  const r = await fetch(apiUrl("/api/v1/daily/archive"), { cache: "no-store" });
  if (!r.ok) throw new Error(await r.text());
  return r.json();
}

export type DailyEntry = {
  entry_date: string;
  theme_label: string;
  daily_rationale_ai_assisted: string;
  canonical?: { ref_label?: string; primary_text: string };
  thomas?: { ref_label?: string; primary_text: string };
  /** Together: how the pair speaks as one reading (AI-assisted). */
  interpretation_ai_assisted: string;
  plain_reading_ai_assisted?: string;
  deeper_reading_ai_assisted?: string;
  why_matched_ai_assisted?: string;
  tension_ai_assisted?: string | null;
  reflection_questions_ai_assisted?: string[];
  generation_model?: string;
  generation_prompt_version?: string;
};

/** User's local calendar date as YYYY-MM-DD (for "today" daily — avoids server UTC vs your midnight). */
export function localCalendarDateIso(): string {
  const d = new Date();
  const y = d.getFullYear();
  const m = String(d.getMonth() + 1).padStart(2, "0");
  const day = String(d.getDate()).padStart(2, "0");
  return `${y}-${m}-${day}`;
}

/** 404 → no row for that date (not an error). Pass explicit YYYY-MM-DD for "today" (see localCalendarDateIso). */
export async function getDaily(date?: string): Promise<DailyEntry | null> {
  const q = date ? `?d=${encodeURIComponent(date)}` : "";
  const r = await fetch(apiUrl(`/api/v1/daily${q}`), { cache: "no-store" });
  if (r.status === 404) return null;
  if (!r.ok) throw new Error(await r.text());
  return r.json();
}

export async function getMap(tradition?: string) {
  const q = tradition ? `?tradition=${encodeURIComponent(tradition)}` : "";
  const r = await fetch(apiUrl(`/api/v1/map${q}`), { cache: "no-store" });
  if (!r.ok) throw new Error(await r.text());
  return r.json();
}
