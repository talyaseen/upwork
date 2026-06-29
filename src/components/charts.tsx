"use client";

import { motion } from "framer-motion";
import type {
  BrandStat,
  DestinationStat,
  ScatterPoint,
  SeasonRow,
} from "@/lib/types";
import { levelMeta } from "@/lib/intelligence";

const EASE = [0.22, 1, 0.36, 1] as const;

// ---------------------------------------------------------------------------
//  Brand league table - animated horizontal bars
// ---------------------------------------------------------------------------
export function BrandLeagueTable({ stats }: { stats: BrandStat[] }) {
  const max = Math.max(1, ...stats.map((s) => s.avgBelowPct));
  return (
    <div className="space-y-2.5">
      {stats.map((s, i) => (
        <motion.div
          key={s.brand.id}
          initial={{ opacity: 0, x: -12 }}
          whileInView={{ opacity: 1, x: 0 }}
          viewport={{ once: true, margin: "-40px" }}
          transition={{ duration: 0.5, delay: i * 0.05, ease: EASE }}
          className="grid grid-cols-[1.5rem_1fr_auto] items-center gap-3 rounded-xl border border-white/[0.06] bg-ink-800/50 px-4 py-3"
        >
          <span className="font-display text-white/30">{i + 1}</span>
          <div className="min-w-0">
            <div className="flex items-baseline gap-2">
              <span className="truncate text-white">{s.brand.name}</span>
              <span className="shrink-0 text-xs text-white/35">
                {s.count} {s.count === 1 ? "stay" : "stays"}
              </span>
            </div>
            <div className="mt-2 h-1.5 w-full overflow-hidden rounded-full bg-white/[0.05]">
              <motion.div
                initial={{ width: 0 }}
                whileInView={{ width: `${(s.avgBelowPct / max) * 100}%` }}
                viewport={{ once: true }}
                transition={{ duration: 0.9, delay: 0.1 + i * 0.05, ease: EASE }}
                className="h-full rounded-full bg-gradient-to-r from-gilt-deep to-gilt-soft"
              />
            </div>
          </div>
          <div className="text-right">
            <div className="font-display text-gilt-soft">-{s.avgBelowPct}%</div>
            <div className="text-[11px] text-white/35">
              ~${s.avgRateUsd.toLocaleString("en-US")}
            </div>
          </div>
        </motion.div>
      ))}
    </div>
  );
}

// ---------------------------------------------------------------------------
//  Destination analysis - tile grid with mini bars
// ---------------------------------------------------------------------------
export function DestinationAnalysis({ stats }: { stats: DestinationStat[] }) {
  const max = Math.max(1, ...stats.map((s) => s.avgBelowPct));
  return (
    <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
      {stats.map((s, i) => (
        <motion.div
          key={s.destination}
          initial={{ opacity: 0, y: 14 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true, margin: "-40px" }}
          transition={{ duration: 0.5, delay: i * 0.04, ease: EASE }}
          className="rounded-xl border border-white/[0.06] bg-ink-800/50 p-4"
        >
          <div className="flex items-baseline justify-between gap-2">
            <div className="min-w-0">
              <p className="truncate text-white">{s.destination}</p>
              <p className="truncate text-xs text-white/35">{s.country}</p>
            </div>
            <span className="shrink-0 font-display text-gilt-soft">
              -{s.avgBelowPct}%
            </span>
          </div>
          <div className="mt-3 h-1.5 w-full overflow-hidden rounded-full bg-white/[0.05]">
            <motion.div
              initial={{ width: 0 }}
              whileInView={{ width: `${(s.avgBelowPct / max) * 100}%` }}
              viewport={{ once: true }}
              transition={{ duration: 0.9, delay: 0.1 + i * 0.04, ease: EASE }}
              className="h-full rounded-full bg-gradient-to-r from-gilt-deep to-gilt-soft"
            />
          </div>
          <div className="mt-2.5 flex items-center justify-between text-[11px] text-white/35">
            <span>
              {s.count} {s.count === 1 ? "stay" : "stays"}
            </span>
            <span>avg ~${s.avgRateUsd.toLocaleString("en-US")}</span>
          </div>
        </motion.div>
      ))}
    </div>
  );
}

// ---------------------------------------------------------------------------
//  Seasonal heat map
// ---------------------------------------------------------------------------
export function SeasonHeatmap({
  rows,
  months,
}: {
  rows: SeasonRow[];
  months: string[];
}) {
  const all = rows.flatMap((r) => r.months);
  const min = Math.min(...all);
  const max = Math.max(...all);

  return (
    <div className="overflow-x-auto pb-1">
      <div className="min-w-[640px]">
        <div className="grid grid-cols-[7rem_repeat(12,1fr)] gap-1 text-[10px] text-white/40">
          <span />
          {months.map((m) => (
            <span key={m} className="text-center">
              {m}
            </span>
          ))}
        </div>
        {rows.map((row, ri) => (
          <div
            key={row.destination}
            className="mt-1 grid grid-cols-[7rem_repeat(12,1fr)] items-center gap-1"
          >
            <span className="truncate pr-2 text-xs text-white/60">
              {row.destination}
            </span>
            {row.months.map((v, mi) => {
              const t = max > min ? (v - min) / (max - min) : 0.5;
              return (
                <motion.div
                  key={mi}
                  initial={{ opacity: 0, scale: 0.6 }}
                  whileInView={{ opacity: 1, scale: 1 }}
                  viewport={{ once: true }}
                  transition={{ duration: 0.4, delay: (ri * 12 + mi) * 0.004 }}
                  title={`${row.destination}, ${months[mi]}: ${v.toFixed(2)}x average`}
                  className="h-7 rounded-[5px]"
                  style={{ backgroundColor: `rgba(200,162,90,${0.1 + t * 0.82})` }}
                />
              );
            })}
          </div>
        ))}
        <div className="mt-4 flex items-center gap-2 text-[10px] text-white/35">
          <span>Off-peak</span>
          <span
            className="h-2 w-28 rounded-full"
            style={{
              background:
                "linear-gradient(90deg, rgba(200,162,90,0.12), rgba(200,162,90,0.92))",
            }}
          />
          <span>Peak season</span>
        </div>
      </div>
    </div>
  );
}

// ---------------------------------------------------------------------------
//  Rate vs signal scatter plot
// ---------------------------------------------------------------------------
export function RateSignalScatter({ points }: { points: ScatterPoint[] }) {
  const W = 680;
  const H = 380;
  const padL = 48;
  const padB = 44;
  const padT = 20;
  const padR = 20;

  const xs = points.map((p) => p.rateUsd);
  const ys = points.map((p) => p.belowPct);
  const xMin = Math.min(...xs) * 0.9;
  const xMax = Math.max(...xs) * 1.05;
  const yMax = Math.max(...ys, 10) * 1.1;

  const sx = (v: number) =>
    padL + ((v - xMin) / (xMax - xMin)) * (W - padL - padR);
  const sy = (v: number) => H - padB - (v / yMax) * (H - padB - padT);

  const yTicks = [0, Math.round(yMax / 2), Math.round(yMax)];
  const xTicks = [
    Math.round(xMin),
    Math.round((xMin + xMax) / 2),
    Math.round(xMax),
  ];

  return (
    <svg
      viewBox={`0 0 ${W} ${H}`}
      width="100%"
      className="h-auto w-full"
      role="img"
      aria-label="Rate versus signal scatter plot"
    >
      {/* gridlines */}
      {yTicks.map((t) => (
        <g key={`y${t}`}>
          <line
            x1={padL}
            y1={sy(t)}
            x2={W - padR}
            y2={sy(t)}
            stroke="rgba(255,255,255,0.06)"
          />
          <text x={8} y={sy(t) + 4} fill="rgba(255,255,255,0.4)" fontSize="11">
            {t}%
          </text>
        </g>
      ))}
      {xTicks.map((t) => (
        <text
          key={`x${t}`}
          x={sx(t)}
          y={H - 16}
          fill="rgba(255,255,255,0.4)"
          fontSize="11"
          textAnchor="middle"
        >
          ${t.toLocaleString("en-US")}
        </text>
      ))}
      <text
        x={padL}
        y={14}
        fill="rgba(255,255,255,0.45)"
        fontSize="11"
      >
        Signal (% below avg)
      </text>
      <text
        x={W - padR}
        y={H - 16}
        fill="rgba(255,255,255,0.45)"
        fontSize="11"
        textAnchor="end"
      >
        Rate (USD / night)
      </text>

      {/* points */}
      {points.map((p, i) => (
        <motion.circle
          key={p.id}
          cx={sx(p.rateUsd)}
          cy={sy(p.belowPct)}
          r={p.isAlert ? 7 : 5.5}
          fill={p.isAlert ? "#d9bd86" : "rgba(255,255,255,0.35)"}
          stroke={p.isAlert ? "rgba(200,162,90,0.4)" : "transparent"}
          strokeWidth={p.isAlert ? 6 : 0}
          initial={{ scale: 0, opacity: 0 }}
          whileInView={{ scale: 1, opacity: 1 }}
          viewport={{ once: true }}
          transition={{ duration: 0.5, delay: 0.1 + i * 0.05, ease: EASE }}
        >
          <title>{`${p.name} - $${p.rateUsd.toLocaleString("en-US")}, ${p.belowPct}% below avg`}</title>
        </motion.circle>
      ))}
    </svg>
  );
}

// ---------------------------------------------------------------------------
//  Signal distribution - properties per intelligence level
// ---------------------------------------------------------------------------
export function SignalDistribution({
  dist,
}: {
  dist: { level: number; count: number }[];
}) {
  const max = Math.max(1, ...dist.map((d) => d.count));
  return (
    <div className="space-y-3">
      {dist.map((d, i) => {
        const meta = levelMeta(d.level);
        return (
          <div key={d.level} className="flex items-center gap-3">
            <span className="w-24 shrink-0 text-xs text-white/55">
              <span className="font-display text-gilt-soft">{meta.short}</span>{" "}
              {meta.label}
            </span>
            <div className="h-2 flex-1 overflow-hidden rounded-full bg-white/[0.05]">
              <motion.div
                initial={{ width: 0 }}
                whileInView={{ width: `${(d.count / max) * 100}%` }}
                viewport={{ once: true }}
                transition={{ duration: 0.9, delay: i * 0.06, ease: EASE }}
                className="h-full rounded-full bg-gradient-to-r from-gilt-deep to-gilt-soft"
              />
            </div>
            <span className="w-6 shrink-0 text-right text-sm text-white/70">
              {d.count}
            </span>
          </div>
        );
      })}
    </div>
  );
}

// ---------------------------------------------------------------------------
//  Market trend line (animated draw)
// ---------------------------------------------------------------------------
export function MarketTrendLine({
  values,
  labels,
}: {
  values: number[];
  labels: string[];
}) {
  const W = 720;
  const H = 280;
  const padL = 54;
  const padB = 34;
  const padT = 18;
  const padR = 14;

  const min = Math.min(...values);
  const max = Math.max(...values);
  const sx = (i: number) =>
    padL + (i / Math.max(1, values.length - 1)) * (W - padL - padR);
  const sy = (v: number) =>
    H - padB - ((v - min) / (max - min || 1)) * (H - padB - padT);

  const line = values
    .map((v, i) => `${i === 0 ? "M" : "L"}${sx(i).toFixed(1)},${sy(v).toFixed(1)}`)
    .join(" ");
  const area = `${line} L${sx(values.length - 1).toFixed(1)},${H - padB} L${sx(0).toFixed(1)},${H - padB} Z`;
  const yTicks = [min, Math.round((min + max) / 2), max];

  return (
    <svg
      viewBox={`0 0 ${W} ${H}`}
      width="100%"
      className="h-auto w-full"
      role="img"
      aria-label="Market average rate trend"
    >
      <defs>
        <linearGradient id="trend-fill" x1="0" y1="0" x2="0" y2="1">
          <stop offset="0%" stopColor="#c8a25a" stopOpacity="0.25" />
          <stop offset="100%" stopColor="#c8a25a" stopOpacity="0" />
        </linearGradient>
      </defs>
      {yTicks.map((t) => (
        <g key={t}>
          <line
            x1={padL}
            y1={sy(t)}
            x2={W - padR}
            y2={sy(t)}
            stroke="rgba(255,255,255,0.06)"
          />
          <text x={8} y={sy(t) + 4} fill="rgba(255,255,255,0.4)" fontSize="11">
            {"$" + t.toLocaleString("en-US")}
          </text>
        </g>
      ))}
      {labels.map((l, i) =>
        i % 2 === 0 || i === labels.length - 1 ? (
          <text
            key={l}
            x={sx(i)}
            y={H - 12}
            fill="rgba(255,255,255,0.4)"
            fontSize="10"
            textAnchor="middle"
          >
            {l}
          </text>
        ) : null,
      )}
      <motion.path
        d={area}
        fill="url(#trend-fill)"
        initial={{ opacity: 0 }}
        whileInView={{ opacity: 1 }}
        viewport={{ once: true }}
        transition={{ duration: 0.8, delay: 0.6 }}
      />
      <motion.path
        d={line}
        fill="none"
        stroke="#d9bd86"
        strokeWidth="2.5"
        strokeLinecap="round"
        strokeLinejoin="round"
        initial={{ pathLength: 0 }}
        whileInView={{ pathLength: 1 }}
        viewport={{ once: true }}
        transition={{ duration: 1.4, ease: EASE }}
      />
      {values.map((v, i) => (
        <motion.circle
          key={labels[i] ?? i}
          cx={sx(i)}
          cy={sy(v)}
          r="3"
          fill="#d9bd86"
          initial={{ scale: 0 }}
          whileInView={{ scale: 1 }}
          viewport={{ once: true }}
          transition={{ delay: 0.8 + i * 0.05, duration: 0.3 }}
        />
      ))}
    </svg>
  );
}
