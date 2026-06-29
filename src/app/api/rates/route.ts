import { NextResponse } from "next/server";
import { getProperties } from "@/lib/data";

export const dynamic = "force-dynamic";

/**
 * GET /api/rates            - all tracked properties with their live signal
 * GET /api/rates?alert=true - only properties currently flagged as Rate Alerts
 *
 * A read-only JSON endpoint over the same typed data layer the pages use.
 */
export async function GET(request: Request) {
  const { searchParams } = new URL(request.url);
  const alertsOnly = searchParams.get("alert") === "true";

  const properties = await getProperties();
  const data = properties
    .filter((p) => (alertsOnly ? p.signal.isAlert : true))
    .map((p) => ({
      id: p.id,
      name: p.name,
      destination: p.destination,
      country: p.country,
      brand_id: p.brand_id,
      currency: p.currency,
      current_rate: p.current_rate,
      avg_rate: p.avg_rate,
      below_pct: p.signal.belowPct,
      level: p.signal.level,
      is_alert: p.signal.isAlert,
    }));

  return NextResponse.json(
    { count: data.length, generated_at: new Date().toISOString(), properties: data },
    { headers: { "cache-control": "no-store" } },
  );
}
