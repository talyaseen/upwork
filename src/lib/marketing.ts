// Marketing copy for the landing page. Placeholder copy for the demo; intended
// to be swapped for the richer copy pack when it lands. Kept in one module so
// the swap is a single import change.

export const HERO = {
  eyebrow: "Rate intelligence for luxury hotels",
  title: "Know the moment a great hotel is worth booking.",
  subtitle:
    "AURUM tracks prepaid rates across the world's finest hotels, grades every rate against its own history, and signals the instant a stay drops below its average.",
  primaryCta: { label: "Launch the app", href: "/briefing" },
  secondaryCta: { label: "Explore The View", href: "/view" },
};

export interface Feature {
  icon: "signal" | "chart" | "bell" | "crown";
  title: string;
  description: string;
  href: string;
}

export const FEATURES: Feature[] = [
  {
    icon: "signal",
    title: "Five intelligence levels",
    description:
      "Every rate is graded L1 to L5 against its own history, so you see genuine value at a glance, never a manufactured discount.",
    href: "/briefing",
  },
  {
    icon: "chart",
    title: "The View",
    description:
      "Brand league tables, destination analysis, a seasonal heat map and a rate-versus-signal plot, refreshed daily.",
    href: "/view",
  },
  {
    icon: "bell",
    title: "Rate Alerts",
    description:
      "Set your thresholds and interests and receive a beautifully simple briefing the instant a stay moves below its average.",
    href: "/alerts",
  },
  {
    icon: "crown",
    title: "Reserve loyalty",
    description:
      "Earn credits on every stay, climb the tiers and unlock privileges across the collection.",
    href: "/reserve",
  },
];

export const PROBLEM = {
  title: "Luxury rates move constantly. You should never overpay.",
  body: "The finest hotels reprice every day. Without a reference point, a 'deal' is just a number. AURUM benchmarks every rate against its own history, so you know exactly when a stay is genuinely worth booking.",
  points: [
    "Daily prepaid rate capture across a curated collection",
    "Each rate graded against its own historical average",
    "Signals, not noise: only meaningful drops surface",
  ],
};

export interface PricingTier {
  name: string;
  price: string;
  period: string;
  tagline: string;
  features: string[];
  cta: string;
  highlighted: boolean;
}

export const PRICING: PricingTier[] = [
  {
    name: "Explorer",
    price: "Free",
    period: "",
    tagline: "For the occasional traveller.",
    features: [
      "The daily Briefing feed",
      "Five intelligence levels",
      "Up to five saved stays",
    ],
    cta: "Start free",
    highlighted: false,
  },
  {
    name: "Connoisseur",
    price: "$29",
    period: "/mo",
    tagline: "For the frequent connoisseur.",
    features: [
      "Everything in Explorer",
      "The View market intelligence",
      "Unlimited collection",
      "Instant Rate Alerts",
    ],
    cta: "Go Connoisseur",
    highlighted: true,
  },
  {
    name: "Concierge",
    price: "$99",
    period: "/mo",
    tagline: "White-glove, for the few.",
    features: [
      "Everything in Connoisseur",
      "Reserve Noir status",
      "Dedicated concierge",
      "Priority availability",
    ],
    cta: "Talk to us",
    highlighted: false,
  },
];

export interface Faq {
  q: string;
  a: string;
}

export const FAQS: Faq[] = [
  {
    q: "Where do the rates come from?",
    a: "In this demo, rates are illustrative sample data. In production, AURUM captures prepaid nightly rates daily from each property and the major travel platforms.",
  },
  {
    q: "What is an intelligence level?",
    a: "A grade from L1 (at market) to L5 (exceptional, 20%+ below its historical average). It turns a raw price into a clear read on value.",
  },
  {
    q: "How do Rate Alerts work?",
    a: "Choose a minimum signal level, a frequency and the experiences you care about. We send a concise digest the moment a matching stay drops below its average.",
  },
  {
    q: "Is my data private?",
    a: "Your saved collection is private to your account, enforced at the database level with row-level security. Property and market data is shared.",
  },
];

export const FINAL_CTA = {
  title: "Start booking the great hotels at their best.",
  subtitle: "Join AURUM and let the rates come to you.",
  cta: { label: "Launch the app", href: "/briefing" },
};
