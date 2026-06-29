"use client";

import { useState } from "react";
import { AnimatePresence, motion } from "framer-motion";
import { TAGS } from "@/lib/demo-data";
import { INTELLIGENCE_LEVELS } from "@/lib/intelligence";

const FREQUENCIES = ["Instant", "Daily", "Weekly"];
const LEVEL_OPTIONS = [
  { value: 3, label: "L3+" },
  { value: 4, label: "L4+" },
  { value: 5, label: "L5 only" },
];
const INTEREST_TAGS = TAGS.filter((t) =>
  [
    "overwater",
    "beachfront",
    "safari",
    "urban",
    "design-led",
    "heritage",
    "wellness",
    "culinary",
    "honeymoon",
    "adventure",
  ].includes(t.id),
);

export function AlertPreferences() {
  const [level, setLevel] = useState(4);
  const [frequency, setFrequency] = useState("Weekly");
  const [email, setEmail] = useState(true);
  const [push, setPush] = useState(false);
  const [interests, setInterests] = useState<string[]>([
    "overwater",
    "wellness",
    "culinary",
  ]);
  const [saved, setSaved] = useState(false);

  const toggleInterest = (id: string) =>
    setInterests((s) =>
      s.includes(id) ? s.filter((x) => x !== id) : [...s, id],
    );

  const levelMeta = INTELLIGENCE_LEVELS.find((l) => l.level === level);

  function onSave(e: React.FormEvent) {
    e.preventDefault();
    setSaved(true);
    window.setTimeout(() => setSaved(false), 2500);
  }

  return (
    <form
      onSubmit={onSave}
      className="rounded-3xl border border-white/[0.08] bg-ink-700/50 p-6 sm:p-7"
    >
      <h2 className="font-display text-xl text-white">Alert preferences</h2>
      <p className="mt-1 text-sm text-white/45">
        Tell us when a stay is worth your attention.
      </p>

      {/* Threshold */}
      <Field label="Minimum signal level">
        <Segmented
          name="level"
          options={LEVEL_OPTIONS.map((o) => o.label)}
          value={LEVEL_OPTIONS.find((o) => o.value === level)?.label ?? "L4+"}
          onChange={(label) =>
            setLevel(
              LEVEL_OPTIONS.find((o) => o.label === label)?.value ?? 4,
            )
          }
        />
        {levelMeta && (
          <p className="mt-2 text-xs text-white/40">{levelMeta.description}</p>
        )}
      </Field>

      {/* Frequency */}
      <Field label="Frequency">
        <Segmented
          name="frequency"
          options={FREQUENCIES}
          value={frequency}
          onChange={setFrequency}
        />
      </Field>

      {/* Channels */}
      <Field label="Channels">
        <div className="space-y-2.5">
          <Toggle label="Email digest" on={email} onChange={setEmail} />
          <Toggle label="Push notifications" on={push} onChange={setPush} />
        </div>
      </Field>

      {/* Interests */}
      <Field label="Experience interests">
        <div className="flex flex-wrap gap-2">
          {INTEREST_TAGS.map((t) => {
            const active = interests.includes(t.id);
            return (
              <button
                key={t.id}
                type="button"
                onClick={() => toggleInterest(t.id)}
                className={`rounded-full border px-3 py-1.5 text-sm transition ${
                  active
                    ? "border-gilt/50 bg-gilt/15 text-gilt-soft"
                    : "border-white/10 bg-white/[0.03] text-white/60 hover:border-white/25 hover:text-white"
                }`}
              >
                {t.label}
              </button>
            );
          })}
        </div>
      </Field>

      <div className="mt-7 flex items-center gap-3">
        <button
          type="submit"
          className="rounded-full bg-gilt px-5 py-2.5 text-sm font-semibold text-ink-900 transition hover:bg-gilt-soft active:scale-[0.98]"
        >
          Save preferences
        </button>
        <AnimatePresence>
          {saved && (
            <motion.span
              initial={{ opacity: 0, x: -8 }}
              animate={{ opacity: 1, x: 0 }}
              exit={{ opacity: 0 }}
              className="text-sm text-gilt-soft"
            >
              Preferences saved
            </motion.span>
          )}
        </AnimatePresence>
      </div>
    </form>
  );
}

function Field({
  label,
  children,
}: {
  label: string;
  children: React.ReactNode;
}) {
  return (
    <div className="mt-6">
      <p className="mb-2 text-xs font-medium uppercase tracking-wide text-white/50">
        {label}
      </p>
      {children}
    </div>
  );
}

function Segmented({
  name,
  options,
  value,
  onChange,
}: {
  name: string;
  options: string[];
  value: string;
  onChange: (v: string) => void;
}) {
  return (
    <div className="inline-flex rounded-full border border-white/10 bg-ink-900/50 p-1">
      {options.map((o) => {
        const active = o === value;
        return (
          <button
            key={o}
            type="button"
            onClick={() => onChange(o)}
            className="relative rounded-full px-4 py-1.5 text-sm transition"
          >
            {active && (
              <motion.span
                layoutId={`segmented-${name}`}
                className="absolute inset-0 rounded-full bg-gilt"
                transition={{ type: "spring", stiffness: 360, damping: 30 }}
              />
            )}
            <span
              className={`relative ${active ? "font-medium text-ink-900" : "text-white/60"}`}
            >
              {o}
            </span>
          </button>
        );
      })}
    </div>
  );
}

function Toggle({
  label,
  on,
  onChange,
}: {
  label: string;
  on: boolean;
  onChange: (v: boolean) => void;
}) {
  return (
    <button
      type="button"
      onClick={() => onChange(!on)}
      className="flex w-full items-center justify-between gap-3 rounded-xl border border-white/[0.07] bg-ink-800/50 px-4 py-2.5 text-sm text-white/75"
    >
      {label}
      <span
        className={`relative h-6 w-11 rounded-full transition ${on ? "bg-gilt" : "bg-white/15"}`}
      >
        <motion.span
          layout
          transition={{ type: "spring", stiffness: 500, damping: 32 }}
          className={`absolute top-0.5 h-5 w-5 rounded-full bg-white shadow ${on ? "right-0.5" : "left-0.5"}`}
        />
      </span>
    </button>
  );
}
