import type { Metadata } from "next";
import Link from "next/link";
import { getSessionEmail } from "@/lib/data";
import { isSupabaseConfigured } from "@/lib/env";
import { signout } from "@/app/auth/actions";
import { LOYALTY_ACCOUNT, LOYALTY_TIERS } from "@/lib/demo-data";
import { PageHeader } from "@/components/PageHeader";
import { Reveal } from "@/components/motion";
import { COLLECTION_IMAGE } from "@/lib/images";

export const dynamic = "force-dynamic";
export const metadata: Metadata = {
  title: "Account",
  description: "Manage your AURUM profile, membership and preferences.",
};

const LINKS = [
  { href: "/alerts", title: "Alert preferences", body: "Thresholds, frequency and the experiences you care about." },
  { href: "/collection", title: "Your collection", body: "The stays you have saved to watch." },
  { href: "/reserve", title: "Reserve membership", body: "Your tier, credits and privileges." },
  { href: "/dashboard", title: "Market dashboard", body: "The tracked market at a glance." },
];

export default async function AccountPage() {
  const configured = isSupabaseConfigured();
  const email = await getSessionEmail();
  const tier = LOYALTY_TIERS.find((t) => t.id === LOYALTY_ACCOUNT.tierId);

  return (
    <div className="mx-auto max-w-6xl px-5 pb-12">
      <div className="pt-7">
        <PageHeader
          image={COLLECTION_IMAGE}
          eyebrow="Account"
          title="Your AURUM account."
          subtitle="Profile, membership and the settings that shape your briefings."
        />
      </div>

      {!configured || !email ? (
        <Reveal className="mt-8">
          <div className="rounded-3xl border border-gilt/20 bg-gilt/[0.05] p-12 text-center">
            <p className="font-display text-2xl text-white">
              Sign in to manage your account
            </p>
            <p className="mx-auto mt-3 max-w-md text-sm leading-relaxed text-white/55">
              {configured
                ? "Log in to view your profile, membership and preferences."
                : "Running in demo mode. Connect a Supabase project to enable accounts."}
            </p>
            <div className="mt-6 flex justify-center gap-3">
              <Link
                href="/login?next=/account"
                className="rounded-full bg-gilt px-5 py-2.5 text-sm font-semibold text-ink-900 transition hover:bg-gilt-soft"
              >
                Log in
              </Link>
              <Link
                href="/signup"
                className="rounded-full border border-white/15 px-5 py-2.5 text-sm text-white/80 transition hover:border-white/30 hover:text-white"
              >
                Create account
              </Link>
            </div>
          </div>
        </Reveal>
      ) : (
        <div className="mt-8 space-y-6">
          {/* Profile */}
          <Reveal>
            <section className="rounded-3xl border border-white/[0.08] bg-ink-700/50 p-6 sm:p-8">
              <div className="flex flex-wrap items-center justify-between gap-4">
                <div className="flex items-center gap-4">
                  <div
                    className="flex h-14 w-14 items-center justify-center rounded-2xl font-display text-xl text-ink-900"
                    style={{
                      backgroundImage:
                        "linear-gradient(135deg, #d9bd86, #a37e3c)",
                    }}
                  >
                    {email.slice(0, 1).toUpperCase()}
                  </div>
                  <div>
                    <p className="font-display text-xl text-white">{email}</p>
                    <p className="text-sm text-white/45">
                      {tier ? `${tier.name} member` : "Member"} · Reserve credits{" "}
                      {LOYALTY_ACCOUNT.credits.toLocaleString("en-US")}
                    </p>
                  </div>
                </div>
                <form action={signout}>
                  <button
                    type="submit"
                    className="rounded-full border border-white/15 px-5 py-2.5 text-sm text-white/80 transition hover:border-white/30 hover:text-white"
                  >
                    Sign out
                  </button>
                </form>
              </div>
            </section>
          </Reveal>

          {/* Quick links */}
          <Reveal delay={0.05}>
            <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
              {LINKS.map((l) => (
                <Link
                  key={l.href}
                  href={l.href}
                  className="group rounded-3xl border border-white/[0.08] bg-ink-700/40 p-6 transition hover:-translate-y-0.5 hover:border-white/20"
                >
                  <div className="flex items-center justify-between">
                    <h2 className="font-display text-lg text-white">
                      {l.title}
                    </h2>
                    <span className="text-gilt-soft transition group-hover:translate-x-0.5">
                      &rarr;
                    </span>
                  </div>
                  <p className="mt-1.5 text-sm text-white/50">{l.body}</p>
                </Link>
              ))}
            </div>
          </Reveal>
        </div>
      )}
    </div>
  );
}
