"use client";

import { motion } from "framer-motion";
import { AnimatedNumber } from "@/components/motion";
import { formatShortDate } from "@/lib/format";
import type { LoyaltyAccount, LoyaltyTier } from "@/lib/types";

const EASE = [0.22, 1, 0.36, 1] as const;

export function ReserveDashboard({
  account,
  tiers,
  memberName,
}: {
  account: LoyaltyAccount;
  tiers: LoyaltyTier[];
  memberName: string;
}) {
  const sorted = [...tiers].sort((a, b) => a.threshold - b.threshold);
  const currentIdx = Math.max(
    0,
    sorted.findIndex((t) => t.id === account.tierId),
  );
  const current = sorted[currentIdx];
  const next = sorted[currentIdx + 1] ?? null;
  const floor = current.threshold;
  const ceil = next ? next.threshold : current.threshold;
  const progress = next
    ? Math.min(1, Math.max(0, (account.credits - floor) / (ceil - floor)))
    : 1;
  const toNext = next ? Math.max(0, ceil - account.credits) : 0;

  return (
    <div className="space-y-6">
      {/* Membership card */}
      <div className="relative overflow-hidden rounded-3xl border border-gilt/25 bg-gradient-to-br from-ink-600 via-ink-800 to-ink-900 p-7 shadow-glow sm:p-9">
        <div className="absolute inset-0 bg-grain [background-size:22px_22px] opacity-40" />
        <div className="relative flex items-start justify-between">
          <div>
            <p className="text-xs uppercase tracking-luxe text-gilt-soft">
              AURUM Reserve
            </p>
            <p className="mt-1.5 font-display text-2xl text-white">
              {memberName}
            </p>
          </div>
          <span className="rounded-full border border-gilt/40 bg-gilt/10 px-3 py-1 font-display text-sm text-gilt-soft">
            {current.name}
          </span>
        </div>
        <div className="relative mt-9 flex items-end justify-between gap-4">
          <div>
            <p className="text-[11px] uppercase tracking-luxe text-white/40">
              Reserve credits
            </p>
            <AnimatedNumber
              value={account.credits}
              className="font-display text-4xl text-gilt-soft sm:text-5xl"
            />
          </div>
          <div className="text-right">
            <p className="text-[11px] uppercase tracking-luxe text-white/40">
              Nights this year
            </p>
            <AnimatedNumber
              value={account.ytdNights}
              className="font-display text-3xl text-white"
            />
          </div>
        </div>
      </div>

      {/* Progress to next tier */}
      <div className="rounded-3xl border border-white/[0.08] bg-ink-700/50 p-6 sm:p-7">
        <div className="flex items-baseline justify-between text-sm">
          <span className="text-white/70">{current.name}</span>
          {next ? (
            <span className="text-white/45">
              {toNext.toLocaleString("en-US")} credits to {next.name}
            </span>
          ) : (
            <span className="text-gilt-soft">Top tier reached</span>
          )}
        </div>
        <div className="mt-2.5 h-2 overflow-hidden rounded-full bg-white/[0.06]">
          <motion.div
            initial={{ width: 0 }}
            whileInView={{ width: `${progress * 100}%` }}
            viewport={{ once: true }}
            transition={{ duration: 1.1, ease: EASE }}
            className="h-full rounded-full bg-gradient-to-r from-gilt-deep to-gilt-soft"
          />
        </div>

        <div className="mt-6 grid grid-cols-2 gap-3 sm:grid-cols-4">
          {sorted.map((t) => {
            const achieved = account.credits >= t.threshold;
            const isCurrent = t.id === current.id;
            return (
              <div
                key={t.id}
                className={`rounded-2xl border p-4 ${
                  isCurrent
                    ? "border-gilt/50 bg-gilt/10"
                    : achieved
                      ? "border-white/15 bg-white/[0.04]"
                      : "border-white/[0.06] bg-ink-800/40"
                }`}
              >
                <p
                  className={`font-display text-lg ${achieved ? "text-gilt-soft" : "text-white/50"}`}
                >
                  {t.name}
                </p>
                <p className="text-[11px] text-white/35">
                  {t.threshold.toLocaleString("en-US")} credits
                </p>
                <p className="mt-2 text-xs leading-snug text-white/45">
                  {t.benefit}
                </p>
              </div>
            );
          })}
        </div>
      </div>

      {/* Activity + perks */}
      <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
        <div className="rounded-3xl border border-white/[0.08] bg-ink-700/50 p-6 sm:p-7">
          <h2 className="font-display text-xl text-white">Recent activity</h2>
          <ul className="mt-4 divide-y divide-white/[0.06]">
            {account.history.map((h, i) => (
              <motion.li
                key={`${h.date}-${i}`}
                initial={{ opacity: 0, x: -10 }}
                whileInView={{ opacity: 1, x: 0 }}
                viewport={{ once: true, margin: "-30px" }}
                transition={{ duration: 0.45, delay: i * 0.05, ease: EASE }}
                className="flex items-center justify-between gap-3 py-3"
              >
                <div className="min-w-0">
                  <p className="truncate text-sm text-white/80">{h.label}</p>
                  <p className="text-xs text-white/35">
                    {formatShortDate(h.date)}
                  </p>
                </div>
                <span className="shrink-0 font-display text-gilt-soft">
                  +{h.credits.toLocaleString("en-US")}
                </span>
              </motion.li>
            ))}
          </ul>
        </div>

        <div className="rounded-3xl border border-white/[0.08] bg-ink-700/50 p-6 sm:p-7">
          <h2 className="font-display text-xl text-white">Your privileges</h2>
          <ul className="mt-4 space-y-3">
            {account.perks.map((perk) => (
              <li
                key={perk}
                className="flex items-start gap-3 text-sm text-white/70"
              >
                <span className="mt-0.5 flex h-5 w-5 shrink-0 items-center justify-center rounded-full border border-gilt/40 bg-gilt/10 text-[11px] text-gilt-soft">
                  ✓
                </span>
                {perk}
              </li>
            ))}
          </ul>
        </div>
      </div>
    </div>
  );
}
