import Link from "next/link";
import { signup } from "@/app/auth/actions";
import { isSupabaseConfigured } from "@/lib/env";
import { SubmitButton } from "@/components/SubmitButton";
import { AuthField } from "@/components/AuthField";

interface PageProps {
  searchParams: Promise<{ error?: string }>;
}

export default async function SignupPage({ searchParams }: PageProps) {
  const { error } = await searchParams;
  const configured = isSupabaseConfigured();

  return (
    <div className="mx-auto flex max-w-md flex-col px-5 py-16 sm:py-24">
      <div className="rounded-3xl border border-white/[0.08] bg-ink-700/60 p-7 sm:p-8">
        <p className="text-[11px] uppercase tracking-luxe text-gilt-soft">
          Join AURUM
        </p>
        <h1 className="mt-2 font-display text-3xl text-white">
          Create your account
        </h1>
        <p className="mt-2 text-sm text-white/50">
          Save stays and track when their rates drop.
        </p>

        {!configured && (
          <p className="mt-5 rounded-xl border border-gilt/25 bg-gilt/[0.06] px-4 py-3 text-sm text-gilt-soft">
            Demo mode: sign up needs a Supabase project. Add your keys to{" "}
            <code className="text-white/80">.env.local</code> to enable accounts.
          </p>
        )}

        {error && (
          <p className="mt-5 rounded-xl border border-red-400/25 bg-red-400/[0.06] px-4 py-3 text-sm text-red-200">
            {error === "demo"
              ? "Sign up is disabled in demo mode. Connect Supabase to continue."
              : error}
          </p>
        )}

        <form action={signup} className="mt-6 space-y-4">
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
            placeholder="At least 6 characters"
            autoComplete="new-password"
            minLength={6}
          />
          <SubmitButton
            className="mt-2 w-full rounded-full bg-gilt px-4 py-2.5 text-sm font-semibold text-ink-900 transition hover:bg-gilt-soft"
            pendingLabel="Creating account..."
          >
            Create account
          </SubmitButton>
        </form>

        <p className="mt-6 text-center text-sm text-white/45">
          Already have an account?{" "}
          <Link href="/login" className="text-gilt-soft hover:text-gilt">
            Log in
          </Link>
        </p>
      </div>
    </div>
  );
}
