import Link from "next/link";
import { notFound } from "next/navigation";
import type { Metadata } from "next";
import { getProperty, getSavedIds } from "@/lib/data";
import { computeSignal } from "@/lib/rates";
import { formatRate, formatShortDate } from "@/lib/format";
import { SignalBadge } from "@/components/SignalBadge";
import { StarRating } from "@/components/StarRating";
import { Sparkline } from "@/components/Sparkline";
import { BookingButtons } from "@/components/BookingButtons";
import { SaveButton } from "@/components/SaveButton";
import { PropertyImage } from "@/components/PropertyImage";

export const dynamic = "force-dynamic";

interface PageProps {
  params: Promise<{ id: string }>;
}

export async function generateMetadata({
  params,
}: PageProps): Promise<Metadata> {
  const { id } = await params;
  const property = await getProperty(id);
  if (!property) return { title: "Property not found" };
  return {
    title: `${property.name} - ${property.destination}`,
    description: property.description,
  };
}

export default async function PropertyPage({ params }: PageProps) {
  const { id } = await params;
  const [property, savedIds] = await Promise.all([
    getProperty(id),
    getSavedIds(),
  ]);

  if (!property) notFound();

  const signal = computeSignal(property.current_rate, property.avg_rate);
  const accentColor = "#c8a25a"; // champagne gold - the single metallic accent
  const series = property.history.map((h) => h.rate);

  // Build a latest-first history list with the change vs the previous capture.
  const rows = property.history
    .map((point, i) => ({
      ...point,
      delta: i === 0 ? 0 : point.rate - property.history[i - 1].rate,
    }))
    .reverse();

  return (
    <div className="mx-auto max-w-6xl px-5 pb-10">
      <div className="pt-8">
        <Link
          href="/"
          className="inline-flex items-center gap-1.5 text-sm text-white/50 transition hover:text-white"
        >
          <span aria-hidden="true">←</span> Back to all stays
        </Link>
      </div>

      {/* Hero banner with real photography */}
      <header className="relative mt-4 overflow-hidden rounded-3xl border border-white/[0.08]">
        <PropertyImage
          property={property}
          sizes="(min-width:1152px) 1152px, 100vw"
          priority
          className="absolute inset-0"
        />
        <div className="absolute inset-0 bg-gradient-to-t from-ink-900/92 via-ink-900/45 to-ink-900/15" />
        <div className="relative flex min-h-[340px] flex-col justify-end gap-3 p-6 sm:min-h-[440px] sm:p-10">
          <div className="flex items-center gap-3">
            <StarRating count={property.star_rating} />
            <span className="text-[11px] uppercase tracking-luxe text-white/65">
              {property.destination}, {property.country}
            </span>
          </div>
          <h1 className="max-w-2xl font-display text-3xl leading-tight text-white sm:text-5xl">
            {property.name}
          </h1>
          <p className="max-w-2xl text-balance text-white/70">
            {property.description}
          </p>
          <div className="pt-1">
            <SignalBadge signal={signal} />
          </div>
        </div>
      </header>

      <div className="mt-8 grid grid-cols-1 gap-6 lg:grid-cols-3">
        {/* Rate history */}
        <section className="lg:col-span-2">
          <div className="rounded-3xl border border-white/[0.08] bg-ink-700/60 p-6">
            <div className="flex items-end justify-between">
              <div>
                <h2 className="font-display text-xl text-white">Rate history</h2>
                <p className="mt-1 text-sm text-white/45">
                  Prepaid nightly rate, last {property.history.length} captures.
                </p>
              </div>
              <div className="text-right">
                <p className="text-[10px] uppercase tracking-luxe text-white/40">
                  Average
                </p>
                <p className="font-display text-xl text-white/85">
                  {formatRate(property.avg_rate, property.currency)}
                </p>
              </div>
            </div>

            <div className="mt-5">
              <Sparkline
                data={series}
                color={accentColor}
                gradientId={`spark-${property.id}`}
              />
            </div>

            <ul className="mt-5 divide-y divide-white/[0.06]">
              {rows.map((row) => {
                const up = row.delta > 0;
                const down = row.delta < 0;
                return (
                  <li
                    key={row.captured_on}
                    className="flex items-center justify-between py-2.5 text-sm"
                  >
                    <span className="text-white/50">
                      {formatShortDate(row.captured_on)}
                    </span>
                    <span className="flex items-center gap-3">
                      <span className="font-medium text-white/90">
                        {formatRate(row.rate, property.currency)}
                      </span>
                      <span
                        className={`w-16 text-right text-xs tabular-nums ${
                          down
                            ? "text-gilt-soft"
                            : up
                              ? "text-white/40"
                              : "text-white/25"
                        }`}
                      >
                        {row.delta === 0
                          ? "-"
                          : `${up ? "▲" : "▼"} ${formatRate(
                              Math.abs(row.delta),
                              property.currency,
                            )}`}
                      </span>
                    </span>
                  </li>
                );
              })}
            </ul>
          </div>
        </section>

        {/* Booking panel */}
        <aside className="lg:col-span-1">
          <div className="lg:sticky lg:top-20">
            <div className="rounded-3xl border border-white/[0.08] bg-ink-700/60 p-6">
              <p className="text-[10px] uppercase tracking-luxe text-white/40">
                Current prepaid / night
              </p>
              <div className="mt-1 flex items-end gap-3">
                <span className="font-display text-4xl text-white">
                  {formatRate(property.current_rate, property.currency)}
                </span>
                <span className="pb-1.5 text-sm text-white/40 line-through">
                  {formatRate(property.avg_rate, property.currency)}
                </span>
              </div>

              <div className="mt-3">
                <SignalBadge signal={signal} />
              </div>

              {signal.isAlert && (
                <p className="mt-3 text-sm text-gilt-soft">
                  About {signal.belowPct}% below the historical average, a
                  strong moment to book.
                </p>
              )}

              <div className="mt-5">
                <SaveButton
                  propertyId={property.id}
                  saved={savedIds.has(property.id)}
                  redirectTo={`/property/${property.id}`}
                  variant="full"
                />
              </div>

              <div className="my-5 h-px bg-white/[0.06]" />

              <p className="mb-3 text-[10px] uppercase tracking-luxe text-white/40">
                Book this stay
              </p>
              <BookingButtons property={property} />
            </div>
          </div>
        </aside>
      </div>
    </div>
  );
}
