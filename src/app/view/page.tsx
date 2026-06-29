import type { Metadata } from "next";
import { getProperties } from "@/lib/data";
import {
  brandStats,
  destinationStats,
  scatterPoints,
  seasonRows,
  MONTH_LABELS,
} from "@/lib/analytics";
import {
  BrandLeagueTable,
  DestinationAnalysis,
  SeasonHeatmap,
  RateSignalScatter,
} from "@/components/charts";
import { PageHeader } from "@/components/PageHeader";
import { Reveal } from "@/components/motion";
import { VIEW_IMAGE } from "@/lib/images";

export const dynamic = "force-dynamic";
export const metadata: Metadata = {
  title: "The View",
  description:
    "Market intelligence for luxury hotels: brand league tables, destination analysis, seasonality and the rate-versus-signal picture.",
};

export default async function TheViewPage() {
  const properties = await getProperties();
  const brands = brandStats(properties);
  const destinations = destinationStats(properties);
  const scatter = scatterPoints(properties);
  const seasons = seasonRows(properties);

  return (
    <div className="mx-auto max-w-6xl px-5 pb-12">
      <div className="pt-7">
        <PageHeader
          image={VIEW_IMAGE}
          eyebrow="The View"
          title="Market intelligence across the finest hotels."
          subtitle="Brand league tables, destination analysis, seasonality and the rate-versus-signal picture, refreshed daily."
        />
      </div>

      <div className="mt-8 grid grid-cols-1 gap-6 lg:grid-cols-2">
        <Reveal>
          <Card
            title="Brand league table"
            subtitle="Average discount vs historical average, by group."
          >
            <BrandLeagueTable stats={brands} />
          </Card>
        </Reveal>

        <Reveal delay={0.05}>
          <Card
            title="Destination analysis"
            subtitle="Where prepaid rates are softest right now."
          >
            <DestinationAnalysis stats={destinations} />
          </Card>
        </Reveal>

        <Reveal className="lg:col-span-2">
          <Card
            title="Rate vs signal"
            subtitle="Every stay plotted by nightly rate against its discount. Gold points are live Rate Alerts."
          >
            <div className="mt-2">
              <RateSignalScatter points={scatter} />
            </div>
          </Card>
        </Reveal>

        <Reveal className="lg:col-span-2">
          <Card
            title="Seasonal heat map"
            subtitle="Indicative rate index by month and destination (sample data)."
          >
            <div className="mt-2">
              <SeasonHeatmap rows={seasons} months={MONTH_LABELS} />
            </div>
          </Card>
        </Reveal>
      </div>
    </div>
  );
}

function Card({
  title,
  subtitle,
  children,
}: {
  title: string;
  subtitle: string;
  children: React.ReactNode;
}) {
  return (
    <section className="h-full rounded-3xl border border-white/[0.08] bg-ink-700/50 p-6 sm:p-7">
      <h2 className="font-display text-xl text-white">{title}</h2>
      <p className="mt-1 text-sm text-white/45">{subtitle}</p>
      <div className="mt-5">{children}</div>
    </section>
  );
}
