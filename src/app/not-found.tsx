import Link from "next/link";

export default function NotFound() {
  return (
    <div className="mx-auto max-w-2xl px-5 py-28 text-center">
      <p className="font-display text-7xl text-gilt">404</p>
      <h1 className="mt-4 font-display text-2xl text-white">
        This stay could not be found
      </h1>
      <p className="mt-2 text-white/50">
        The page or property you are looking for is not here.
      </p>
      <Link
        href="/"
        className="mt-7 inline-flex rounded-full bg-gilt px-5 py-2.5 text-sm font-semibold text-ink-900 transition hover:bg-gilt-soft"
      >
        Back to all stays
      </Link>
    </div>
  );
}
