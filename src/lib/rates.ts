import type { Property, RateSignal, SignalProperty } from "@/lib/types";
import { levelFor } from "@/lib/intelligence";

/** A current rate this far below average (or more) raises a "Rate Alert". */
export const ALERT_THRESHOLD = 0.12; // 12% -> intelligence level 4+

/**
 * Compute the rate signal for a property: how the current prepaid rate compares
 * to its historical average, plus its intelligence level.
 */
export function computeSignal(current: number, avg: number): RateSignal {
  const delta = avg > 0 ? (current - avg) / avg : 0;
  const deltaPct = Math.round(delta * 100);
  const belowPct = Math.max(0, -deltaPct);
  return {
    delta,
    deltaPct,
    belowPct,
    isAlert: delta <= -ALERT_THRESHOLD,
    level: levelFor(belowPct),
  };
}

export function withSignal(property: Property): SignalProperty {
  return {
    ...property,
    signal: computeSignal(property.current_rate, property.avg_rate),
  };
}

export function withSignals(properties: Property[]): SignalProperty[] {
  return properties.map(withSignal);
}

/** Sort so the best deals (largest discount vs average) surface first. */
export function byBestDeal(a: SignalProperty, b: SignalProperty): number {
  return a.signal.delta - b.signal.delta;
}
