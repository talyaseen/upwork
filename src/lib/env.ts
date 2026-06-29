/**
 * True when both Supabase env vars are present. When false the app runs in
 * "demo mode": data comes from bundled illustrative sample data and auth /
 * collections are disabled. This lets the project build and preview with zero
 * configuration and no network calls.
 */
export function isSupabaseConfigured(): boolean {
  return (
    !!process.env.NEXT_PUBLIC_SUPABASE_URL &&
    !!process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY
  );
}
