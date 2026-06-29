import { Logo } from "@/components/Logo";

export function Footer() {
  return (
    <footer className="mt-24 border-t border-white/[0.06]">
      <div className="mx-auto flex max-w-6xl flex-col gap-4 px-5 py-10 text-sm text-white/45 sm:flex-row sm:items-center sm:justify-between">
        <div className="flex items-center gap-2.5">
          <Logo className="opacity-80" />
          <div className="leading-tight">
            <p className="font-display text-base text-white/80">AURUM</p>
            <p className="text-xs">Rate intelligence for luxury stays</p>
          </div>
        </div>
        <p className="max-w-md text-xs leading-relaxed">
          Demo / portfolio build. Hotels and destinations are real; rates and
          rate history are illustrative sample data for demonstration only, not
          live or quoted prices.
        </p>
      </div>
    </footer>
  );
}
