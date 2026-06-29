import Link from "next/link";
import type { SignalProperty } from "@/lib/types";
import { formatRate } from "@/lib/format";
import { SignalBadge } from "@/components/SignalBadge";
import { StarRating } from "@/components/StarRating";
import { PropertyImage } from "@/components/PropertyImage";

interface Props {
  property: SignalProperty;
  saved?: boolean;
  priority?: boolean;
}

export function PropertyCard({ property, saved = false, priority = false }: Props) {
  const { signal } = property;

  return (
    <Link
      href={`/property/${property.id}`}
      className={`group relative flex flex-col overflow-hidden rounded-2xl border bg-ink-700 shadow-card transition duration-300 hover:-translate-y-1 ${
        signal.isAlert
          ? "border-gilt/30 hover:border-gilt/55 hover:shadow-glow"
          : "border-white/[0.08] hover:border-white/20"
      }`}
    >
      {/* Hero photo with gradient + blur fallback */}
      <div className="relative h-52 w-full">
        <PropertyImage
          property={property}
          sizes="(min-width:1024px) 360px, (min-width:640px) 45vw, 92vw"
          priority={priority}
          className="absolute inset-0"
          imageClassName="transition-transform duration-700 ease-out group-hover:scale-[1.06]"
        />
        <div className="absolute inset-0 bg-gradient-to-t from-ink-900/95 via-ink-900/25 to-transparent" />

        <div className="absolute inset-x-4 top-4 flex items-start justify-between">
          {signal.isAlert ? <SignalBadge signal={signal} /> : <span />}
          {saved && (
            <span
              title="In your collection"
              className="flex h-7 w-7 items-center justify-center rounded-full bg-ink-900/70 text-gilt backdrop-blur"
            >
              ♥
            </span>
          )}
        </div>

        <div className="absolute inset-x-5 bottom-4">
          <p className="text-[11px] uppercase tracking-luxe text-white/70">
            {property.destination}, {property.country}
          </p>
          <h3 className="mt-0.5 font-display text-xl leading-tight text-white drop-shadow-sm">
            {property.name}
          </h3>
        </div>
      </div>

      {/* Footer: pricing + signal */}
      <div className="flex items-end justify-between gap-3 p-5">
        <div>
          <p className="text-[10px] uppercase tracking-luxe text-white/40">
            Prepaid / night
          </p>
          <p className="font-display text-2xl text-white">
            {formatRate(property.current_rate, property.currency)}
          </p>
          <p className="text-xs text-white/45">
            avg {formatRate(property.avg_rate, property.currency)}
          </p>
        </div>
        <div className="flex flex-col items-end gap-2">
          <StarRating count={property.star_rating} />
          {!signal.isAlert && <SignalBadge signal={signal} />}
        </div>
      </div>
    </Link>
  );
}
