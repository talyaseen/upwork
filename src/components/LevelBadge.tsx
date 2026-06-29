import { levelMeta } from "@/lib/intelligence";

const TONE: Record<number, string> = {
  5: "border-gilt/55 bg-gilt/25 text-gilt-soft",
  4: "border-gilt/40 bg-gilt/15 text-gilt-soft",
  3: "border-white/15 bg-white/[0.06] text-white/70",
  2: "border-white/10 bg-white/[0.04] text-white/55",
  1: "border-white/10 bg-white/[0.03] text-white/40",
};

export function LevelBadge({
  level,
  showLabel = true,
  className = "",
}: {
  level: number;
  showLabel?: boolean;
  className?: string;
}) {
  const meta = levelMeta(level);
  return (
    <span
      title={`Intelligence level ${level}: ${meta.label}`}
      className={`inline-flex items-center gap-1.5 rounded-full border px-2.5 py-0.5 text-[11px] font-medium ${TONE[level] ?? TONE[1]} ${className}`}
    >
      <span className="font-display tracking-wide">{meta.short}</span>
      {showLabel && <span>{meta.label}</span>}
    </span>
  );
}
