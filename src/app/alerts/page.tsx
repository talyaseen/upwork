import type { Metadata } from "next";
import { getProperties } from "@/lib/data";
import { byBestDeal } from "@/lib/rates";
import { PageHeader } from "@/components/PageHeader";
import { AlertPreferences } from "@/components/AlertPreferences";
import { EmailDigestPreview } from "@/components/EmailDigestPreview";
import { Reveal } from "@/components/motion";
import { ALERTS_IMAGE } from "@/lib/images";

export const dynamic = "force-dynamic";
export const metadata: Metadata = { title: "Alerts" };

export default async function AlertsPage() {
  const properties = await getProperties();
  const top = [...properties]
    .filter((p) => p.signal.isAlert)
    .sort(byBestDeal)
    .slice(0, 3);

  return (
    <div className="mx-auto max-w-6xl px-5 pb-12">
      <div className="pt-7">
        <PageHeader
          image={ALERTS_IMAGE}
          eyebrow="Alerts"
          title="Never miss the moment a rate drops."
          subtitle="Set your thresholds and interests, and we send a beautifully simple briefing the instant a stay moves below its average."
        />
      </div>

      <div className="mt-8 grid grid-cols-1 gap-6 lg:grid-cols-2">
        <Reveal>
          <AlertPreferences />
        </Reveal>

        <Reveal delay={0.05}>
          <div>
            <p className="mb-3 text-xs uppercase tracking-luxe text-white/40">
              Sample weekly digest
            </p>
            <EmailDigestPreview properties={top} />
          </div>
        </Reveal>
      </div>
    </div>
  );
}
