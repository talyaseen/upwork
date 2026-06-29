import Image from "next/image";
import Link from "next/link";
import type { Metadata } from "next";
import { HERO_IMAGE, HERO_BLUR } from "@/lib/images";
import {
  HERO,
  FEATURES,
  PROBLEM,
  PRICING,
  FAQS,
  FINAL_CTA,
} from "@/lib/marketing";
import { DEMO_PROPERTIES, BRANDS } from "@/lib/demo-data";
import { withSignals } from "@/lib/rates";
import { brandStats } from "@/lib/analytics";
import { BrandLeagueTable } from "@/components/charts";
import { FeatureIcon } from "@/components/FeatureIcon";
import { FaqAccordion } from "@/components/FaqAccordion";
import { Reveal, Stagger, StaggerItem, AnimatedNumber } from "@/components/motion";

export const metadata: Metadata = {
  title: { absolute: "AURUM · Rate Intelligence for Luxury Hotels" },
  description:
    "AURUM tracks prepaid rates across the world's finest hotels, grades every rate against its history, and signals the moment a stay is worth booking.",
};

export default function LandingPage() {
  const signaled = withSignals(DEMO_PROPERTIES);
  const brands = brandStats(signaled);
  const alerts = signaled.filter((p) => p.signal.isAlert).length;
  const bestPct = Math.max(...signaled.map((p) => p.signal.belowPct));

  const heroStats = [
    { value: DEMO_PROPERTIES.length, label: "Hotels tracked", prefix: "", suffix: "" },
    { value: brands.length, label: "Luxury brands", prefix: "", suffix: "" },
    { value: bestPct, label: "Best signal today", prefix: "-", suffix: "%" },
  ];

  return (
    <>
      {/* Hero */}
      <section className="relative w-full overflow-hidden">
        <Image
          src={HERO_IMAGE}
          alt=""
          fill
          priority
          placeholder="blur"
          blurDataURL={HERO_BLUR}
          sizes="100vw"
          className="animate-kenburns object-cover"
        />
        <div className="absolute inset-0 bg-gradient-to-t from-ink-900 via-ink-900/65 to-ink-900/40" />
        <div className="absolute inset-0 bg-gradient-to-r from-ink-900/80 to-transparent" />

        <div className="relative mx-auto flex min-h-[86vh] max-w-6xl flex-col justify-center px-5 py-20">
          <Reveal>
            <span className="inline-flex w-fit items-center gap-2 rounded-full border border-gilt/30 bg-ink-900/40 px-3.5 py-1.5 text-xs font-medium uppercase tracking-luxe text-gilt-soft backdrop-blur">
              <span className="h-1.5 w-1.5 rounded-full bg-gilt" />
              {HERO.eyebrow}
            </span>
          </Reveal>
          <Reveal delay={0.08}>
            <h1 className="mt-6 max-w-3xl text-balance font-display text-4xl leading-[1.04] text-white sm:text-6xl lg:text-7xl">
              {HERO.title}
            </h1>
          </Reveal>
          <Reveal delay={0.16}>
            <p className="mt-6 max-w-xl text-balance text-lg leading-relaxed text-white/70">
              {HERO.subtitle}
            </p>
          </Reveal>
          <Reveal delay={0.24}>
            <div className="mt-8 flex flex-col gap-3 sm:flex-row">
              <Link
                href={HERO.primaryCta.href}
                className="inline-flex items-center justify-center rounded-full bg-gilt px-6 py-3 text-sm font-semibold text-ink-900 transition hover:bg-gilt-soft active:scale-[0.98]"
              >
                {HERO.primaryCta.label}
              </Link>
              <Link
                href={HERO.secondaryCta.href}
                className="inline-flex items-center justify-center rounded-full border border-white/20 bg-white/[0.03] px-6 py-3 text-sm font-medium text-white/85 transition hover:border-white/40 hover:text-white"
              >
                {HERO.secondaryCta.label}
              </Link>
            </div>
          </Reveal>
          <Reveal delay={0.32}>
            <dl className="mt-12 grid max-w-lg grid-cols-3 gap-6">
              {heroStats.map((s) => (
                <div key={s.label}>
                  <dt>
                    <AnimatedNumber
                      value={s.value}
                      prefix={s.prefix}
                      suffix={s.suffix}
                      className="font-display text-3xl text-gilt-soft sm:text-4xl"
                    />
                  </dt>
                  <dd className="mt-1 text-xs text-white/45">{s.label}</dd>
                </div>
              ))}
            </dl>
          </Reveal>
        </div>
      </section>

      <div className="mx-auto max-w-6xl px-5">
        {/* Trust strip */}
        <Reveal className="border-b border-white/[0.06] py-10">
          <p className="text-center text-[11px] uppercase tracking-luxe text-white/35">
            Tracking the great names
          </p>
          <div className="mt-5 flex flex-wrap items-center justify-center gap-x-8 gap-y-3">
            {BRANDS.map((b) => (
              <span
                key={b.id}
                className="font-display text-lg text-white/45 transition hover:text-white/70"
              >
                {b.name}
              </span>
            ))}
          </div>
        </Reveal>

        {/* Problem */}
        <section className="grid grid-cols-1 gap-10 py-20 lg:grid-cols-2 lg:items-center">
          <Reveal>
            <div>
              <h2 className="max-w-md text-balance font-display text-3xl leading-tight text-white sm:text-4xl">
                {PROBLEM.title}
              </h2>
              <p className="mt-5 max-w-md text-balance leading-relaxed text-white/55">
                {PROBLEM.body}
              </p>
            </div>
          </Reveal>
          <Reveal delay={0.08}>
            <ul className="space-y-3 rounded-3xl border border-white/[0.08] bg-ink-700/40 p-6 sm:p-8">
              {PROBLEM.points.map((p) => (
                <li key={p} className="flex items-start gap-3 text-white/75">
                  <span className="mt-0.5 flex h-5 w-5 shrink-0 items-center justify-center rounded-full border border-gilt/40 bg-gilt/10 text-[11px] text-gilt-soft">
                    ✓
                  </span>
                  {p}
                </li>
              ))}
            </ul>
          </Reveal>
        </section>

        {/* Features */}
        <section className="py-16">
          <Reveal>
            <div className="mb-10 text-center">
              <p className="text-[11px] uppercase tracking-luxe text-gilt-soft">
                The platform
              </p>
              <h2 className="mt-2 font-display text-3xl text-white sm:text-4xl">
                Everything you need to book at the right moment.
              </h2>
            </div>
          </Reveal>
          <Stagger className="grid grid-cols-1 gap-5 sm:grid-cols-2">
            {FEATURES.map((f) => (
              <StaggerItem key={f.title}>
                <Link
                  href={f.href}
                  className="group flex h-full flex-col rounded-3xl border border-white/[0.08] bg-ink-700/40 p-7 transition hover:-translate-y-1 hover:border-white/20"
                >
                  <span className="flex h-11 w-11 items-center justify-center rounded-2xl border border-gilt/30 bg-gilt/10 text-gilt-soft">
                    <FeatureIcon name={f.icon} />
                  </span>
                  <h3 className="mt-5 font-display text-xl text-white">
                    {f.title}
                  </h3>
                  <p className="mt-2 flex-1 leading-relaxed text-white/55">
                    {f.description}
                  </p>
                  <span className="mt-4 text-sm text-gilt-soft transition group-hover:text-gilt">
                    Explore &rarr;
                  </span>
                </Link>
              </StaggerItem>
            ))}
          </Stagger>
        </section>

        {/* Live preview */}
        <section className="py-16">
          <Reveal>
            <div className="rounded-3xl border border-white/[0.08] bg-ink-700/40 p-6 sm:p-9">
              <div className="mb-6 flex flex-wrap items-end justify-between gap-3">
                <div>
                  <p className="text-[11px] uppercase tracking-luxe text-gilt-soft">
                    Live preview
                  </p>
                  <h2 className="mt-2 font-display text-2xl text-white">
                    A look inside The View
                  </h2>
                </div>
                <Link
                  href="/view"
                  className="rounded-full border border-white/15 px-4 py-2 text-sm text-white/80 transition hover:border-white/30 hover:text-white"
                >
                  Open The View
                </Link>
              </div>
              <BrandLeagueTable stats={brands} />
            </div>
          </Reveal>
        </section>

        {/* Pricing */}
        <section className="py-16">
          <Reveal>
            <div className="mb-10 text-center">
              <p className="text-[11px] uppercase tracking-luxe text-gilt-soft">
                Membership
              </p>
              <h2 className="mt-2 font-display text-3xl text-white sm:text-4xl">
                Choose how you travel.
              </h2>
            </div>
          </Reveal>
          <Stagger className="grid grid-cols-1 gap-5 lg:grid-cols-3">
            {PRICING.map((tier) => (
              <StaggerItem key={tier.name}>
                <div
                  className={`flex h-full flex-col rounded-3xl border p-7 ${
                    tier.highlighted
                      ? "border-gilt/40 bg-gilt/[0.06] shadow-glow"
                      : "border-white/[0.08] bg-ink-700/40"
                  }`}
                >
                  {tier.highlighted && (
                    <span className="mb-3 inline-flex w-fit rounded-full bg-gilt px-3 py-1 text-[11px] font-semibold uppercase tracking-wide text-ink-900">
                      Most popular
                    </span>
                  )}
                  <h3 className="font-display text-xl text-white">{tier.name}</h3>
                  <p className="mt-1 text-sm text-white/45">{tier.tagline}</p>
                  <div className="mt-5 flex items-end gap-1">
                    <span className="font-display text-4xl text-white">
                      {tier.price}
                    </span>
                    {tier.period && (
                      <span className="pb-1.5 text-sm text-white/40">
                        {tier.period}
                      </span>
                    )}
                  </div>
                  <ul className="mt-6 flex-1 space-y-2.5">
                    {tier.features.map((f) => (
                      <li
                        key={f}
                        className="flex items-start gap-2.5 text-sm text-white/70"
                      >
                        <span className="mt-0.5 flex h-4 w-4 shrink-0 items-center justify-center rounded-full border border-gilt/40 bg-gilt/10 text-[9px] text-gilt-soft">
                          ✓
                        </span>
                        {f}
                      </li>
                    ))}
                  </ul>
                  <Link
                    href="/signup"
                    className={`mt-7 inline-flex items-center justify-center rounded-full px-5 py-2.5 text-sm font-semibold transition ${
                      tier.highlighted
                        ? "bg-gilt text-ink-900 hover:bg-gilt-soft"
                        : "border border-white/15 text-white/85 hover:border-white/35 hover:text-white"
                    }`}
                  >
                    {tier.cta}
                  </Link>
                </div>
              </StaggerItem>
            ))}
          </Stagger>
        </section>

        {/* FAQ */}
        <section className="py-16">
          <Reveal>
            <div className="mb-8 text-center">
              <p className="text-[11px] uppercase tracking-luxe text-gilt-soft">
                Questions
              </p>
              <h2 className="mt-2 font-display text-3xl text-white sm:text-4xl">
                Frequently asked.
              </h2>
            </div>
          </Reveal>
          <Reveal delay={0.05}>
            <div className="mx-auto max-w-3xl">
              <FaqAccordion faqs={FAQS} />
            </div>
          </Reveal>
        </section>

        {/* Final CTA */}
        <section className="py-16">
          <Reveal>
            <div className="relative overflow-hidden rounded-3xl border border-gilt/25 bg-gradient-to-br from-ink-700 via-ink-800 to-ink-900 p-10 text-center shadow-glow sm:p-16">
              <div className="absolute inset-0 bg-grain [background-size:22px_22px] opacity-40" />
              <div className="relative">
                <h2 className="mx-auto max-w-2xl text-balance font-display text-3xl text-white sm:text-4xl">
                  {FINAL_CTA.title}
                </h2>
                <p className="mx-auto mt-4 max-w-md text-balance text-white/60">
                  {FINAL_CTA.subtitle}
                </p>
                <Link
                  href={FINAL_CTA.cta.href}
                  className="mt-8 inline-flex rounded-full bg-gilt px-7 py-3 text-sm font-semibold text-ink-900 transition hover:bg-gilt-soft active:scale-[0.98]"
                >
                  {FINAL_CTA.cta.label}
                </Link>
              </div>
            </div>
          </Reveal>
        </section>
      </div>
    </>
  );
}
