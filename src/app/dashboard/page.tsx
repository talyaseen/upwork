import type { Metadata } from "next";
import { getProperties } from "@/lib/data";
import { toUsd, marketSeries } from "@/lib/analytics";
import { byBestDeal } from "@/lib/rates";
import { formatShortDate } from "@/lib/format";
import { PageHeader } from "@/components/PageHeader";
import { MarketTrendLine, SignalDistribution } from "@/components/charts";
import { MiniPropertyRow } from "@/components/MiniPropertyRow";
import { Reveal, AnimatedNumber } from "@/components/motion";
import { DASHBOARD_IMAGE } from "@/lib/images";

export const dynamic = "force-dynamic";
export const metadata: Metadata = { title: "Dashboard" };

export default async function DashboardPage() {
  const properties = await getProperties();
  const n = properties.length;

  const usdRates = properties.map((p) => toUsd(p.current_rate, p.currency));
  const adr = Math.round(usdRates.reduce((a, b) => a + b, 0) / Math.max(1, n));
  const avgSignal = Math.round(
    properties.reduce((a, p) => a + p.signal.belowPct, 0) / Math.max(1, n),
  );
  const alerts = [...properties].filter((p) => p.signal.isAlert).sort(byBestDeal);

  const series = marketSeries();
  const values = series.map((s) => s.avgUsd);
  const labels = series.map((s) => formatShortDate(s.date));
  const first = values[0] ?? 0;
  const last = values[values.length - 1] ?? 0;
  const trendDelta = first ? Math.round(((last - first) / first) * 100) : 0;

  const dist = [5, 4, 3, 2, 1].map((level) => ({
    level,
    count: properties.filter((p) => p.signal.level === level).length,
  }));

  const kpis = [
    { label: "Hotels tracked", value: n, prefix: "", suffix: "" },
    { label: "Market ADR", value: adr, prefix: "$", suffix: "" },
    { label: "Avg signal vs history", value: avgSignal, prefix: "-", suffix: "%" },
    { label: "Live Rate Alerts", value: alerts.length, prefix: "", suffix: "" },
  ];

  return (
    <div className="mx-auto max-w-6xl px-5 pb-12">
      <div className="pt-7">
        <PageHeader
          image={DASHBOARD_IMAGE}
          eyebrow="Dashboard"
          title="The tracked market, at a glance."
          subtitle="Average daily rate, signal distribution, the market trend and every live Rate Alert in one intelligence overview."
        />
      </div>

      {/* KPIs */}
      <section className="mt-8 grid grid-cols-2 gap-4 lg:grid-cols-4">
        {kpis.map((k, i) => (
          <Reveal key={k.label} delay={i * 0.05}>
            <div className="rounded-2xl border border-white/[0.08] bg-ink-700/60 p-5">
              <AnimatedNumber
                value={k.value}
                prefix={k.prefix}
                suffix={k.suffix}
                className="font-display text-3xl text-gilt-soft sm:text-4xl"
              />
              <p className="mt-1.5 text-xs leading-snug text-white/45">
                {k.label}
              </p>
            </div>
          </Reveal>
        ))}
      </section>

      <div className="mt-6 grid grid-cols-1 gap-6 lg:grid-cols-3">
        <Reveal className="lg:col-span-2">
          <Card
            title="Market rate trend"
            subtitle={`USD-normalised average nightly rate. The market is ${
              trendDelta <= 0 ? "down" : "up"
            } ${Math.abs(trendDelta)}% over the last ${values.length} captures.`}
          >
            <div className="mt-2">
              <MarketTrendLine values={values} labels={labels} />
            </div>
          </Card>
        </Reveal>

        <Reveal delay={0.05}>
          <Card
            title="Signal distribution"
            subtitle="Properties graded by intelligence level."
          >
            <SignalDistribution dist={dist} />
          </Card>
        </Reveal>
      </div>

      {/* Live alerts */}
      <Reveal className="mt-6">
        <Card
          title="Live Rate Alerts"
          subtitle="Every stay currently 12%+ below its historical average."
        >
          {alerts.length > 0 ? (
            <div className="grid grid-cols-1 gap-2.5 sm:grid-cols-2">
              {alerts.map((p) => (
                <MiniPropertyRow key={p.id} property={p} />
              ))}
            </div>
          ) : (
            <p className="py-8 text-center text-sm text-white/40">
              No live alerts right now.
            </p>
          )}
        </Card>
      </Reveal>
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
