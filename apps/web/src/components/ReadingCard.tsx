export type ReadingCardProps = {
  tradition: "canonical" | "thomas";
  refLabel?: string;
  text: string;
  /** Extra label for noncanonical sources */
  badge?: string;
};

export function ReadingCard({ tradition, refLabel, text, badge }: ReadingCardProps) {
  const heading =
    tradition === "canonical"
      ? "Gospels (Matthew, Mark, Luke, or John)"
      : "Gospel of Thomas (ancient text, not in the Bible)";

  const provenance =
    tradition === "canonical"
      ? "Published Bible translation \u2014 not written by AI."
      : "Published translation \u2014 not written by AI.";

  return (
    <div>
      <h4 className="text-xs uppercase tracking-widest text-muted">{heading}</h4>
      {badge && <p className="text-[11px] text-muted/80 mt-0.5 italic">{badge}</p>}
      {refLabel && <p className="text-xs text-muted mt-1">{refLabel}</p>}
      <p className="font-serif mt-3 leading-relaxed">{text}</p>
      <p className="text-xs text-muted mt-2">{provenance}</p>
    </div>
  );
}
