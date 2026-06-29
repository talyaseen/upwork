interface Props {
  count: number;
  className?: string;
}

export function StarRating({ count, className = "" }: Props) {
  const stars = Math.max(0, Math.min(5, Math.round(count)));
  return (
    <span
      aria-label={`${stars} star property`}
      className={`select-none text-[0.7rem] tracking-[0.2em] text-gilt-soft ${className}`}
    >
      {"★".repeat(stars)}
    </span>
  );
}
