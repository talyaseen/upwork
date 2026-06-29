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
  brand_id: string;
  tags: string[];
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
  /** intelligence level 1 (at market) - 5 (exceptional) */
  level: number;
}

export interface SignalProperty extends Property {
  signal: RateSignal;
}

// ---------------------------------------------------------------------------
//  Reference data
// ---------------------------------------------------------------------------

export interface Brand {
  id: string;
  name: string;
  origin: string;
  founded: number;
  description: string;
}

export type TagCategory = "Setting" | "Style" | "Experience";

export interface Tag {
  id: string;
  label: string;
  category: TagCategory;
}

// ---------------------------------------------------------------------------
//  Market intelligence (The View)
// ---------------------------------------------------------------------------

export interface BrandStat {
  brand: Brand;
  count: number;
  avgRateUsd: number;
  avgBelowPct: number;
  alerts: number;
}

export interface DestinationStat {
  destination: string;
  country: string;
  count: number;
  avgRateUsd: number;
  avgBelowPct: number;
  bestBelowPct: number;
}

export interface ScatterPoint {
  id: string;
  name: string;
  destination: string;
  rateUsd: number;
  belowPct: number;
  isAlert: boolean;
}

export interface SeasonRow {
  destination: string;
  months: number[]; // 12 monthly rate-index values (~0.7 - 1.3)
}

// ---------------------------------------------------------------------------
//  Loyalty (Reserve)
// ---------------------------------------------------------------------------

export interface LoyaltyTier {
  id: string;
  name: string;
  threshold: number; // credits required to reach this tier
  benefit: string;
}

export interface LoyaltyActivity {
  date: string;
  label: string;
  credits: number;
}

export interface LoyaltyAccount {
  member: string;
  tierId: string;
  credits: number;
  ytdNights: number;
  history: LoyaltyActivity[];
  perks: string[];
}

// ---------------------------------------------------------------------------
//  Rates & packages / booking
// ---------------------------------------------------------------------------

export interface RoomType {
  id: string;
  name: string;
  description: string;
  /** multiplier applied to the property's base nightly rate */
  multiplier: number;
  maxOccupancy: number;
  beds: string;
  sizeSqm: number;
  accent_from: string;
  accent_to: string;
}

export interface StayPackage {
  id: string;
  name: string;
  description: string;
  /** added per night */
  perNight: number;
  /** added once per stay */
  flat: number;
}

export interface QuoteNight {
  date: string; // ISO date of the night
  weekend: boolean;
  rate: number;
}

export interface StayQuote {
  nights: QuoteNight[];
  nightsCount: number;
  roomSubtotal: number;
  packageTotal: number;
  taxes: number;
  fees: number;
  grandTotal: number;
  currency: string;
}
