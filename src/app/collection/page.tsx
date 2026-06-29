import Link from "next/link";
import type { Metadata } from "next";
import { getCollection, getSessionEmail } from "@/lib/data";
import { isSupabaseConfigured } from "@/lib/env";
import { PropertyCard } from "@/components/PropertyCard";
import { SaveButton } from "@/components/SaveButton";
import { Stagger, StaggerItem } from "@/components/motion";

export const dynamic = "force-dynamic";

export const metadata: Metadata = {
  title: "Your collection",
};

export default async function CollectionPage() {
  const configured = isSupabaseConfigured();

  return (
    <div className="mx-auto max-w-6xl px-5 py-14">
      <header className="mb-8 border-b border-white/[0.06] pb-5">
        <p className="text-[11px] uppercase tracking-luxe text-gilt-soft">
          Saved stays
        </p>
        <h1 className="mt-2 font-display text-3xl text-white sm:text-4xl">
          Your collection
        </h1>
      </header>

      {!configured ? (
        <DemoNotice />
      ) : (
        <CollectionList />
      )}
    </div>
  );
}

async function CollectionList() {
  const [collection, email] = await Promise.all([
    getCollection(),
    getSessionEmail(),
  ]);

  if (collection.length === 0) {
    return (
      <div className="rounded-3xl border border-white/[0.08] bg-ink-700/40 p-12 text-center">
        <p className="font-display text-2xl text-white">
          Nothing saved yet
        </p>
        <p className="mx-auto mt-2 max-w-sm text-sm text-white/45">
          Tap the heart on any stay to keep an eye on its rate. Saved stays live
          here for quick comparison.
        </p>
        <Link
          href="/"
          className="mt-6 inline-flex rounded-full bg-gilt px-5 py-2.5 text-sm font-semibold text-ink-900 transition hover:bg-gilt-soft"
        >
          Discover stays
        </Link>
      </div>
    );
  }

  return (
    <>
      <p className="mb-6 text-sm text-white/45">
        {email && (
          <>
            Signed in as{" "}
            <span className="text-white/70">{email}</span> ·{" "}
          </>
        )}
        {collection.length} saved {collection.length === 1 ? "stay" : "stays"}
      </p>

      <Stagger className="grid grid-cols-1 gap-5 sm:grid-cols-2 lg:grid-cols-3">
        {collection.map((property) => (
          <StaggerItem key={property.id} className="relative">
            <PropertyCard property={property} />
            <div className="absolute right-3 top-3 z-10">
              <SaveButton
                propertyId={property.id}
                saved
                redirectTo="/collection"
                variant="icon"
              />
            </div>
          </StaggerItem>
        ))}
      </Stagger>
    </>
  );
}

function DemoNotice() {
  return (
    <div className="rounded-3xl border border-gilt/20 bg-gilt/[0.05] p-12 text-center">
      <p className="font-display text-2xl text-white">Collections are live</p>
      <p className="mx-auto mt-3 max-w-md text-sm leading-relaxed text-white/55">
        This is running in demo mode with bundled sample data. Connect a Supabase
        project (add your keys to{" "}
        <code className="text-gilt-soft">.env.local</code> and apply{" "}
        <code className="text-gilt-soft">supabase/schema.sql</code>) to enable
        accounts and per-user saved collections, protected by row-level security.
      </p>
      <Link
        href="/"
        className="mt-6 inline-flex rounded-full border border-white/15 px-5 py-2.5 text-sm text-white/80 transition hover:border-white/30 hover:text-white"
      >
        Back to stays
      </Link>
    </div>
  );
}
