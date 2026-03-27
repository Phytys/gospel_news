/** Shared API response shapes (keep in sync with FastAPI). */

export interface AskResponse {
  session_id: string;
  canonical: Array<{
    id: string;
    ref_label: string;
    tradition: string;
    primary_text: string;
    theme_tags: string[];
  }>;
  thomas: {
    id: string;
    ref_label: string;
    tradition: string;
    primary_text: string;
    noncanonical_label: string;
    theme_tags: string[];
  };
  interpretation_ai_assisted: string;
  plain_reading_ai_assisted: string;
  deeper_reading_ai_assisted: string;
  why_matched_ai_assisted: string;
  tension_ai_assisted: string | null;
  reflection_questions_ai_assisted: string[];
}

export interface DailyResponse {
  entry_date: string;
  theme_label: string;
  daily_rationale_ai_assisted: string;
  canonical: { id: string; ref_label: string; primary_text: string; tradition: string } | null;
  thomas: {
    id: string;
    ref_label: string;
    primary_text: string;
    tradition: string;
    noncanonical_label: string;
  } | null;
  interpretation_ai_assisted: string;
  plain_reading_ai_assisted: string;
  deeper_reading_ai_assisted: string;
  why_matched_ai_assisted: string;
  tension_ai_assisted: string | null;
  reflection_questions_ai_assisted: string[];
}
