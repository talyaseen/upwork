import { formatRate } from "@/lib/format";
import type { SignalProperty } from "@/lib/types";
import { Logo } from "@/components/Logo";

/**
 * A styled preview of the "weekly rate briefing" email a subscriber receives.
 * Uses gradient swatches (no image loads) so it renders instantly.
 */
export function EmailDigestPreview({
  properties,
}: {
  properties: SignalProperty[];
}) {
  return (
    <div className="overflow-hidden rounded-3xl border border-white/[0.1] bg-ink-800/80 shadow-card">
      {/* Email client chrome */}
      <div className="flex items-center justify-between border-b border-white/[0.06] px-5 py-3 text-xs text-white/40">
        <span>AURUM &lt;briefings@aurum.travel&gt;</span>
        <span>Mon, 06:00</span>
      </div>

      <div className="p-6 sm:p-7">
        <div className="flex items-center gap-2">
          <Logo className="h-5 w-5" />
          <span className="font-display tracking-wide text-white">AURUM</span>
        </div>

        <h3 className="mt-4 font-display text-2xl text-white">
          Your weekly rate briefing
        </h3>
        <p className="mt-1 text-sm text-white/50">
          {properties.length} stays just dropped below their historical average.
        </p>

        <div className="mt-5 space-y-3">
          {properties.map((p) => (
            <div
              key={p.id}
              className="flex items-center gap-3 rounded-2xl border border-white/[0.06] bg-ink-700/60 p-3"
            >
              <div
                className="h-12 w-12 shrink-0 rounded-lg"
                style={{
                  backgroundImage: `linear-gradient(135deg, ${p.accent_from}, ${p.accent_to})`,
                }}
              />
              <div className="min-w-0 flex-1">
                <p className="truncate text-sm text-white">{p.name}</p>
                <p className="truncate text-xs text-white/40">
                  {p.destination}
                </p>
              </div>
              <div className="text-right">
                <p className="font-display text-gilt-soft">
                  {formatRate(p.current_rate, p.currency)}
                </p>
                <p className="text-[11px] text-white/35">
                  -{p.signal.belowPct}% vs avg
                </p>
              </div>
            </div>
          ))}
        </div>

        <div className="mt-6">
          <span className="inline-flex rounded-full bg-gilt px-5 py-2.5 text-sm font-semibold text-ink-900">
            View the full briefing
          </span>
        </div>

        <p className="mt-6 text-[11px] leading-relaxed text-white/30">
          You receive this because you subscribed to weekly rate alerts. Manage
          preferences or unsubscribe at any time.
        </p>
      </div>
    </div>
  );
}
