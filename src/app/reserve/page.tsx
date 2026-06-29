import type { Metadata } from "next";
import { getSessionEmail } from "@/lib/data";
import { LOYALTY_ACCOUNT, LOYALTY_TIERS } from "@/lib/demo-data";
import { PageHeader } from "@/components/PageHeader";
import { ReserveDashboard } from "@/components/ReserveDashboard";
import { RESERVE_IMAGE } from "@/lib/images";

export const dynamic = "force-dynamic";
export const metadata: Metadata = {
  title: "Reserve",
  description:
    "The AURUM Reserve loyalty programme: earn credits on every stay, climb the tiers and unlock privileges across the collection.",
};

function nameFromEmail(email: string | null): string {
  if (!email) return "Aurum Member";
  const local = email.split("@")[0].replace(/[._-]+/g, " ").trim();
  if (!local) return "Aurum Member";
  return local.replace(/\b\w/g, (c) => c.toUpperCase());
}

export default async function ReservePage() {
  const memberName = nameFromEmail(await getSessionEmail());

  return (
    <div className="mx-auto max-w-6xl px-5 pb-12">
      <div className="pt-7">
        <PageHeader
          image={RESERVE_IMAGE}
          eyebrow="Reserve"
          title="Your loyalty, elevated."
          subtitle="Earn Reserve credits on every stay, climb the tiers, and unlock privileges across the collection. Sample membership shown."
        />
      </div>

      <div className="mt-8">
        <ReserveDashboard
          account={LOYALTY_ACCOUNT}
          tiers={LOYALTY_TIERS}
          memberName={memberName}
        />
      </div>
    </div>
  );
}
