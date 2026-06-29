"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useEffect, useState } from "react";
import type { User } from "@supabase/supabase-js";
import { createClient } from "@/lib/supabase/client";
import { isSupabaseConfigured } from "@/lib/env";
import { signout } from "@/app/auth/actions";
import { Logo } from "@/components/Logo";

export function Header() {
  const pathname = usePathname();
  const configured = isSupabaseConfigured();
  const [user, setUser] = useState<User | null>(null);
  const [loading, setLoading] = useState<boolean>(configured);

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

  const isActive = (href: string) =>
    href === "/" ? pathname === "/" : pathname.startsWith(href);

  return (
    <header className="sticky top-0 z-40 border-b border-white/[0.06] bg-ink-900/80 backdrop-blur-xl">
      <div className="mx-auto flex h-16 max-w-6xl items-center justify-between gap-4 px-5">
        <Link href="/" className="flex items-center gap-2.5">
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

        <nav className="flex items-center gap-1 text-sm">
          <NavLink href="/" active={isActive("/")}>
            Discover
          </NavLink>
          <NavLink href="/collection" active={isActive("/collection")}>
            Collection
          </NavLink>

          <span className="mx-2 hidden h-5 w-px bg-white/10 sm:block" />

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
              <NavLink href="/login" active={isActive("/login")}>
                Log in
              </NavLink>
              <Link
                href="/signup"
                className="rounded-full bg-gilt px-4 py-1.5 text-sm font-medium text-ink-900 transition hover:bg-gilt-soft"
              >
                Sign up
              </Link>
            </>
          )}
        </nav>
      </div>
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
      className={`rounded-full px-3 py-1.5 transition ${
        active
          ? "bg-white/[0.06] text-white"
          : "text-white/60 hover:text-white"
      }`}
    >
      {children}
    </Link>
  );
}
