export default function Loading() {
  return (
    <div className="mx-auto max-w-6xl px-5 pb-10">
      <div className="pt-8">
        <div className="h-4 w-32 animate-pulse rounded bg-white/[0.05]" />
      </div>

      {/* Hero skeleton */}
      <div className="mt-4 h-[340px] animate-pulse rounded-3xl border border-white/[0.06] bg-ink-700/60 sm:h-[440px]" />

      <div className="mt-8 grid grid-cols-1 gap-6 lg:grid-cols-3">
        <div className="lg:col-span-2">
          <div className="rounded-3xl border border-white/[0.06] bg-ink-700/50 p-6">
            <div className="h-6 w-40 animate-pulse rounded bg-white/[0.05]" />
            <div className="mt-5 h-40 animate-pulse rounded-xl bg-white/[0.03]" />
            <div className="mt-5 space-y-3">
              {Array.from({ length: 5 }).map((_, i) => (
                <div
                  key={i}
                  className="h-5 w-full animate-pulse rounded bg-white/[0.04]"
                />
              ))}
            </div>
          </div>
        </div>
        <div className="lg:col-span-1">
          <div className="rounded-3xl border border-white/[0.06] bg-ink-700/50 p-6">
            <div className="h-10 w-2/3 animate-pulse rounded bg-white/[0.05]" />
            <div className="mt-5 h-11 w-full animate-pulse rounded-full bg-white/[0.04]" />
            <div className="mt-6 space-y-2.5">
              {Array.from({ length: 3 }).map((_, i) => (
                <div
                  key={i}
                  className="h-12 w-full animate-pulse rounded-xl bg-white/[0.03]"
                />
              ))}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
