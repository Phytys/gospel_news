"use client";

import { useCallback, useMemo, useRef, useState } from "react";

export type MapPoint = {
  id: string;
  x: number;
  y: number;
  tradition: string;
  ref_label?: string;
  preview?: string;
  cluster_id?: string | null;
  cluster_label?: string | null;
};

/** Stable hue from backend cluster id (layout region), not decoration. */
function regionHue(clusterId: string | null | undefined): number {
  if (clusterId == null || clusterId === "") return 210;
  const n = parseInt(clusterId, 10);
  if (Number.isNaN(n)) return 210;
  return (n * 41) % 360;
}

const W = 800;
const H = 400;
const PAD = 24;
const MIN_ZOOM = 0.2;
const MAX_ZOOM = 8;

export function MapExplorer({ points }: { points: MapPoint[] }) {
  const wrapRef = useRef<HTMLDivElement>(null);
  const [zoom, setZoom] = useState(1);
  const [pan, setPan] = useState({ x: 0, y: 0 });
  const dragRef = useRef<{ active: boolean; lastX: number; lastY: number }>({
    active: false,
    lastX: 0,
    lastY: 0,
  });

  const [hover, setHover] = useState<MapPoint | null>(null);
  const [tipPos, setTipPos] = useState({ x: 0, y: 0 });

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
    return { sx, sy, minX, maxX, minY, maxY };
  }, [points]);

  const onWheel = useCallback((e: React.WheelEvent<SVGSVGElement>) => {
    e.preventDefault();
    const factor = e.deltaY > 0 ? 0.9 : 1.11;
    setZoom((z0) => Math.min(MAX_ZOOM, Math.max(MIN_ZOOM, z0 * factor)));
  }, []);

  const onPointerDown = (e: React.PointerEvent<SVGSVGElement>) => {
    if (e.button !== 0) return;
    (e.target as SVGSVGElement).setPointerCapture(e.pointerId);
    dragRef.current = { active: true, lastX: e.clientX, lastY: e.clientY };
  };

  const onPointerMove = (e: React.PointerEvent<SVGSVGElement>) => {
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
    dragRef.current.active = false;
    try {
      (e.target as SVGSVGElement).releasePointerCapture(e.pointerId);
    } catch {
      /* ignore */
    }
  };

  const resetView = () => {
    setZoom(1);
    setPan({ x: 0, y: 0 });
  };

  const showTip = (e: React.MouseEvent, p: MapPoint) => {
    const el = wrapRef.current;
    if (!el) return;
    const r = el.getBoundingClientRect();
    setTipPos({ x: e.clientX - r.left, y: e.clientY - r.top });
    setHover(p);
  };

  const moveTip = (e: React.MouseEvent) => {
    if (!hover) return;
    const el = wrapRef.current;
    if (!el) return;
    const r = el.getBoundingClientRect();
    setTipPos({ x: e.clientX - r.left, y: e.clientY - r.top });
  };

  if (!layout) {
    return (
      <p className="p-8 text-sm text-muted text-center leading-relaxed">
        Nothing to show here yet—the passage layout may still be preparing.
      </p>
    );
  }

  const { sx, sy } = layout;

  return (
    <div ref={wrapRef} className="relative">
      <div className="flex flex-wrap items-center justify-between gap-2 mb-2 text-xs text-muted">
        <span>
          Scroll to zoom · drag to pan · hover a dot for reference + preview
        </span>
        <button
          type="button"
          onClick={resetView}
          className="rounded border border-ink/15 px-2 py-1 text-ink hover:bg-white/60"
        >
          Reset view
        </button>
      </div>

      <svg
        viewBox={`0 0 ${W} ${H}`}
        className="h-[420px] w-full touch-none select-none cursor-grab active:cursor-grabbing bg-white/50 rounded border border-ink/10"
        onWheel={onWheel}
        onPointerDown={onPointerDown}
        onPointerMove={onPointerMove}
        onPointerUp={onPointerUp}
        onPointerLeave={() => {
          dragRef.current.active = false;
        }}
        role="img"
        aria-label="Semantic map: passage positions from embeddings; colors are layout regions"
      >
        <g transform={`translate(${pan.x + W / 2} ${pan.y + H / 2}) scale(${zoom}) translate(${-W / 2} ${-H / 2})`}>
          {points.map((p) => {
            const cx = sx(p.x);
            const cy = H - sy(p.y);
            const isT = p.tradition === "thomas";
            const h = regionHue(p.cluster_id);
            const fill = isT
              ? `hsl(${h} 52% 38%)`
              : `hsl(${h} 28% 52%)`;
            const stroke = isT ? `hsl(${h} 60% 28%)` : `hsl(${h} 22% 42%)`;
            return (
              <circle
                key={p.id}
                cx={cx}
                cy={cy}
                r={isT ? 3.2 : 2.2}
                className="stroke-[0.45] hover:opacity-90"
                style={{ fill, stroke, transition: "fill 0.12s ease, stroke 0.12s ease" }}
                onMouseEnter={(e) => showTip(e, p)}
                onMouseMove={moveTip}
                onMouseLeave={() => setHover(null)}
              />
            );
          })}
        </g>
      </svg>

      {hover && (
        <div
          className="pointer-events-none absolute z-20 max-w-sm rounded border border-ink/15 bg-paper/95 px-3 py-2 text-left text-xs shadow-lg backdrop-blur-sm"
          style={{
            left: Math.min(tipPos.x + 12, (wrapRef.current?.clientWidth ?? 400) - 280),
            top: Math.min(tipPos.y + 12, (wrapRef.current?.clientHeight ?? 400) - 120),
          }}
        >
          <p className="font-mono text-[11px] text-muted">{hover.ref_label || hover.id.slice(0, 8)}</p>
          {hover.cluster_label && (
            <p className="text-[10px] text-muted mt-0.5">Layout region · {hover.cluster_label}</p>
          )}
          <p className="mt-1 leading-snug text-ink line-clamp-6">{hover.preview || "—"}</p>
          <p className="mt-1 text-[10px] text-muted capitalize">{hover.tradition}</p>
        </div>
      )}
    </div>
  );
}
