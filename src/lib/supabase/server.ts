import { createServerClient, type CookieOptions } from "@supabase/ssr";
import { cookies } from "next/headers";

type CookieToSet = { name: string; value: string; options: CookieOptions };

/**
 * Server-side Supabase client (Server Components, Route Handlers, Server
 * Actions). Wires Supabase's auth cookies through Next's cookie store so that
 * sessions persist and RLS sees the authenticated user.
 *
 * In Next 15 `cookies()` is async, hence the `await`.
 */
export async function createClient() {
  const cookieStore = await cookies();

  return createServerClient(
    process.env.NEXT_PUBLIC_SUPABASE_URL!,
    process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY!,
    {
      cookies: {
        getAll() {
          return cookieStore.getAll();
        },
        setAll(cookiesToSet: CookieToSet[]) {
          try {
            cookiesToSet.forEach(({ name, value, options }) =>
              cookieStore.set(name, value, options),
            );
          } catch {
            // `setAll` is called from a Server Component where mutating cookies
            // is not allowed. This is safe to ignore when middleware is in
            // charge of refreshing the session.
          }
        },
      },
    },
  );
}
