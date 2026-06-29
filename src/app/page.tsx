import Image from "next/image";
import { getProperties, getSavedIds } from "@/lib/data";
import { byBestDeal } from "@/lib/rates";
import { PropertyCard } from "@/components/PropertyCard";
import { HERO_IMAGE, HERO_BLUR } from "@/lib/images";

// Reads request cookies (auth) -> always render per-request.
export const dynamic = "force-dynamic";

export default async function HomePage() {
  const [properties, savedIds] = await Promise.all([
    getProperties(),
    getSavedIds(),
  ]);

  const sorted = [...properties].sort(byBestDeal);
  const alerts = sorted.filter((p) => p.signal.isAlert);
  const bestDeal = sorted.reduce(
    (best, p) => Math.max(best, p.signal.belowPct),
    0,
  );

  const stats = [
    { value: properties.length, label: "Luxury stays tracked" },
    { value: alerts.length, label: "Rate alerts live now" },
    { value: `-${bestDeal}%`, label: "Best value vs average" },
  ];

  return (
    <div className="mx-auto max-w-6xl px-5">
      {/* Cinematic hero */}
      <section className="pt-7">
        <div className="relative overflow-hidden rounded-3xl border border-white/[0.08] shadow-card">
          <Image
            src={HERO_IMAGE}
            alt=""
            fill
            priority
            placeholder="blur"
            blurDataURL={HERO_BLUR}
            sizes="(min-width:1152px) 1100px, 100vw"
            className="object-cover"
          />
          <div className="absolute inset-0 bg-gradient-to-t from-ink-900 via-ink-900/55 to-ink-900/20" />
          <div className="absolute inset-0 bg-gradient-to-r from-ink-900/85 via-ink-900/30 to-transparent" />

          <div className="relative flex min-h-[440px] flex-col justify-end gap-5 p-7 sm:min-h-[540px] sm:p-12">
            <span className="inline-flex w-fit items-center gap-2 rounded-full border border-gilt/30 bg-ink-900/40 px-3.5 py-1.5 text-xs font-medium uppercase tracking-luxe text-gilt-soft backdrop-blur">
              <span className="h-1.5 w-1.5 rounded-full bg-gilt" />
              Live prepaid rates
            </span>

            <h1 className="max-w-3xl text-balance font-display text-4xl leading-[1.04] text-white sm:text-6xl">
              Rate intelligence for the world&apos;s finest stays.
            </h1>

            <p className="max-w-xl text-balance text-lg leading-relaxed text-white/70">
              We watch prepaid nightly rates across the great hotels and signal
              the moment a stay drops below its historical average, so you book
              at its best price.
            </p>
          </div>
        </div>
      </section>

      {/* Stats */}
      <section className="pt-10">
        <dl className="grid grid-cols-3 gap-4">
          {stats.map((s) => (
            <div
              key={s.label}
              className="rounded-2xl border border-white/[0.08] bg-ink-700/60 p-5"
            >
              <dt className="font-display text-3xl text-gilt-soft sm:text-4xl">
                {s.value}
              </dt>
              <dd className="mt-1.5 text-xs leading-snug text-white/45 sm:text-sm">
                {s.label}
              </dd>
            </div>
          ))}
        </dl>
      </section>

      {/* Grid */}
      <section className="pb-8 pt-12">
        <div className="mb-6 flex flex-wrap items-end justify-between gap-3 border-b border-white/[0.06] pb-4">
          <div>
            <h2 className="font-display text-2xl text-white">Tracked stays</h2>
            <p className="mt-1 text-sm text-white/45">
              Sorted by today&apos;s value against the historical average.
            </p>
          </div>
          <p className="flex items-center gap-2 text-xs text-white/50">
            <span className="inline-flex h-2 w-2 rounded-full bg-gilt" />
            Rate Alert = current rate 10%+ below average
          </p>
        </div>

        <div className="grid grid-cols-1 gap-5 sm:grid-cols-2 lg:grid-cols-3">
          {sorted.map((property) => (
            <PropertyCard
              key={property.id}
              property={property}
              saved={savedIds.has(property.id)}
            />
          ))}
        </div>
      </section>
    </div>
  );
}
