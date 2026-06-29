import type {
  BrandStat,
  DestinationStat,
  ScatterPoint,
  SeasonRow,
  SignalProperty,
} from "@/lib/types";
import { BRANDS, seasonRow } from "@/lib/demo-data";

// Indicative FX to normalise rates to USD for cross-market comparison.
const FX: Record<string, number> = { USD: 1, EUR: 1.08, GBP: 1.27 };

export function toUsd(rate: number, currency: string): number {
  return Math.round(rate * (FX[currency] ?? 1));
}

function avg(values: number[]): number {
  if (values.length === 0) return 0;
  return values.reduce((a, b) => a + b, 0) / values.length;
}

/** Brand league table, sorted by average discount vs historical average. */
export function brandStats(properties: SignalProperty[]): BrandStat[] {
  return BRANDS.map((brand) => {
    const owned = properties.filter((p) => p.brand_id === brand.id);
    return {
      brand,
      count: owned.length,
      avgRateUsd: Math.round(
        avg(owned.map((p) => toUsd(p.current_rate, p.currency))),
      ),
      avgBelowPct: Math.round(avg(owned.map((p) => p.signal.belowPct))),
      alerts: owned.filter((p) => p.signal.isAlert).length,
    };
  })
    .filter((b) => b.count > 0)
    .sort((a, b) => b.avgBelowPct - a.avgBelowPct);
}

/** Destination analysis, sorted by average discount vs historical average. */
export function destinationStats(properties: SignalProperty[]): DestinationStat[] {
  const byDestination = new Map<string, SignalProperty[]>();
  for (const p of properties) {
    const list = byDestination.get(p.destination) ?? [];
    list.push(p);
    byDestination.set(p.destination, list);
  }

  return Array.from(byDestination.entries())
    .map(([destination, list]) => ({
      destination,
      country: list[0].country,
      count: list.length,
      avgRateUsd: Math.round(
        avg(list.map((p) => toUsd(p.current_rate, p.currency))),
      ),
      avgBelowPct: Math.round(avg(list.map((p) => p.signal.belowPct))),
      bestBelowPct: Math.max(...list.map((p) => p.signal.belowPct)),
    }))
    .sort((a, b) => b.avgBelowPct - a.avgBelowPct);
}

/** Rate (USD) vs signal scatter data. */
export function scatterPoints(properties: SignalProperty[]): ScatterPoint[] {
  return properties.map((p) => ({
    id: p.id,
    name: p.name,
    destination: p.destination,
    rateUsd: toUsd(p.current_rate, p.currency),
    belowPct: p.signal.belowPct,
    isAlert: p.signal.isAlert,
  }));
}

/** Seasonal rate-index heat map for the distinct destinations on offer. */
export function seasonRows(properties: SignalProperty[]): SeasonRow[] {
  const seen = new Set<string>();
  const rows: SeasonRow[] = [];
  for (const p of properties) {
    if (seen.has(p.destination)) continue;
    seen.add(p.destination);
    rows.push({ destination: p.destination, months: seasonRow(p.destination) });
  }
  return rows.sort((a, b) => a.destination.localeCompare(b.destination));
}

export const MONTH_LABELS = [
  "Jan",
  "Feb",
  "Mar",
  "Apr",
  "May",
  "Jun",
  "Jul",
  "Aug",
  "Sep",
  "Oct",
  "Nov",
  "Dec",
];
