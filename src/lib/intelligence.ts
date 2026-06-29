// The five "intelligence levels" - a signal-tier classification layered on top
// of the raw rate delta. Level 5 is the rarest, deepest discount vs the
// historical average; level 1 is at or above market.

export interface IntelligenceLevel {
  level: number;
  label: string;
  short: string;
  description: string;
}

export const INTELLIGENCE_LEVELS: IntelligenceLevel[] = [
  {
    level: 5,
    label: "Exceptional",
    short: "L5",
    description: "20%+ below the historical average. A rare booking window.",
  },
  {
    level: 4,
    label: "Strong",
    short: "L4",
    description: "12-20% below average. A strong signal worth acting on.",
  },
  {
    level: 3,
    label: "Notable",
    short: "L3",
    description: "6-12% below average. Softening rates, worth watching.",
  },
  {
    level: 2,
    label: "Fair value",
    short: "L2",
    description: "2-6% below average. Around its usual price.",
  },
  {
    level: 1,
    label: "At market",
    short: "L1",
    description: "At or above the historical average. No edge today.",
  },
];

/** Map a "percent below average" figure to an intelligence level (1-5). */
export function levelFor(belowPct: number): number {
  if (belowPct >= 20) return 5;
  if (belowPct >= 12) return 4;
  if (belowPct >= 6) return 3;
  if (belowPct >= 2) return 2;
  return 1;
}

export function levelMeta(level: number): IntelligenceLevel {
  return (
    INTELLIGENCE_LEVELS.find((l) => l.level === level) ??
    INTELLIGENCE_LEVELS[INTELLIGENCE_LEVELS.length - 1]
  );
}
