import Image from "next/image";
import { SECTION_BLUR } from "@/lib/images";

/** Compact photographic page header used across the section pages. */
export function PageHeader({
  image,
  eyebrow,
  title,
  subtitle,
}: {
  image: string;
  eyebrow: string;
  title: string;
  subtitle: string;
}) {
  return (
    <div className="relative overflow-hidden rounded-3xl border border-white/[0.08] shadow-card">
      <Image
        src={image}
        alt=""
        fill
        priority
        placeholder="blur"
        blurDataURL={SECTION_BLUR}
        sizes="(min-width:1152px) 1100px, 100vw"
        className="object-cover"
      />
      <div className="absolute inset-0 bg-gradient-to-t from-ink-900 via-ink-900/60 to-ink-900/25" />
      <div className="absolute inset-0 bg-gradient-to-r from-ink-900/80 to-transparent" />
      <div className="relative flex min-h-[240px] flex-col justify-end gap-3 p-7 sm:min-h-[300px] sm:p-10">
        <span className="inline-flex w-fit items-center gap-2 rounded-full border border-gilt/30 bg-ink-900/40 px-3.5 py-1.5 text-xs font-medium uppercase tracking-luxe text-gilt-soft backdrop-blur">
          <span className="h-1.5 w-1.5 rounded-full bg-gilt" />
          {eyebrow}
        </span>
        <h1 className="max-w-2xl text-balance font-display text-3xl leading-tight text-white sm:text-5xl">
          {title}
        </h1>
        <p className="max-w-xl text-balance text-white/65">{subtitle}</p>
      </div>
    </div>
  );
}
