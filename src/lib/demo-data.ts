import type {
  Brand,
  LoyaltyAccount,
  LoyaltyTier,
  Property,
  PropertyWithHistory,
  RatePoint,
  Tag,
} from "@/lib/types";
import { unsplash } from "@/lib/images";

// -----------------------------------------------------------------------------
// Bundled illustrative sample data. The hotels, brands and destinations are
// real; the rates, rate history and loyalty figures are illustrative sample
// data for demonstration only, not live or quoted prices. The same dataset is
// reflected in supabase/schema.sql + seed.sql so the app renders identically
// with or without a Supabase backend (no network calls at build time).
// -----------------------------------------------------------------------------

// --- Brands (hotel groups) ---------------------------------------------------
export const BRANDS: Brand[] = [
  { id: "aman", name: "Aman", origin: "Switzerland", founded: 1988, description: "Pioneering intimate, design-led sanctuaries in extraordinary settings." },
  { id: "belmond", name: "Belmond", origin: "United Kingdom", founded: 1976, description: "A storied collection of legendary hotels, trains and journeys." },
  { id: "four-seasons", name: "Four Seasons", origin: "Canada", founded: 1960, description: "Defining modern luxury through intuitive, personalised service." },
  { id: "mandarin-oriental", name: "Mandarin Oriental", origin: "Hong Kong", founded: 1963, description: "Oriental heritage and award-winning spas in landmark city hotels." },
  { id: "rosewood", name: "Rosewood", origin: "United States", founded: 1979, description: "A Sense of Place philosophy rooted in each destination's culture." },
  { id: "jumeirah", name: "Jumeirah", origin: "United Arab Emirates", founded: 1997, description: "Bold, iconic architecture and lavish Arabian hospitality." },
  { id: "singita", name: "Singita", origin: "South Africa", founded: 1993, description: "Conservation-led safari lodges across Africa's great wildernesses." },
  { id: "maybourne", name: "Maybourne", origin: "United Kingdom", founded: 1812, description: "London's grande dame hotels, the byword for British luxury." },
  { id: "raffles", name: "Raffles", origin: "Singapore", founded: 1887, description: "Colonial-era grandeur and legendary, gracious service." },
];

// --- Experience tags (thematic) ---------------------------------------------
export const TAGS: Tag[] = [
  { id: "beachfront", label: "Beachfront", category: "Setting" },
  { id: "overwater", label: "Overwater", category: "Setting" },
  { id: "island", label: "Island", category: "Setting" },
  { id: "lakeside", label: "Lakeside", category: "Setting" },
  { id: "clifftop", label: "Clifftop", category: "Setting" },
  { id: "urban", label: "Urban", category: "Setting" },
  { id: "safari", label: "Safari", category: "Setting" },
  { id: "waterfront", label: "Waterfront", category: "Setting" },
  { id: "palace", label: "Palace", category: "Style" },
  { id: "design-led", label: "Design-Led", category: "Style" },
  { id: "heritage", label: "Heritage", category: "Style" },
  { id: "contemporary", label: "Contemporary", category: "Style" },
  { id: "minimalist", label: "Minimalist", category: "Style" },
  { id: "art-deco", label: "Art Deco", category: "Style" },
  { id: "honeymoon", label: "Honeymoon", category: "Experience" },
  { id: "wellness", label: "Wellness", category: "Experience" },
  { id: "culinary", label: "Culinary", category: "Experience" },
  { id: "family", label: "Family", category: "Experience" },
  { id: "adventure", label: "Adventure", category: "Experience" },
  { id: "romance", label: "Romance", category: "Experience" },
];

export function tagLabel(id: string): string {
  return TAGS.find((t) => t.id === id)?.label ?? id;
}

// --- Properties --------------------------------------------------------------
export const DEMO_PROPERTIES: Property[] = [
  {
    id: "aman-tokyo",
    name: "Aman Tokyo",
    destination: "Tokyo",
    country: "Japan",
    description:
      "Urban sanctuary on the upper floors of Otemachi Tower, with onsen baths and city-wide views.",
    star_rating: 5,
    current_rate: 1130,
    avg_rate: 1320,
    currency: "USD",
    accent_from: "#1f2350",
    accent_to: "#4a2d52",
    image_url: unsplash("1540959733332-eab4deabeeaf"),
    brand_id: "aman",
    tags: ["urban", "minimalist", "design-led", "wellness"],
  },
  {
    id: "aman-venice",
    name: "Aman Venice",
    destination: "Venice",
    country: "Italy",
    description:
      "A sixteenth-century palazzo on the Grand Canal, with frescoed salons and a secret garden.",
    star_rating: 5,
    current_rate: 1480,
    avg_rate: 1850,
    currency: "EUR",
    accent_from: "#2a2440",
    accent_to: "#6b4a6e",
    image_url: unsplash("1514890547357-a9ee288728e0"),
    brand_id: "aman",
    tags: ["waterfront", "heritage", "design-led", "romance", "culinary"],
  },
  {
    id: "belmond-caruso",
    name: "Belmond Hotel Caruso",
    destination: "Amalfi Coast",
    country: "Italy",
    description:
      "An eleventh-century palazzo above Ravello, with a cliff-edge infinity pool over the Tyrrhenian Sea.",
    star_rating: 5,
    current_rate: 1490,
    avg_rate: 1520,
    currency: "EUR",
    accent_from: "#0f3b34",
    accent_to: "#3f7d5a",
    image_url: unsplash("1533104816931-20fa691ff6ca"),
    brand_id: "belmond",
    tags: ["clifftop", "heritage", "romance", "culinary", "honeymoon"],
  },
  {
    id: "belmond-cipriani",
    name: "Belmond Hotel Cipriani",
    destination: "Venice",
    country: "Italy",
    description:
      "A serene island retreat moments from St Mark's Square, with a saltwater Olympic pool.",
    star_rating: 5,
    current_rate: 1510,
    avg_rate: 1780,
    currency: "EUR",
    accent_from: "#123040",
    accent_to: "#356b7a",
    image_url: unsplash("1523906834658-6e24ef2386f9"),
    brand_id: "belmond",
    tags: ["waterfront", "heritage", "romance", "culinary"],
  },
  {
    id: "four-seasons-bora-bora",
    name: "Four Seasons Resort Bora Bora",
    destination: "Bora Bora",
    country: "French Polynesia",
    description:
      "Overwater bungalows above a turquoise lagoon, framed by the silhouette of Mount Otemanu.",
    star_rating: 5,
    current_rate: 1820,
    avg_rate: 2300,
    currency: "USD",
    accent_from: "#0a4f5c",
    accent_to: "#2aa7a0",
    image_url: unsplash("1518391846015-55a9cc003b25"),
    brand_id: "four-seasons",
    tags: ["overwater", "island", "beachfront", "honeymoon", "romance"],
  },
  {
    id: "four-seasons-george-v",
    name: "Four Seasons George V",
    destination: "Paris",
    country: "France",
    description:
      "A 1928 Art Deco landmark off the Champs-Elysees, with Michelin-starred dining and rooftop Eiffel views.",
    star_rating: 5,
    current_rate: 1830,
    avg_rate: 1900,
    currency: "EUR",
    accent_from: "#2c2418",
    accent_to: "#6e5a38",
    image_url: unsplash("1502602898657-3e91760cbb34"),
    brand_id: "four-seasons",
    tags: ["urban", "palace", "heritage", "culinary"],
  },
  {
    id: "mandarin-oriental-bangkok",
    name: "Mandarin Oriental Bangkok",
    destination: "Bangkok",
    country: "Thailand",
    description:
      "A riverside legend on the Chao Phraya, host to writers and royalty since 1876.",
    star_rating: 5,
    current_rate: 690,
    avg_rate: 780,
    currency: "USD",
    accent_from: "#2a1830",
    accent_to: "#7a3f5a",
    image_url: unsplash("1563492065599-3520f775eeed"),
    brand_id: "mandarin-oriental",
    tags: ["urban", "waterfront", "heritage", "wellness", "culinary"],
  },
  {
    id: "rosewood-hong-kong",
    name: "Rosewood Hong Kong",
    destination: "Hong Kong",
    country: "China",
    description:
      "A vertical estate on the Kowloon waterfront with sweeping Victoria Harbour views.",
    star_rating: 5,
    current_rate: 740,
    avg_rate: 920,
    currency: "USD",
    accent_from: "#1a2433",
    accent_to: "#41597a",
    image_url: unsplash("1536599018102-9f803c140fc1"),
    brand_id: "rosewood",
    tags: ["urban", "contemporary", "design-led", "wellness"],
  },
  {
    id: "burj-al-arab",
    name: "Burj Al Arab Jumeirah",
    destination: "Dubai",
    country: "United Arab Emirates",
    description:
      "The sail-shaped icon of Jumeirah Beach, defined by gold-leaf suites and Arabian opulence.",
    star_rating: 5,
    current_rate: 2100,
    avg_rate: 2750,
    currency: "USD",
    accent_from: "#0b2a4a",
    accent_to: "#1d6fa5",
    image_url: unsplash("1512453979798-5ea266f8880c"),
    brand_id: "jumeirah",
    tags: ["beachfront", "urban", "contemporary", "family"],
  },
  {
    id: "singita-sasakwa",
    name: "Singita Sasakwa Lodge",
    destination: "Serengeti",
    country: "Tanzania",
    description:
      "An Edwardian-style safari lodge on a private hill, overlooking the Serengeti plains.",
    star_rating: 5,
    current_rate: 2460,
    avg_rate: 2400,
    currency: "USD",
    accent_from: "#3a2a12",
    accent_to: "#9a6b2f",
    image_url: unsplash("1516026672322-bc52d61a55d5"),
    brand_id: "singita",
    tags: ["safari", "adventure", "wellness", "family"],
  },
  {
    id: "claridges-london",
    name: "Claridge's",
    destination: "London",
    country: "United Kingdom",
    description:
      "Art Deco grandeur in the heart of Mayfair, a byword for understated British luxury.",
    star_rating: 5,
    current_rate: 815,
    avg_rate: 950,
    currency: "GBP",
    accent_from: "#26282b",
    accent_to: "#4a4f57",
    image_url: unsplash("1513635269975-59663e0ac1ad"),
    brand_id: "maybourne",
    tags: ["urban", "art-deco", "heritage", "palace"],
  },
  {
    id: "raffles-singapore",
    name: "Raffles Singapore",
    destination: "Singapore",
    country: "Singapore",
    description:
      "A restored colonial icon of arcades and suites, birthplace of the Singapore Sling since 1887.",
    star_rating: 5,
    current_rate: 1010,
    avg_rate: 1080,
    currency: "USD",
    accent_from: "#173a2f",
    accent_to: "#3f7d5e",
    image_url: unsplash("1525625293386-3f8f99389edd"),
    brand_id: "raffles",
    tags: ["urban", "heritage", "palace", "romance"],
  },
];

// Nine weekly rate captures per property; the final point is "today" and equals
// the property's current_rate.
const DEMO_RATES: Record<string, number[]> = {
  "aman-tokyo": [1345, 1280, 1385, 1320, 1265, 1360, 1305, 1335, 1130],
  "aman-venice": [1885, 1795, 1945, 1850, 1775, 1905, 1830, 1870, 1480],
  "belmond-caruso": [1550, 1475, 1595, 1520, 1460, 1565, 1505, 1535, 1490],
  "belmond-cipriani": [1815, 1725, 1870, 1780, 1710, 1835, 1760, 1800, 1510],
  "four-seasons-bora-bora": [2345, 2230, 2415, 2300, 2210, 2370, 2275, 2325, 1820],
  "four-seasons-george-v": [1940, 1845, 1995, 1900, 1825, 1955, 1880, 1920, 1830],
  "mandarin-oriental-bangkok": [795, 755, 820, 780, 750, 805, 770, 790, 690],
  "rosewood-hong-kong": [940, 890, 965, 920, 885, 950, 910, 930, 740],
  "burj-al-arab": [2805, 2670, 2885, 2750, 2640, 2830, 2720, 2775, 2100],
  "singita-sasakwa": [2450, 2330, 2520, 2400, 2305, 2470, 2375, 2425, 2460],
  "claridges-london": [970, 920, 1000, 950, 910, 980, 940, 960, 815],
  "raffles-singapore": [1100, 1050, 1135, 1080, 1035, 1110, 1070, 1090, 1010],
};

const CAPTURE_DATES = [
  "2026-04-27",
  "2026-05-04",
  "2026-05-11",
  "2026-05-18",
  "2026-05-25",
  "2026-06-01",
  "2026-06-08",
  "2026-06-15",
  "2026-06-22",
];

export function demoHistory(id: string): RatePoint[] {
  const rates = DEMO_RATES[id] ?? [];
  return rates.map((rate, i) => ({ captured_on: CAPTURE_DATES[i], rate }));
}

export function demoPropertyWithHistory(
  id: string,
): PropertyWithHistory | null {
  const property = DEMO_PROPERTIES.find((p) => p.id === id);
  if (!property) return null;
  return { ...property, history: demoHistory(id) };
}

// --- Loyalty (Reserve) -------------------------------------------------------
export const LOYALTY_TIERS: LoyaltyTier[] = [
  { id: "silver", name: "Silver", threshold: 0, benefit: "Member rates and 4pm late checkout" },
  { id: "gold", name: "Gold", threshold: 25000, benefit: "Room upgrades and daily breakfast for two" },
  { id: "platinum", name: "Platinum", threshold: 60000, benefit: "Suite upgrades and airport transfers" },
  { id: "noir", name: "Noir", threshold: 120000, benefit: "Dedicated concierge and guaranteed availability" },
];

export const LOYALTY_ACCOUNT: LoyaltyAccount = {
  member: "Aurum Member",
  tierId: "gold",
  credits: 38500,
  ytdNights: 24,
  history: [
    { date: "2026-06-18", label: "Stay - Aman Tokyo (3 nights)", credits: 4200 },
    { date: "2026-05-30", label: "Stay - Claridge's (2 nights)", credits: 2600 },
    { date: "2026-05-12", label: "Rate Alert booking bonus", credits: 1500 },
    { date: "2026-04-22", label: "Stay - Belmond Cipriani (4 nights)", credits: 6100 },
    { date: "2026-03-28", label: "Referral credit", credits: 2000 },
  ],
  perks: [
    "Complimentary room upgrades on arrival",
    "Daily breakfast for two",
    "Guaranteed 4pm late checkout",
    "Priority Rate Alert notifications",
  ],
};

// --- Seasonality (heat map) --------------------------------------------------
function hashString(value: string): number {
  let h = 0;
  for (let i = 0; i < value.length; i += 1) {
    h = (h * 31 + value.charCodeAt(i)) >>> 0;
  }
  return h;
}

/** Deterministic 12-month rate index (~0.8 - 1.2) for a destination. */
export function seasonRow(destination: string): number[] {
  const h = hashString(destination);
  const phase = h % 12;
  const amp = 0.14 + ((h >> 4) % 8) / 100; // 0.14 - 0.21
  return Array.from({ length: 12 }, (_, m) => {
    const v = 1 + amp * Math.sin(((m - phase) / 12) * Math.PI * 2);
    return Math.round(v * 100) / 100;
  });
}
