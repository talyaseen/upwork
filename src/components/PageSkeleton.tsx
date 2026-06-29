/** Generic shimmer skeleton used as route-level loading UI (streams via
 *  App Router Suspense while the server component fetches). */
export function PageSkeleton() {
  return (
    <div className="mx-auto max-w-6xl px-5 pb-12">
      <div className="pt-7">
        <div className="shimmer h-[260px] rounded-3xl border border-white/[0.06] bg-ink-700/50 sm:h-[300px]" />
      </div>
      <div className="mt-8 grid grid-cols-2 gap-4 lg:grid-cols-4">
        {Array.from({ length: 4 }).map((_, i) => (
          <div
            key={i}
            className="shimmer h-24 rounded-2xl border border-white/[0.06] bg-ink-700/40"
          />
        ))}
      </div>
      <div className="mt-6 grid grid-cols-1 gap-6 lg:grid-cols-3">
        <div className="shimmer h-72 rounded-3xl border border-white/[0.06] bg-ink-700/40 lg:col-span-2" />
        <div className="shimmer h-72 rounded-3xl border border-white/[0.06] bg-ink-700/40" />
      </div>
    </div>
  );
}
