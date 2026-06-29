"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useEffect, useState } from "react";
import { AnimatePresence, motion } from "framer-motion";
import type { User } from "@supabase/supabase-js";
import { createClient } from "@/lib/supabase/client";
import { isSupabaseConfigured } from "@/lib/env";
import { signout } from "@/app/auth/actions";
import { Logo } from "@/components/Logo";

const NAV = [
  { href: "/briefing", label: "Briefing" },
  { href: "/dashboard", label: "Dashboard" },
  { href: "/view", label: "The View" },
  { href: "/collection", label: "Collection" },
  { href: "/reserve", label: "Reserve" },
  { href: "/alerts", label: "Alerts" },
];

export function Header() {
  const pathname = usePathname();
  const configured = isSupabaseConfigured();
  const [user, setUser] = useState<User | null>(null);
  const [loading, setLoading] = useState<boolean>(configured);
  const [open, setOpen] = useState(false);

  useEffect(() => {
    if (!configured) return;
    const supabase = createClient();
    let active = true;

    supabase.auth.getUser().then(({ data }) => {
      if (!active) return;
      setUser(data.user);
      setLoading(false);
    });

    const {
      data: { subscription },
    } = supabase.auth.onAuthStateChange((_event, session) => {
      setUser(session?.user ?? null);
      setLoading(false);
    });

    return () => {
      active = false;
      subscription.unsubscribe();
    };
  }, [configured]);

  // Close the mobile drawer on navigation.
  useEffect(() => setOpen(false), [pathname]);

  const isActive = (href: string) =>
    href === "/" ? pathname === "/" : pathname.startsWith(href);

  const auth = (
    <>
      {!configured ? (
        <span className="rounded-full border border-white/10 bg-white/[0.03] px-3 py-1.5 text-xs text-white/45">
          Demo mode
        </span>
      ) : loading ? (
        <span className="h-8 w-20 animate-pulse rounded-full bg-white/5" />
      ) : user ? (
        <form action={signout}>
          <button
            type="submit"
            className="rounded-full border border-white/12 bg-white/[0.03] px-4 py-1.5 text-sm text-white/75 transition hover:border-white/25 hover:text-white"
          >
            Sign out
          </button>
        </form>
      ) : (
        <>
          <Link
            href="/login"
            className="rounded-full px-3 py-1.5 text-sm text-white/60 transition hover:text-white"
          >
            Log in
          </Link>
          <Link
            href="/signup"
            className="rounded-full bg-gilt px-4 py-1.5 text-sm font-medium text-ink-900 transition hover:bg-gilt-soft"
          >
            Sign up
          </Link>
        </>
      )}
    </>
  );

  return (
    <header className="sticky top-0 z-40 border-b border-white/[0.06] bg-ink-900/80 backdrop-blur-xl">
      <div className="mx-auto flex h-16 max-w-6xl items-center justify-between gap-3 px-5">
        <Link href="/" className="flex shrink-0 items-center gap-2.5">
          <Logo />
          <span className="flex flex-col leading-none">
            <span className="font-display text-lg tracking-wide text-white">
              AURUM
            </span>
            <span className="hidden text-[9px] uppercase tracking-luxe text-gilt/70 sm:block">
              Rate Intelligence
            </span>
          </span>
        </Link>

        {/* Desktop nav */}
        <nav className="hidden items-center gap-1 text-sm lg:flex">
          {NAV.map((item) => (
            <NavLink
              key={item.href}
              href={item.href}
              active={isActive(item.href)}
            >
              {item.label}
            </NavLink>
          ))}
        </nav>

        <div className="flex items-center gap-2">
          <div className="hidden items-center gap-2 lg:flex">{auth}</div>

          {/* Mobile menu toggle */}
          <button
            type="button"
            onClick={() => setOpen((o) => !o)}
            aria-label={open ? "Close menu" : "Open menu"}
            aria-expanded={open}
            className="flex h-10 w-10 items-center justify-center rounded-full border border-white/10 bg-white/[0.03] text-white/80 transition hover:text-white lg:hidden"
          >
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round">
              {open ? (
                <>
                  <path d="M6 6l12 12" />
                  <path d="M18 6 6 18" />
                </>
              ) : (
                <>
                  <path d="M3 6h18" />
                  <path d="M3 12h18" />
                  <path d="M3 18h18" />
                </>
              )}
            </svg>
          </button>
        </div>
      </div>

      {/* Mobile drawer */}
      <AnimatePresence>
        {open && (
          <motion.div
            initial={{ opacity: 0, height: 0 }}
            animate={{ opacity: 1, height: "auto" }}
            exit={{ opacity: 0, height: 0 }}
            transition={{ duration: 0.28, ease: [0.22, 1, 0.36, 1] }}
            className="overflow-hidden border-t border-white/[0.06] lg:hidden"
          >
            <nav className="mx-auto flex max-w-6xl flex-col gap-1 px-5 py-4">
              {NAV.map((item) => (
                <Link
                  key={item.href}
                  href={item.href}
                  className={`rounded-xl px-4 py-3 text-base transition ${
                    isActive(item.href)
                      ? "bg-white/[0.06] text-white"
                      : "text-white/65 hover:bg-white/[0.03] hover:text-white"
                  }`}
                >
                  {item.label}
                </Link>
              ))}
              <div className="mt-2 flex items-center gap-2 border-t border-white/[0.06] pt-4">
                {auth}
              </div>
            </nav>
          </motion.div>
        )}
      </AnimatePresence>
    </header>
  );
}

function NavLink({
  href,
  active,
  children,
}: {
  href: string;
  active: boolean;
  children: React.ReactNode;
}) {
  return (
    <Link
      href={href}
      className={`whitespace-nowrap rounded-full px-3 py-1.5 transition ${
        active ? "bg-white/[0.06] text-white" : "text-white/60 hover:text-white"
      }`}
    >
      {children}
    </Link>
  );
}
