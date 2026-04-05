"use client";

import { useCallback, useEffect, useMemo, useRef, useState } from "react";

export type MapPoint = {
  id: string;
  x: number;
  y: number;
  tradition: string;
  book?: string;
  ref_label?: string;
  chunk_type?: string;
  preview?: string;
  cluster_id?: string | null;
  cluster_label?: string | null;
};

const BOOK_COLORS: Record<string, { fill: string; glow: string }> = {
  Matthew: { fill: "#6ea8fe", glow: "#4a90d9" },
  Mark: { fill: "#f87171", glow: "#dc2626" },
  Luke: { fill: "#6ee7b7", glow: "#34d399" },
  John: { fill: "#fbbf24", glow: "#d97706" },
  Thomas: { fill: "#c084fc", glow: "#9333ea" },
};
const DEFAULT_COLOR = { fill: "#94a3b8", glow: "#64748b" };

function bookColor(book?: string) {
  return (book && BOOK_COLORS[book]) || DEFAULT_COLOR;
}

const W = 800;
const H = 500;
const PAD = 20;
const MIN_ZOOM = 0.3;
const MAX_ZOOM = 12;

export function MapExplorer({ points }: { points: MapPoint[] }) {
  const wrapRef = useRef<HTMLDivElement>(null);
  const svgRef = useRef<SVGSVGElement>(null);
  const [zoom, setZoom] = useState(1);
  const [pan, setPan] = useState({ x: 0, y: 0 });
  const dragRef = useRef<{ active: boolean; lastX: number; lastY: number }>({
    active: false,
    lastX: 0,
    lastY: 0,
  });
  const pinchRef = useRef<{ active: boolean; dist: number; zoom: number }>({
    active: false,
    dist: 0,
    zoom: 1,
  });

  const [selected, setSelected] = useState<MapPoint | null>(null);
  const [hover, setHover] = useState<MapPoint | null>(null);
  const [tipPos, setTipPos] = useState({ x: 0, y: 0 });
  const [filter, setFilter] = useState<string | null>(null);
  const [isMobile, setIsMobile] = useState(false);

  useEffect(() => {
    const mq = window.matchMedia("(pointer: coarse)");
    setIsMobile(mq.matches);
    const handler = (e: MediaQueryListEvent) => setIsMobile(e.matches);
    mq.addEventListener("change", handler);
    return () => mq.removeEventListener("change", handler);
  }, []);

  const layout = useMemo(() => {
    if (!points.length) return null;
    const xs = points.map((p) => p.x);
    const ys = points.map((p) => p.y);
    const minX = Math.min(...xs);
    const maxX = Math.max(...xs);
    const minY = Math.min(...ys);
    const maxY = Math.max(...ys);
    const sx = (x: number) => PAD + ((x - minX) / (maxX - minX || 1)) * (W - 2 * PAD);
    const sy = (y: number) => PAD + ((y - minY) / (maxY - minY || 1)) * (H - 2 * PAD);
    return { sx, sy };
  }, [points]);

  const filteredPoints = useMemo(() => {
    if (!filter) return points;
    return points.map((p) => ({ ...p, _dimmed: p.book !== filter }));
  }, [points, filter]);

  const onWheel = useCallback((e: React.WheelEvent<SVGSVGElement>) => {
    e.preventDefault();
    const factor = e.deltaY > 0 ? 0.9 : 1.11;
    setZoom((z) => Math.min(MAX_ZOOM, Math.max(MIN_ZOOM, z * factor)));
  }, []);

  const onPointerDown = (e: React.PointerEvent<SVGSVGElement>) => {
    if (e.pointerType === "touch") return;
    if (e.button !== 0) return;
    (e.target as SVGSVGElement).setPointerCapture(e.pointerId);
    dragRef.current = { active: true, lastX: e.clientX, lastY: e.clientY };
  };

  const onPointerMove = (e: React.PointerEvent<SVGSVGElement>) => {
    if (e.pointerType === "touch") return;
    if (!dragRef.current.active) return;
    const dx = e.clientX - dragRef.current.lastX;
    const dy = e.clientY - dragRef.current.lastY;
    dragRef.current.lastX = e.clientX;
    dragRef.current.lastY = e.clientY;
    const rect = e.currentTarget.getBoundingClientRect();
    setPan((p) => ({
      x: p.x + (dx / rect.width) * W,
      y: p.y + (dy / rect.height) * H,
    }));
  };

  const onPointerUp = (e: React.PointerEvent<SVGSVGElement>) => {
    if (e.pointerType === "touch") return;
    dragRef.current.active = false;
    try {
      (e.target as SVGSVGElement).releasePointerCapture(e.pointerId);
    } catch {}
  };

  // Touch handlers for pan and pinch-to-zoom
  const onTouchStart = useCallback((e: React.TouchEvent<SVGSVGElement>) => {
    if (e.touches.length === 2) {
      const dx = e.touches[0].clientX - e.touches[1].clientX;
      const dy = e.touches[0].clientY - e.touches[1].clientY;
      pinchRef.current = { active: true, dist: Math.hypot(dx, dy), zoom };
      dragRef.current.active = false;
    } else if (e.touches.length === 1) {
      pinchRef.current.active = false;
      dragRef.current = { active: true, lastX: e.touches[0].clientX, lastY: e.touches[0].clientY };
    }
  }, [zoom]);

  const onTouchMove = useCallback((e: React.TouchEvent<SVGSVGElement>) => {
    e.preventDefault();
    if (pinchRef.current.active && e.touches.length === 2) {
      const dx = e.touches[0].clientX - e.touches[1].clientX;
      const dy = e.touches[0].clientY - e.touches[1].clientY;
      const newDist = Math.hypot(dx, dy);
      const scale = newDist / pinchRef.current.dist;
      setZoom(Math.min(MAX_ZOOM, Math.max(MIN_ZOOM, pinchRef.current.zoom * scale)));
    } else if (dragRef.current.active && e.touches.length === 1) {
      const t = e.touches[0];
      const dx = t.clientX - dragRef.current.lastX;
      const dy = t.clientY - dragRef.current.lastY;
      dragRef.current.lastX = t.clientX;
      dragRef.current.lastY = t.clientY;
      const rect = e.currentTarget.getBoundingClientRect();
      setPan((p) => ({
        x: p.x + (dx / rect.width) * W,
        y: p.y + (dy / rect.height) * H,
      }));
    }
  }, []);

  const onTouchEnd = useCallback(() => {
    dragRef.current.active = false;
    pinchRef.current.active = false;
  }, []);

  const resetView = () => {
    setZoom(1);
    setPan({ x: 0, y: 0 });
    setFilter(null);
    setSelected(null);
  };

  const showTip = (e: React.MouseEvent, p: MapPoint) => {
    if (isMobile) return;
    const el = wrapRef.current;
    if (!el) return;
    const r = el.getBoundingClientRect();
    setTipPos({ x: e.clientX - r.left, y: e.clientY - r.top });
    setHover(p);
  };

  if (!layout) {
    return (
      <p className="p-8 text-sm text-muted text-center leading-relaxed">
        No map data yet. An admin needs to run the UMAP rebuild once (see README).
      </p>
    );
  }

  const { sx, sy } = layout;
  const books = Object.keys(BOOK_COLORS);
  const dotRadius = isMobile ? 3.8 : 2.2;
  const thomasDotRadius = isMobile ? 5.5 : 3.5;

  return (
    <div ref={wrapRef} className="space-y-3">
      {/* Legend + controls */}
      <div className="flex flex-wrap items-center justify-between gap-x-3 gap-y-2">
        <div className="flex flex-wrap gap-x-3 gap-y-1.5 text-xs">
          {books.map((b) => {
            const active = !filter || filter === b;
            return (
              <button
                key={b}
                type="button"
                onClick={() => setFilter((f) => (f === b ? null : b))}
                className="flex items-center gap-1.5 py-0.5 transition-opacity"
                style={{ opacity: active ? 1 : 0.35 }}
              >
                <span
                  className="inline-block w-3 h-3 rounded-full"
                  style={{ background: BOOK_COLORS[b].fill }}
                />
                <span className="text-muted">{b}</span>
              </button>
            );
          })}
        </div>
        <button
          type="button"
          onClick={resetView}
          className="rounded border border-ink/15 px-3 py-1.5 text-xs text-muted hover:text-ink hover:bg-white/60"
        >
          Reset
        </button>
      </div>

      {/* SVG galaxy */}
      <div className="relative">
        <svg
          ref={svgRef}
          viewBox={`0 0 ${W} ${H}`}
          className="w-full select-none cursor-grab active:cursor-grabbing rounded-lg border border-ink/5"
          style={{
            background: "radial-gradient(ellipse at center, #1a1f2e 0%, #0d1017 100%)",
            height: "min(65vh, 520px)",
            touchAction: "none",
          }}
          onWheel={onWheel}
          onPointerDown={onPointerDown}
          onPointerMove={onPointerMove}
          onPointerUp={onPointerUp}
          onPointerLeave={() => { dragRef.current.active = false; }}
          onTouchStart={onTouchStart}
          onTouchMove={onTouchMove}
          onTouchEnd={onTouchEnd}
          role="img"
          aria-label="Galaxy map of Gospel passages and Thomas sayings"
        >
          <defs>
            {books.map((b) => (
              <radialGradient key={b} id={`glow-${b}`}>
                <stop offset="0%" stopColor={BOOK_COLORS[b].glow} stopOpacity="0.6" />
                <stop offset="100%" stopColor={BOOK_COLORS[b].glow} stopOpacity="0" />
              </radialGradient>
            ))}
          </defs>

          <g transform={`translate(${pan.x + W / 2} ${pan.y + H / 2}) scale(${zoom}) translate(${-W / 2} ${-H / 2})`}>
            {(filteredPoints as (MapPoint & { _dimmed?: boolean })[]).map((p) => {
              const cx = sx(p.x);
              const cy = H - sy(p.y);
              const isT = p.tradition === "thomas";
              const c = bookColor(p.book);
              const dimmed = (p as { _dimmed?: boolean })._dimmed;
              const isSelected = selected?.id === p.id;
              const r = isT ? thomasDotRadius : dotRadius;

              return (
                <g key={p.id} style={{ opacity: dimmed ? 0.12 : 1, transition: "opacity 0.3s" }}>
                  <circle cx={cx} cy={cy} r={r * 3} fill={`url(#glow-${p.book || ""})`} style={{ pointerEvents: "none" }} />
                  <circle
                    cx={cx}
                    cy={cy}
                    r={isSelected ? r * 1.6 : r}
                    fill={c.fill}
                    stroke={isSelected ? "#fff" : "none"}
                    strokeWidth={isSelected ? 0.8 : 0}
                    className="cursor-pointer"
                    style={{ transition: "r 0.15s, stroke-width 0.15s" }}
                    onClick={() => setSelected(p)}
                    onMouseEnter={(e) => showTip(e, p)}
                    onMouseMove={(e) => {
                      if (!hover) return;
                      const el = wrapRef.current;
                      if (!el) return;
                      const rect = el.getBoundingClientRect();
                      setTipPos({ x: e.clientX - rect.left, y: e.clientY - rect.top });
                    }}
                    onMouseLeave={() => setHover(null)}
                  />
                </g>
              );
            })}
          </g>
        </svg>

        {/* Desktop hover tooltip */}
        {hover && !isMobile && (
          <div
            className="pointer-events-none absolute z-20 max-w-xs rounded border border-white/10 bg-[#1a1f2e]/95 px-3 py-2 text-left text-xs shadow-lg backdrop-blur-sm"
            style={{
              left: Math.min(tipPos.x + 12, (wrapRef.current?.clientWidth ?? 400) - 260),
              top: Math.min(tipPos.y + 12, (wrapRef.current?.clientHeight ?? 400) - 80),
            }}
          >
            <p className="font-mono text-[11px] text-white/70">{hover.ref_label}</p>
            <p className="mt-0.5 text-[10px]" style={{ color: bookColor(hover.book).fill }}>
              {hover.book} · {hover.chunk_type}
            </p>
          </div>
        )}

        <p className="text-[11px] text-muted/50 mt-1 text-center">
          {isMobile ? "Pinch to zoom · drag to pan · tap a dot to read" : "Scroll to zoom · drag to pan · click a dot to read"}
        </p>
      </div>

      {/* Selected passage reading panel */}
      {selected && (
        <div className="rounded border border-ink/10 bg-white/60 p-4 sm:p-5 space-y-2">
          <div className="flex items-start justify-between gap-3">
            <div className="min-w-0">
              <p className="text-xs uppercase tracking-widest text-muted">
                {selected.tradition === "thomas" ? "Gospel of Thomas (noncanonical)" : selected.book}
              </p>
              <p className="text-sm text-muted mt-0.5">{selected.ref_label}</p>
            </div>
            <button
              type="button"
              onClick={() => setSelected(null)}
              className="text-muted hover:text-ink text-lg leading-none shrink-0 p-1 -m-1"
              aria-label="Close"
            >
              &times;
            </button>
          </div>
          <p className="font-serif leading-relaxed text-ink text-[15px] sm:text-base">{selected.preview}</p>
          <p className="text-xs text-muted">
            {selected.tradition === "canonical"
              ? "Published Bible translation \u2014 not written by AI."
              : "Published translation \u2014 not written by AI."}
          </p>
        </div>
      )}
    </div>
  );
}
