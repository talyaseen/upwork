import { INTELLIGENCE_LEVELS } from "@/lib/intelligence";
import { LevelBadge } from "@/components/LevelBadge";

/**
 * Explains the five intelligence levels: a signal-tier classification layered
 * on top of the raw rate delta.
 */
export function IntelligenceLegend() {
  return (
    <div className="rounded-3xl border border-white/[0.08] bg-ink-700/50 p-6 sm:p-7">
      <div className="flex flex-wrap items-end justify-between gap-2">
        <div>
          <h2 className="font-display text-xl text-white">
            Five intelligence levels
          </h2>
          <p className="mt-1 text-sm text-white/45">
            Every rate is graded against its own history, from at-market to
            exceptional.
          </p>
        </div>
      </div>

      <div className="mt-5 grid grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-5">
        {INTELLIGENCE_LEVELS.map((lvl) => (
          <div
            key={lvl.level}
            className="rounded-2xl border border-white/[0.06] bg-ink-800/60 p-4"
          >
            <LevelBadge level={lvl.level} />
            <p className="mt-2.5 text-xs leading-relaxed text-white/50">
              {lvl.description}
            </p>
          </div>
        ))}
      </div>
    </div>
  );
}
