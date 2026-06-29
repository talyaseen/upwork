interface Props {
  name: "signal" | "chart" | "bell" | "crown";
  className?: string;
}

export function FeatureIcon({ name, className = "" }: Props) {
  const common = {
    width: 22,
    height: 22,
    viewBox: "0 0 24 24",
    fill: "none",
    stroke: "currentColor",
    strokeWidth: 1.6,
    strokeLinecap: "round" as const,
    strokeLinejoin: "round" as const,
    className,
    "aria-hidden": true,
  };

  switch (name) {
    case "signal":
      return (
        <svg {...common}>
          <path d="M4 20v-4" />
          <path d="M10 20V10" />
          <path d="M16 20V6" />
          <path d="M22 20v-8" />
        </svg>
      );
    case "chart":
      return (
        <svg {...common}>
          <path d="M3 3v18h18" />
          <path d="M7 14l4-4 3 3 5-6" />
        </svg>
      );
    case "bell":
      return (
        <svg {...common}>
          <path d="M6 9a6 6 0 0 1 12 0c0 5 2 6 2 6H4s2-1 2-6" />
          <path d="M10 20a2 2 0 0 0 4 0" />
        </svg>
      );
    case "crown":
      return (
        <svg {...common}>
          <path d="M3 7l4 4 5-6 5 6 4-4v10H3z" />
        </svg>
      );
    default:
      return null;
  }
}
