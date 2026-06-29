export function Logo({ className = "" }: { className?: string }) {
  return (
    <svg
      width="28"
      height="28"
      viewBox="0 0 32 32"
      fill="none"
      className={className}
      aria-hidden="true"
    >
      <defs>
        <linearGradient id="logo-gilt" x1="0" y1="0" x2="1" y2="1">
          <stop offset="0%" stopColor="#e3cd9a" />
          <stop offset="55%" stopColor="#c8a25a" />
          <stop offset="100%" stopColor="#a37e3c" />
        </linearGradient>
      </defs>
      <path
        d="M16 2 30 12 16 30 2 12Z"
        fill="url(#logo-gilt)"
        fillOpacity="0.18"
        stroke="url(#logo-gilt)"
        strokeWidth="1.4"
        strokeLinejoin="round"
      />
      <path
        d="M16 2 16 30M2 12h28M9 7l7 5 7-5M16 12l-5 6 5 12 5-12-5-6Z"
        stroke="url(#logo-gilt)"
        strokeWidth="1.1"
        strokeLinejoin="round"
        strokeLinecap="round"
        fill="none"
      />
    </svg>
  );
}
