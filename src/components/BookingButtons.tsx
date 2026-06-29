import { bookingLinks } from "@/lib/booking";
import type { Property } from "@/lib/types";

/**
 * Affiliate-style booking deep links to the major OTAs. Open in a new tab and
 * work for anonymous and authenticated visitors alike.
 */
export function BookingButtons({ property }: { property: Property }) {
  const links = bookingLinks(property);

  return (
    <div className="grid grid-cols-1 gap-2.5 sm:grid-cols-3">
      {links.map((link) => (
        <a
          key={link.partner}
          href={link.url}
          target="_blank"
          rel="noopener noreferrer nofollow"
          className="group flex items-center justify-center gap-2 rounded-xl border border-gilt/25 bg-gilt/[0.06] px-4 py-3 text-sm font-medium text-gilt-soft transition hover:border-gilt/50 hover:bg-gilt/10"
        >
          <span>
            Book on <span className="text-white">{link.partner}</span>
          </span>
          <svg
            width="14"
            height="14"
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor"
            strokeWidth="2"
            strokeLinecap="round"
            strokeLinejoin="round"
            className="transition-transform group-hover:translate-x-0.5 group-hover:-translate-y-0.5"
            aria-hidden="true"
          >
            <path d="M7 17 17 7" />
            <path d="M7 7h10v10" />
          </svg>
        </a>
      ))}
    </div>
  );
}
