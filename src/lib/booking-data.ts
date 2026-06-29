import type {
  Property,
  RoomType,
  StayPackage,
  StayQuote,
  QuoteNight,
} from "@/lib/types";

// Placeholder rates/packages + a quoteStay() helper for the booking widget.
// Intended to be swapped for the data pack's exports (same shapes) when ready.
// This is the property's OWN rate card / booking engine - the surface the
// AURUM intelligence platform monitors and benchmarks against competitors.

export const WEEKEND_MULTIPLIER = 1.25; // Friday + Saturday nights cost more
const TAX_RATE = 0.12;
const RESORT_FEE_PER_NIGHT = 45;

const ROOM_TYPES: RoomType[] = [
  {
    id: "deluxe",
    name: "Deluxe Room",
    description: "Refined comfort with a city or garden view.",
    multiplier: 1.0,
    maxOccupancy: 2,
    beds: "1 King",
    sizeSqm: 42,
    accent_from: "#26233a",
    accent_to: "#4a3f63",
  },
  {
    id: "premier",
    name: "Premier Room",
    description: "More space and a statement bathroom.",
    multiplier: 1.28,
    maxOccupancy: 2,
    beds: "1 King or 2 Twin",
    sizeSqm: 55,
    accent_from: "#1f3340",
    accent_to: "#356b7a",
  },
  {
    id: "junior-suite",
    name: "Junior Suite",
    description: "A separate sitting area and the finest views.",
    multiplier: 1.7,
    maxOccupancy: 3,
    beds: "1 King + sofa bed",
    sizeSqm: 78,
    accent_from: "#34291a",
    accent_to: "#7c5a3a",
  },
  {
    id: "signature-suite",
    name: "Signature Suite",
    description: "The flagship suite, with bespoke service.",
    multiplier: 2.6,
    maxOccupancy: 4,
    beds: "1 King + 1 Queen",
    sizeSqm: 120,
    accent_from: "#2a1830",
    accent_to: "#7a3f5a",
  },
];

export function getRoomTypes(_property: Property): RoomType[] {
  return ROOM_TYPES;
}

export const PACKAGES: StayPackage[] = [
  {
    id: "room-only",
    name: "Room only",
    description: "Just the room, at the best flexible rate.",
    perNight: 0,
    flat: 0,
  },
  {
    id: "bed-breakfast",
    name: "Bed & Breakfast",
    description: "Daily breakfast for two.",
    perNight: 60,
    flat: 0,
  },
  {
    id: "half-board",
    name: "Half Board",
    description: "Breakfast and dinner, every day.",
    perNight: 140,
    flat: 0,
  },
  {
    id: "spa-escape",
    name: "Spa Escape",
    description: "Two 60-minute treatments and full spa access.",
    perNight: 0,
    flat: 420,
  },
  {
    id: "romance",
    name: "Romance",
    description: "Champagne, rose petals and a late checkout.",
    perNight: 0,
    flat: 260,
  },
  {
    id: "suite-upgrade",
    name: "Suite Upgrade",
    description: "A guaranteed one-category upgrade on arrival.",
    perNight: 90,
    flat: 0,
  },
];

function eachNight(checkIn: string, checkOut: string): string[] {
  const start = new Date(`${checkIn}T00:00:00Z`);
  const end = new Date(`${checkOut}T00:00:00Z`);
  const out: string[] = [];
  if (Number.isNaN(start.getTime()) || Number.isNaN(end.getTime())) return out;
  for (
    let d = new Date(start);
    d < end;
    d.setUTCDate(d.getUTCDate() + 1)
  ) {
    out.push(d.toISOString().slice(0, 10));
  }
  return out;
}

/** Friday and Saturday nights carry the weekend lift. */
export function isWeekendNight(iso: string): boolean {
  const day = new Date(`${iso}T00:00:00Z`).getUTCDay(); // 0 Sun .. 6 Sat
  return day === 5 || day === 6;
}

export function quoteStay(input: {
  property: Property;
  room: RoomType;
  pkg: StayPackage;
  checkIn: string;
  checkOut: string;
}): StayQuote {
  const { property, room, pkg, checkIn, checkOut } = input;
  const base = property.current_rate * room.multiplier;

  const nights: QuoteNight[] = eachNight(checkIn, checkOut).map((date) => {
    const weekend = isWeekendNight(date);
    return {
      date,
      weekend,
      rate: Math.round(base * (weekend ? WEEKEND_MULTIPLIER : 1)),
    };
  });

  const nightsCount = nights.length;
  const roomSubtotal = nights.reduce((s, n) => s + n.rate, 0);
  const packageTotal =
    pkg.perNight * nightsCount + (nightsCount > 0 ? pkg.flat : 0);
  const fees = RESORT_FEE_PER_NIGHT * nightsCount;
  const taxes = Math.round((roomSubtotal + packageTotal) * TAX_RATE);
  const grandTotal = roomSubtotal + packageTotal + taxes + fees;

  return {
    nights,
    nightsCount,
    roomSubtotal,
    packageTotal,
    taxes,
    fees,
    grandTotal,
    currency: property.currency,
  };
}

/** Deterministic default stay (a Fri-Sun weekend) so the demo shows the lift. */
export const DEFAULT_CHECK_IN = "2026-07-03"; // Friday
export const DEFAULT_CHECK_OUT = "2026-07-05"; // Sunday (Fri + Sat nights)
