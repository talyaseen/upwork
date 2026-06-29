import { createBrowserClient } from "@supabase/ssr";

/**
 * Browser-side Supabase client (used inside Client Components).
 * Reads the public env vars; both are safe to expose to the browser because
 * access is governed by Row Level Security.
 */
export function createClient() {
  return createBrowserClient(
    process.env.NEXT_PUBLIC_SUPABASE_URL!,
    process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY!,
  );
}
