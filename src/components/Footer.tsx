import Link from "next/link";
import { Logo } from "@/components/Logo";

const LINKS = [
  { href: "/briefing", label: "Briefing" },
  { href: "/dashboard", label: "Dashboard" },
  { href: "/view", label: "The View" },
  { href: "/collection", label: "Collection" },
  { href: "/reserve", label: "Reserve" },
  { href: "/alerts", label: "Alerts" },
];

export function Footer() {
  return (
    <footer className="mt-24 border-t border-white/[0.06]">
      <div className="mx-auto max-w-6xl px-5 py-10">
        <div className="flex flex-col gap-6 sm:flex-row sm:items-center sm:justify-between">
          <div className="flex items-center gap-2.5">
            <Logo className="opacity-80" />
            <div className="leading-tight">
              <p className="font-display text-base text-white/80">AURUM</p>
              <p className="text-xs text-white/45">
                Rate intelligence for luxury stays
              </p>
            </div>
          </div>
          <nav className="flex flex-wrap gap-x-5 gap-y-2 text-sm text-white/50">
            {LINKS.map((l) => (
              <Link
                key={l.href}
                href={l.href}
                className="transition hover:text-white"
              >
                {l.label}
              </Link>
            ))}
          </nav>
        </div>
        <p className="mt-8 max-w-2xl text-xs leading-relaxed text-white/35">
          Demo / portfolio build. Hotels, brands and destinations are real;
          rates, rate history and loyalty figures are illustrative sample data
          for demonstration only, not live or quoted prices.
        </p>
      </div>
    </footer>
  );
}
