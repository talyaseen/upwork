import type { Property, PropertyWithHistory, RatePoint } from "@/lib/types";
import { unsplash } from "@/lib/images";

// -----------------------------------------------------------------------------
// Bundled illustrative sample data. This is the SAME dataset as
// supabase/seed.sql and is used as a fallback so the app renders beautifully
// with zero configuration (no Supabase project, no network calls).
//
// The hotels and destinations are real; the rates and rate history are
// illustrative sample data for demonstration only, not live or quoted prices.
// -----------------------------------------------------------------------------

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

export const DEMO_PROPERTIES: Property[] = [
  {
    id: "aman-tokyo",
    name: "Aman Tokyo",
    destination: "Tokyo",
    country: "Japan",
    description:
      "Urban sanctuary on the upper floors of Otemachi Tower, with onsen baths and city-wide views.",
    star_rating: 5,
    current_rate: 1180,
    avg_rate: 1320,
    currency: "USD",
    accent_from: "#1f2350",
    accent_to: "#4a2d52",
    image_url: unsplash("1540959733332-eab4deabeeaf"),
  },
  {
    id: "ritz-paris",
    name: "The Ritz Paris",
    destination: "Paris",
    country: "France",
    description:
      "The legendary Place Vendome palace hotel, redefining Parisian elegance since 1898.",
    star_rating: 5,
    current_rate: 1650,
    avg_rate: 1700,
    currency: "EUR",
    accent_from: "#3a2c20",
    accent_to: "#7c5a3a",
    image_url: unsplash("1502602898657-3e91760cbb34"),
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
  },
  {
    id: "four-seasons-bora-bora",
    name: "Four Seasons Resort Bora Bora",
    destination: "Bora Bora",
    country: "French Polynesia",
    description:
      "Overwater bungalows above a turquoise lagoon, framed by the silhouette of Mount Otemanu.",
    star_rating: 5,
    current_rate: 1880,
    avg_rate: 2300,
    currency: "USD",
    accent_from: "#0a4f5c",
    accent_to: "#2aa7a0",
    image_url: unsplash("1518391846015-55a9cc003b25"),
  },
  {
    id: "the-plaza-ny",
    name: "The Plaza",
    destination: "New York",
    country: "United States",
    description:
      "A Beaux-Arts landmark on Fifth Avenue overlooking Central Park since 1907.",
    star_rating: 5,
    current_rate: 925,
    avg_rate: 1010,
    currency: "USD",
    accent_from: "#2a2730",
    accent_to: "#5c4a63",
    image_url: unsplash("1496417263034-38ec4f0b665a"),
  },
  {
    id: "claridges-london",
    name: "Claridge's",
    destination: "London",
    country: "United Kingdom",
    description:
      "Art Deco grandeur in the heart of Mayfair, a byword for understated British luxury.",
    star_rating: 5,
    current_rate: 780,
    avg_rate: 950,
    currency: "GBP",
    accent_from: "#26282b",
    accent_to: "#4a4f57",
    image_url: unsplash("1513635269975-59663e0ac1ad"),
  },
  {
    id: "singita-sasakwa",
    name: "Singita Sasakwa Lodge",
    destination: "Serengeti",
    country: "Tanzania",
    description:
      "An Edwardian-style safari lodge on a private hill, overlooking the Serengeti plains.",
    star_rating: 5,
    current_rate: 2450,
    avg_rate: 2400,
    currency: "USD",
    accent_from: "#3a2a12",
    accent_to: "#9a6b2f",
    image_url: unsplash("1516026672322-bc52d61a55d5"),
  },
];

// Nine weekly rate captures per property; the final point is "today" and equals
// the property's current_rate.
const DEMO_RATES: Record<string, number[]> = {
  "aman-tokyo": [1345, 1295, 1385, 1320, 1265, 1360, 1305, 1335, 1180],
  "ritz-paris": [1735, 1665, 1785, 1700, 1630, 1750, 1685, 1715, 1650],
  "burj-al-arab": [2805, 2695, 2885, 2750, 2640, 2830, 2720, 2775, 2100],
  "belmond-caruso": [1550, 1490, 1595, 1520, 1460, 1565, 1505, 1535, 1490],
  "four-seasons-bora-bora": [
    2345, 2255, 2415, 2300, 2210, 2370, 2275, 2325, 1880,
  ],
  "the-plaza-ny": [1030, 990, 1060, 1010, 970, 1040, 1000, 1020, 925],
  "claridges-london": [970, 930, 995, 950, 910, 980, 940, 960, 780],
  "singita-sasakwa": [2450, 2350, 2520, 2400, 2305, 2470, 2375, 2425, 2450],
};

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
