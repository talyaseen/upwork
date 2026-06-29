"use client";

import { useMemo, useState, type ReactNode } from "react";
import { AnimatePresence, motion } from "framer-motion";
import type { Tag } from "@/lib/types";

export interface FeedItem {
  id: string;
  tags: string[];
  node: ReactNode;
}

const EASE = [0.22, 1, 0.36, 1] as const;

export function BriefingFeed({
  items,
  tags,
}: {
  items: FeedItem[];
  tags: Tag[];
}) {
  const [active, setActive] = useState<string | null>(null);

  // Only offer tags that actually match at least one property, with counts.
  const available = useMemo(() => {
    const counts = new Map<string, number>();
    for (const item of items) {
      for (const t of item.tags) counts.set(t, (counts.get(t) ?? 0) + 1);
    }
    return tags
      .filter((t) => counts.has(t.id))
      .map((t) => ({ ...t, count: counts.get(t.id) ?? 0 }));
  }, [items, tags]);

  const filtered = active
    ? items.filter((i) => i.tags.includes(active))
    : items;

  return (
    <div>
      {/* Tag filter bar */}
      <div className="mb-6 flex flex-wrap gap-2">
        <TagPill
          label="All stays"
          count={items.length}
          active={active === null}
          onClick={() => setActive(null)}
        />
        {available.map((t) => (
          <TagPill
            key={t.id}
            label={t.label}
            count={t.count}
            active={active === t.id}
            onClick={() => setActive(active === t.id ? null : t.id)}
          />
        ))}
      </div>

      <motion.div
        layout
        className="grid grid-cols-1 gap-5 sm:grid-cols-2 lg:grid-cols-3"
      >
        <AnimatePresence mode="popLayout">
          {filtered.map((item, i) => (
            <motion.div
              key={item.id}
              layout
              initial={{ opacity: 0, scale: 0.95, y: 18 }}
              animate={{
                opacity: 1,
                scale: 1,
                y: 0,
                transition: { duration: 0.5, ease: EASE, delay: Math.min(i * 0.04, 0.4) },
              }}
              exit={{ opacity: 0, scale: 0.95, transition: { duration: 0.25 } }}
            >
              {item.node}
            </motion.div>
          ))}
        </AnimatePresence>
      </motion.div>

      {filtered.length === 0 && (
        <p className="py-16 text-center text-sm text-white/40">
          No stays match that theme yet.
        </p>
      )}
    </div>
  );
}

function TagPill({
  label,
  count,
  active,
  onClick,
}: {
  label: string;
  count: number;
  active: boolean;
  onClick: () => void;
}) {
  return (
    <button
      type="button"
      onClick={onClick}
      className={`group inline-flex items-center gap-1.5 rounded-full border px-3.5 py-1.5 text-sm transition ${
        active
          ? "border-gilt/50 bg-gilt/15 text-gilt-soft"
          : "border-white/10 bg-white/[0.03] text-white/60 hover:border-white/25 hover:text-white"
      }`}
    >
      {label}
      <span
        className={`text-[11px] tabular-nums ${active ? "text-gilt/80" : "text-white/30"}`}
      >
        {count}
      </span>
    </button>
  );
}
