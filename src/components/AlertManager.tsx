"use client";

import { useState } from "react";
import { AnimatePresence, motion } from "framer-motion";

interface Rule {
  id: string;
  subject: string;
  level: number;
  frequency: string;
  active: boolean;
}

const SUBJECTS = [
  "Any stay",
  "Overwater",
  "Safari",
  "Urban",
  "Wellness",
  "Paris",
  "Venice",
  "Tokyo",
];
const LEVELS = [3, 4, 5];
const FREQUENCIES = ["Instant", "Daily", "Weekly"];

let counter = 0;
const nextId = () => `rule-${++counter}`;

export function AlertManager() {
  const [rules, setRules] = useState<Rule[]>([
    { id: "seed-1", subject: "Any stay", level: 4, frequency: "Weekly", active: true },
    { id: "seed-2", subject: "Overwater", level: 5, frequency: "Instant", active: true },
    { id: "seed-3", subject: "Paris", level: 3, frequency: "Daily", active: false },
  ]);
  const [subject, setSubject] = useState(SUBJECTS[0]);
  const [level, setLevel] = useState(4);
  const [frequency, setFrequency] = useState("Weekly");

  const add = () =>
    setRules((r) => [
      { id: nextId(), subject, level, frequency, active: true },
      ...r,
    ]);
  const remove = (id: string) =>
    setRules((r) => r.filter((x) => x.id !== id));
  const toggle = (id: string) =>
    setRules((r) =>
      r.map((x) => (x.id === id ? { ...x, active: !x.active } : x)),
    );

  return (
    <section className="rounded-3xl border border-white/[0.08] bg-ink-700/50 p-6 sm:p-7">
      <h2 className="font-display text-xl text-white">Manage your alerts</h2>
      <p className="mt-1 text-sm text-white/45">
        Create as many watches as you like. Toggle or remove them any time.
      </p>

      {/* Create */}
      <div className="mt-5 grid grid-cols-1 gap-3 sm:grid-cols-[1fr_auto_auto_auto]">
        <Select label="Watch" value={subject} onChange={setSubject} options={SUBJECTS} />
        <Select
          label="Level"
          value={String(level)}
          onChange={(v) => setLevel(Number(v))}
          options={LEVELS.map((l) => `L${l}+`)}
          values={LEVELS.map(String)}
        />
        <Select
          label="Frequency"
          value={frequency}
          onChange={setFrequency}
          options={FREQUENCIES}
        />
        <div className="flex items-end">
          <button
            type="button"
            onClick={add}
            className="w-full rounded-xl bg-gilt px-5 py-2.5 text-sm font-semibold text-ink-900 transition hover:bg-gilt-soft active:scale-[0.98] sm:w-auto"
          >
            Add alert
          </button>
        </div>
      </div>

      {/* List */}
      <ul className="mt-5 space-y-2.5">
        <AnimatePresence initial={false}>
          {rules.map((rule) => (
            <motion.li
              key={rule.id}
              layout
              initial={{ opacity: 0, y: -8 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, x: 12 }}
              transition={{ duration: 0.3, ease: [0.22, 1, 0.36, 1] }}
              className="flex items-center justify-between gap-3 rounded-2xl border border-white/[0.07] bg-ink-800/50 p-4"
            >
              <div className="min-w-0">
                <p className="truncate text-white">
                  {rule.subject}
                  <span className="ml-2 text-sm text-white/40">
                    L{rule.level}+ · {rule.frequency}
                  </span>
                </p>
              </div>
              <div className="flex shrink-0 items-center gap-3">
                <button
                  type="button"
                  onClick={() => toggle(rule.id)}
                  aria-label={rule.active ? "Pause alert" : "Resume alert"}
                  className={`relative h-6 w-11 rounded-full transition ${
                    rule.active ? "bg-gilt" : "bg-white/15"
                  }`}
                >
                  <motion.span
                    layout
                    transition={{ type: "spring", stiffness: 500, damping: 32 }}
                    className={`absolute top-0.5 h-5 w-5 rounded-full bg-white ${
                      rule.active ? "right-0.5" : "left-0.5"
                    }`}
                  />
                </button>
                <button
                  type="button"
                  onClick={() => remove(rule.id)}
                  aria-label="Remove alert"
                  className="flex h-8 w-8 items-center justify-center rounded-full border border-white/10 text-white/50 transition hover:border-white/25 hover:text-white"
                >
                  ✕
                </button>
              </div>
            </motion.li>
          ))}
        </AnimatePresence>
      </ul>

      {rules.length === 0 && (
        <p className="py-8 text-center text-sm text-white/40">
          No alerts yet. Create one above.
        </p>
      )}
    </section>
  );
}

function Select({
  label,
  value,
  onChange,
  options,
  values,
}: {
  label: string;
  value: string;
  onChange: (v: string) => void;
  options: string[];
  values?: string[];
}) {
  return (
    <label className="block">
      <span className="mb-1.5 block text-xs font-medium uppercase tracking-wide text-white/50">
        {label}
      </span>
      <select
        value={value}
        onChange={(e) => onChange(e.target.value)}
        className="w-full rounded-xl border border-white/10 bg-ink-900/60 px-3.5 py-2.5 text-sm text-white outline-none transition focus:border-gilt/50 [color-scheme:dark]"
      >
        {options.map((o, i) => (
          <option key={o} value={values ? values[i] : o}>
            {o}
          </option>
        ))}
      </select>
    </label>
  );
}
