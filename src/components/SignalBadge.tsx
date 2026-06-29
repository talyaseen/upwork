import type { RateSignal } from "@/lib/types";

interface Props {
  signal: RateSignal;
  className?: string;
}

/**
 * Renders the rate signal. When the current rate is meaningfully below the
 * historical average it shows a pulsing "Rate Alert" pill; otherwise a quiet
 * delta indicator.
 */
export function SignalBadge({ signal, className = "" }: Props) {
  if (signal.isAlert) {
    return (
      <span
        className={`inline-flex items-center gap-2 rounded-full border border-gilt/40 bg-gilt/15 px-3 py-1 text-xs font-medium text-gilt-soft shadow-[0_2px_12px_-4px_rgba(200,162,90,0.5)] backdrop-blur-sm ${className}`}
      >
        <span className="relative flex h-1.5 w-1.5">
          <span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-gilt opacity-60" />
          <span className="relative inline-flex h-1.5 w-1.5 rounded-full bg-gilt" />
        </span>
        Rate Alert {signal.deltaPct}% vs avg
      </span>
    );
  }

  const up = signal.deltaPct > 0;
  const label =
    signal.deltaPct === 0
      ? "On par with avg"
      : `${up ? "+" : ""}${signal.deltaPct}% vs avg`;

  return (
    <span
      className={`inline-flex items-center gap-1.5 rounded-full border border-white/10 bg-white/[0.03] px-3 py-1 text-xs font-medium text-white/55 ${className}`}
    >
      {label}
    </span>
  );
}
