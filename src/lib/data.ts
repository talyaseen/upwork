import "server-only";

import { createClient } from "@/lib/supabase/server";
import { isSupabaseConfigured } from "@/lib/env";
import { withSignal, withSignals } from "@/lib/rates";
import {
  DEMO_PROPERTIES,
  demoPropertyWithHistory,
} from "@/lib/demo-data";
import type {
  Property,
  PropertyWithHistory,
  RatePoint,
  SignalProperty,
} from "@/lib/types";

// Columns selected for a property row.
const PROPERTY_COLUMNS =
  "id, name, destination, country, description, star_rating, current_rate, avg_rate, currency, accent_from, accent_to, image_url, brand_id, tags";

/** Coerce a raw Supabase row into a strongly-typed Property (numeric safety). */
function mapProperty(row: Record<string, unknown>): Property {
  return {
    id: String(row.id),
    name: String(row.name),
    destination: String(row.destination),
    country: String(row.country ?? ""),
    description: String(row.description ?? ""),
    star_rating: Number(row.star_rating ?? 5),
    current_rate: Number(row.current_rate ?? 0),
    avg_rate: Number(row.avg_rate ?? 0),
    currency: String(row.currency ?? "USD"),
    accent_from: String(row.accent_from ?? "#1d1d28"),
    accent_to: String(row.accent_to ?? "#262633"),
    image_url: String(row.image_url ?? ""),
    brand_id: String(row.brand_id ?? ""),
    tags: Array.isArray(row.tags) ? (row.tags as unknown[]).map(String) : [],
  };
}

/**
 * All tracked properties, each enriched with its rate signal. Falls back to
 * bundled demo data when Supabase is unconfigured or unreachable.
 */
export async function getProperties(): Promise<SignalProperty[]> {
  if (!isSupabaseConfigured()) {
    return withSignals(DEMO_PROPERTIES);
  }

  try {
    const supabase = await createClient();
    const { data, error } = await supabase
      .from("properties")
      .select(PROPERTY_COLUMNS)
      .order("name", { ascending: true });

    if (error || !data || data.length === 0) {
      return withSignals(DEMO_PROPERTIES);
    }
    return withSignals(data.map(mapProperty));
  } catch {
    return withSignals(DEMO_PROPERTIES);
  }
}

/** A single property with its rate history, or null if it does not exist. */
export async function getProperty(
  id: string,
): Promise<PropertyWithHistory | null> {
  if (!isSupabaseConfigured()) {
    return demoPropertyWithHistory(id);
  }

  try {
    const supabase = await createClient();
    const { data: propertyRow, error } = await supabase
      .from("properties")
      .select(PROPERTY_COLUMNS)
      .eq("id", id)
      .maybeSingle();

    if (error || !propertyRow) {
      return demoPropertyWithHistory(id);
    }

    const { data: historyRows } = await supabase
      .from("rate_history")
      .select("captured_on, rate")
      .eq("property_id", id)
      .order("captured_on", { ascending: true });

    const history: RatePoint[] = (historyRows ?? []).map((r) => ({
      captured_on: String(r.captured_on),
      rate: Number(r.rate),
    }));

    return { ...mapProperty(propertyRow), history };
  } catch {
    return demoPropertyWithHistory(id);
  }
}

/** Email of the signed-in user, or null. Demo mode is always signed-out. */
export async function getSessionEmail(): Promise<string | null> {
  if (!isSupabaseConfigured()) return null;
  try {
    const supabase = await createClient();
    const {
      data: { user },
    } = await supabase.auth.getUser();
    return user?.email ?? null;
  } catch {
    return null;
  }
}

/** Set of property ids the current user has saved (empty when signed-out). */
export async function getSavedIds(): Promise<Set<string>> {
  if (!isSupabaseConfigured()) return new Set();
  try {
    const supabase = await createClient();
    const {
      data: { user },
    } = await supabase.auth.getUser();
    if (!user) return new Set();

    const { data } = await supabase
      .from("collections")
      .select("property_id")
      .eq("user_id", user.id);

    return new Set((data ?? []).map((r) => String(r.property_id)));
  } catch {
    return new Set();
  }
}

/** The current user's saved properties, enriched with rate signals. */
export async function getCollection(): Promise<SignalProperty[]> {
  if (!isSupabaseConfigured()) return [];
  try {
    const supabase = await createClient();
    const {
      data: { user },
    } = await supabase.auth.getUser();
    if (!user) return [];

    const { data, error } = await supabase
      .from("collections")
      .select(`property:properties(${PROPERTY_COLUMNS})`)
      .eq("user_id", user.id)
      .order("created_at", { ascending: false });

    if (error || !data) return [];

    return data
      .map((row) => {
        const raw = (row as { property: unknown }).property;
        const property = Array.isArray(raw) ? raw[0] : raw;
        return property
          ? withSignal(mapProperty(property as Record<string, unknown>))
          : null;
      })
      .filter((p): p is SignalProperty => p !== null);
  } catch {
    return [];
  }
}
