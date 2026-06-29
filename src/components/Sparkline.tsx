interface Props {
  data: number[];
  width?: number;
  height?: number;
  color?: string;
  gradientId?: string;
  className?: string;
}

/**
 * Lightweight inline SVG area-sparkline. No charting dependency: scales to its
 * container via a viewBox. The final data point is highlighted as "today".
 */
export function Sparkline({
  data,
  width = 720,
  height = 160,
  color = "#c8a25a",
  gradientId = "spark",
  className = "",
}: Props) {
  if (data.length < 2) return null;

  const pad = 10;
  const min = Math.min(...data);
  const max = Math.max(...data);
  const range = max - min || 1;
  const innerH = height - pad * 2;
  const stepX = width / (data.length - 1);

  const points = data.map((d, i) => {
    const x = i * stepX;
    const y = pad + innerH - ((d - min) / range) * innerH;
    return [x, y] as const;
  });

  const line = points
    .map(([x, y], i) => `${i === 0 ? "M" : "L"}${x.toFixed(1)},${y.toFixed(1)}`)
    .join(" ");
  const area = `${line} L${width.toFixed(1)},${height} L0,${height} Z`;
  const last = points[points.length - 1];

  return (
    <svg
      viewBox={`0 0 ${width} ${height}`}
      width="100%"
      height={height}
      preserveAspectRatio="none"
      className={className}
      role="img"
      aria-label="Rate history"
    >
      <defs>
        <linearGradient id={gradientId} x1="0" y1="0" x2="0" y2="1">
          <stop offset="0%" stopColor={color} stopOpacity="0.28" />
          <stop offset="100%" stopColor={color} stopOpacity="0" />
        </linearGradient>
      </defs>
      <path d={area} fill={`url(#${gradientId})`} />
      <path
        d={line}
        fill="none"
        stroke={color}
        strokeWidth="2"
        strokeLinecap="round"
        strokeLinejoin="round"
        vectorEffect="non-scaling-stroke"
      />
      <circle
        cx={last[0]}
        cy={last[1]}
        r="3.5"
        fill={color}
        vectorEffect="non-scaling-stroke"
      />
    </svg>
  );
}
