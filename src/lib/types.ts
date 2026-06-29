// Domain types shared across the app. These mirror the Supabase schema in
// supabase/schema.sql so the data layer can map rows 1:1.

export interface Property {
  id: string;
  name: string;
  destination: string;
  country: string;
  description: string;
  star_rating: number;
  current_rate: number;
  avg_rate: number;
  currency: string;
  accent_from: string;
  accent_to: string;
  image_url: string;
}

export interface RatePoint {
  captured_on: string; // ISO date (YYYY-MM-DD)
  rate: number;
}

export interface PropertyWithHistory extends Property {
  history: RatePoint[];
}

// A property enriched with its computed rate signal, ready for the UI.
export interface RateSignal {
  /** signed fractional delta of current vs average (negative = cheaper) */
  delta: number;
  /** integer percentage delta, e.g. -18 */
  deltaPct: number;
  /** absolute percentage below average when cheaper, e.g. 18 */
  belowPct: number;
  /** true when current rate is meaningfully below average */
  isAlert: boolean;
}

export interface SignalProperty extends Property {
  signal: RateSignal;
}
