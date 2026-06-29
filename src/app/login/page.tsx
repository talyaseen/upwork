import Link from "next/link";
import { login } from "@/app/auth/actions";
import { isSupabaseConfigured } from "@/lib/env";
import { SubmitButton } from "@/components/SubmitButton";
import { AuthField } from "@/components/AuthField";

interface PageProps {
  searchParams: Promise<{ error?: string; notice?: string; next?: string }>;
}

export default async function LoginPage({ searchParams }: PageProps) {
  const { error, notice, next } = await searchParams;
  const configured = isSupabaseConfigured();

  return (
    <div className="mx-auto flex max-w-md flex-col px-5 py-16 sm:py-24">
      <div className="rounded-3xl border border-white/[0.08] bg-ink-700/60 p-7 sm:p-8">
        <p className="text-[11px] uppercase tracking-luxe text-gilt-soft">
          Welcome back
        </p>
        <h1 className="mt-2 font-display text-3xl text-white">Log in</h1>
        <p className="mt-2 text-sm text-white/50">
          Access your saved collection of stays.
        </p>

        {!configured && (
          <p className="mt-5 rounded-xl border border-gilt/25 bg-gilt/[0.06] px-4 py-3 text-sm text-gilt-soft">
            Demo mode: authentication needs a Supabase project. Add your keys to{" "}
            <code className="text-white/80">.env.local</code> to enable sign in.
          </p>
        )}

        {error && (
          <p className="mt-5 rounded-xl border border-red-400/25 bg-red-400/[0.06] px-4 py-3 text-sm text-red-200">
            {error === "demo"
              ? "Authentication is disabled in demo mode. Connect Supabase to continue."
              : error}
          </p>
        )}

        {notice === "check-email" && (
          <p className="mt-5 rounded-xl border border-gilt/25 bg-gilt/[0.06] px-4 py-3 text-sm text-gilt-soft">
            Account created. Check your email to confirm, then log in.
          </p>
        )}

        <form action={login} className="mt-6 space-y-4">
          <input type="hidden" name="next" value={next ?? "/collection"} />
          <AuthField
            id="email"
            name="email"
            type="email"
            label="Email"
            placeholder="you@example.com"
            autoComplete="email"
          />
          <AuthField
            id="password"
            name="password"
            type="password"
            label="Password"
            placeholder="••••••••"
            autoComplete="current-password"
          />
          <SubmitButton
            className="mt-2 w-full rounded-full bg-gilt px-4 py-2.5 text-sm font-semibold text-ink-900 transition hover:bg-gilt-soft"
            pendingLabel="Signing in..."
          >
            Log in
          </SubmitButton>
        </form>

        <p className="mt-6 text-center text-sm text-white/45">
          New here?{" "}
          <Link href="/signup" className="text-gilt-soft hover:text-gilt">
            Create an account
          </Link>
        </p>
      </div>
    </div>
  );
}
