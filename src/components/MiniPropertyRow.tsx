import Link from "next/link";
import type { SignalProperty } from "@/lib/types";
import { formatRate } from "@/lib/format";
import { LevelBadge } from "@/components/LevelBadge";

/** Compact property row used in comparison lists. */
export function MiniPropertyRow({ property }: { property: SignalProperty }) {
  return (
    <Link
      href={`/property/${property.id}`}
      className="group flex items-center gap-3 rounded-2xl border border-white/[0.06] bg-ink-800/40 p-3 transition hover:border-white/15 hover:bg-ink-800/70"
    >
      <div
        className="h-12 w-12 shrink-0 rounded-lg"
        style={{
          backgroundImage: `linear-gradient(135deg, ${property.accent_from}, ${property.accent_to})`,
        }}
      />
      <div className="min-w-0 flex-1">
        <p className="truncate text-sm text-white transition group-hover:text-gilt-soft">
          {property.name}
        </p>
        <p className="truncate text-xs text-white/40">
          {property.destination}, {property.country}
        </p>
      </div>
      <div className="flex shrink-0 flex-col items-end gap-1">
        <span className="font-display text-sm text-white">
          {formatRate(property.current_rate, property.currency)}
        </span>
        <LevelBadge level={property.signal.level} showLabel={false} />
      </div>
    </Link>
  );
}
