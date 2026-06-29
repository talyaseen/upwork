"use client";

import { useMemo, useState } from "react";
import { AnimatePresence, motion } from "framer-motion";
import type { Property, RoomType, StayPackage } from "@/lib/types";
import { formatRate, formatShortDate } from "@/lib/format";
import {
  quoteStay,
  DEFAULT_CHECK_IN,
  DEFAULT_CHECK_OUT,
} from "@/lib/booking-data";

const EASE = [0.22, 1, 0.36, 1] as const;

export function BookingWidget({
  property,
  rooms,
  packages,
}: {
  property: Property;
  rooms: RoomType[];
  packages: StayPackage[];
}) {
  const [roomId, setRoomId] = useState(rooms[0].id);
  const [pkgId, setPkgId] = useState(packages[0].id);
  const [checkIn, setCheckIn] = useState(DEFAULT_CHECK_IN);
  const [checkOut, setCheckOut] = useState(DEFAULT_CHECK_OUT);
  const [guests, setGuests] = useState(2);
  const [showNights, setShowNights] = useState(false);
  const [reserved, setReserved] = useState(false);

  const room = rooms.find((r) => r.id === roomId) ?? rooms[0];
  const pkg = packages.find((p) => p.id === pkgId) ?? packages[0];

  const quote = useMemo(
    () => quoteStay({ property, room, pkg, checkIn, checkOut }),
    [property, room, pkg, checkIn, checkOut],
  );

  const cur = property.currency;
  const validRange = quote.nightsCount > 0;
  const overCapacity = guests > room.maxOccupancy;

  function reserve() {
    if (!validRange) return;
    setReserved(true);
    window.setTimeout(() => setReserved(false), 3000);
  }

  return (
    <section className="rounded-3xl border border-white/[0.08] bg-ink-700/50 p-6 sm:p-8">
      <div className="flex flex-wrap items-end justify-between gap-3">
        <div>
          <h2 className="font-display text-xl text-white">Rates &amp; packages</h2>
          <p className="mt-1 max-w-md text-sm text-white/45">
            This property&apos;s own rate card and booking engine, the live
            surface AURUM monitors and benchmarks against its competitor set.
          </p>
        </div>
        <span className="rounded-full border border-white/10 bg-white/[0.03] px-3 py-1 text-[11px] text-white/45">
          Weekend nights priced higher
        </span>
      </div>

      {/* Room types */}
      <div className="mt-6 grid grid-cols-1 gap-3 sm:grid-cols-2">
        {rooms.map((r) => {
          const active = r.id === roomId;
          const from = Math.round(property.current_rate * r.multiplier);
          return (
            <button
              key={r.id}
              type="button"
              onClick={() => setRoomId(r.id)}
              aria-pressed={active}
              className={`flex gap-3 rounded-2xl border p-3 text-left transition ${
                active
                  ? "border-gilt/45 bg-gilt/[0.07]"
                  : "border-white/[0.07] bg-ink-800/40 hover:border-white/20"
              }`}
            >
              <div
                className="h-16 w-16 shrink-0 rounded-xl"
                style={{
                  backgroundImage: `linear-gradient(135deg, ${r.accent_from}, ${r.accent_to})`,
                }}
              />
              <div className="min-w-0 flex-1">
                <div className="flex items-center justify-between gap-2">
                  <p className="truncate font-medium text-white">{r.name}</p>
                  {active && (
                    <span className="text-gilt-soft" aria-hidden="true">
                      ✓
                    </span>
                  )}
                </div>
                <p className="mt-0.5 truncate text-xs text-white/40">
                  {r.beds} · {r.sizeSqm} m² · up to {r.maxOccupancy}
                </p>
                <p className="mt-1 text-sm text-gilt-soft">
                  from {formatRate(from, cur)}
                  <span className="text-white/35"> / night</span>
                </p>
              </div>
            </button>
          );
        })}
      </div>

      <div className="mt-6 grid grid-cols-1 gap-6 lg:grid-cols-[1.1fr_0.9fr]">
        {/* Controls */}
        <div className="space-y-5">
          <div className="grid grid-cols-2 gap-3">
            <DateField
              label="Check-in"
              value={checkIn}
              onChange={setCheckIn}
            />
            <DateField
              label="Check-out"
              value={checkOut}
              onChange={setCheckOut}
            />
          </div>

          <div>
            <FieldLabel>Guests</FieldLabel>
            <div className="inline-flex rounded-full border border-white/10 bg-ink-900/50 p-1">
              {[1, 2, 3, 4].map((g) => (
                <button
                  key={g}
                  type="button"
                  onClick={() => setGuests(g)}
                  className={`relative rounded-full px-4 py-1.5 text-sm transition ${
                    g === guests ? "text-ink-900" : "text-white/60"
                  }`}
                >
                  {g === guests && (
                    <motion.span
                      layoutId="guest-active"
                      className="absolute inset-0 rounded-full bg-gilt"
                      transition={{ type: "spring", stiffness: 360, damping: 30 }}
                    />
                  )}
                  <span className="relative">{g}</span>
                </button>
              ))}
            </div>
            {overCapacity && (
              <p className="mt-2 text-xs text-gilt-soft">
                {room.name} sleeps up to {room.maxOccupancy}; consider a larger
                room.
              </p>
            )}
          </div>

          <div>
            <FieldLabel>Package</FieldLabel>
            <div className="flex flex-wrap gap-2">
              {packages.map((p) => {
                const active = p.id === pkgId;
                const hint = p.flat
                  ? `+${formatRate(p.flat, cur)}`
                  : p.perNight
                    ? `+${formatRate(p.perNight, cur)}/night`
                    : "included";
                return (
                  <button
                    key={p.id}
                    type="button"
                    onClick={() => setPkgId(p.id)}
                    className={`rounded-full border px-3.5 py-1.5 text-sm transition ${
                      active
                        ? "border-gilt/50 bg-gilt/15 text-gilt-soft"
                        : "border-white/10 bg-white/[0.03] text-white/60 hover:border-white/25 hover:text-white"
                    }`}
                  >
                    {p.name}
                    <span className="ml-1.5 text-[11px] text-white/35">
                      {hint}
                    </span>
                  </button>
                );
              })}
            </div>
            <p className="mt-2 text-xs text-white/40">{pkg.description}</p>
          </div>
        </div>

        {/* Summary */}
        <div className="rounded-2xl border border-white/[0.08] bg-ink-800/50 p-5">
          {validRange ? (
            <>
              <button
                type="button"
                onClick={() => setShowNights((s) => !s)}
                className="flex w-full items-center justify-between text-sm text-white/70"
              >
                <span>
                  {quote.nightsCount}{" "}
                  {quote.nightsCount === 1 ? "night" : "nights"} ·{" "}
                  {formatShortDate(checkIn)} - {formatShortDate(checkOut)}
                </span>
                <span className="text-gilt-soft">
                  {showNights ? "Hide" : "Breakdown"}
                </span>
              </button>

              <AnimatePresence initial={false}>
                {showNights && (
                  <motion.ul
                    initial={{ height: 0, opacity: 0 }}
                    animate={{ height: "auto", opacity: 1 }}
                    exit={{ height: 0, opacity: 0 }}
                    transition={{ duration: 0.3, ease: EASE }}
                    className="mt-3 space-y-1.5 overflow-hidden text-sm"
                  >
                    {quote.nights.map((n) => (
                      <li
                        key={n.date}
                        className="flex items-center justify-between"
                      >
                        <span className="flex items-center gap-2 text-white/55">
                          {formatShortDate(n.date)}
                          {n.weekend && (
                            <span className="rounded-full border border-gilt/40 bg-gilt/10 px-1.5 py-0.5 text-[10px] text-gilt-soft">
                              weekend
                            </span>
                          )}
                        </span>
                        <span
                          className={
                            n.weekend ? "text-gilt-soft" : "text-white/80"
                          }
                        >
                          {formatRate(n.rate, cur)}
                        </span>
                      </li>
                    ))}
                  </motion.ul>
                )}
              </AnimatePresence>

              <div className="mt-4 space-y-2 border-t border-white/[0.06] pt-4 text-sm">
                <Row label="Room subtotal" value={formatRate(quote.roomSubtotal, cur)} />
                {quote.packageTotal > 0 && (
                  <Row
                    label={`Package · ${pkg.name}`}
                    value={formatRate(quote.packageTotal, cur)}
                  />
                )}
                <Row label="Taxes (12%)" value={formatRate(quote.taxes, cur)} muted />
                <Row label="Resort fees" value={formatRate(quote.fees, cur)} muted />
              </div>

              <div className="mt-4 flex items-end justify-between border-t border-white/[0.06] pt-4">
                <span className="text-sm text-white/55">Total</span>
                <AnimatePresence mode="popLayout">
                  <motion.span
                    key={quote.grandTotal}
                    initial={{ opacity: 0, y: 8 }}
                    animate={{ opacity: 1, y: 0 }}
                    exit={{ opacity: 0, y: -8 }}
                    transition={{ duration: 0.3, ease: EASE }}
                    className="font-display text-3xl text-white"
                  >
                    {formatRate(quote.grandTotal, cur)}
                  </motion.span>
                </AnimatePresence>
              </div>

              <button
                type="button"
                onClick={reserve}
                className="mt-5 w-full rounded-full bg-gilt px-5 py-3 text-sm font-semibold text-ink-900 transition hover:bg-gilt-soft active:scale-[0.99]"
              >
                Reserve this stay
              </button>

              <AnimatePresence>
                {reserved && (
                  <motion.p
                    initial={{ opacity: 0, y: 6 }}
                    animate={{ opacity: 1, y: 0 }}
                    exit={{ opacity: 0 }}
                    className="mt-3 flex items-center justify-center gap-2 text-sm text-gilt-soft"
                  >
                    <span className="flex h-5 w-5 items-center justify-center rounded-full border border-gilt/40 bg-gilt/10 text-[11px]">
                      ✓
                    </span>
                    Reservation held for 24 hours (demo)
                  </motion.p>
                )}
              </AnimatePresence>
            </>
          ) : (
            <p className="py-10 text-center text-sm text-white/40">
              Select a check-out date after your check-in to see your quote.
            </p>
          )}
        </div>
      </div>
    </section>
  );
}

function FieldLabel({ children }: { children: React.ReactNode }) {
  return (
    <p className="mb-2 text-xs font-medium uppercase tracking-wide text-white/50">
      {children}
    </p>
  );
}

function DateField({
  label,
  value,
  onChange,
}: {
  label: string;
  value: string;
  onChange: (v: string) => void;
}) {
  return (
    <label className="block">
      <FieldLabel>{label}</FieldLabel>
      <input
        type="date"
        value={value}
        onChange={(e) => onChange(e.target.value)}
        className="w-full rounded-xl border border-white/10 bg-ink-900/60 px-3.5 py-2.5 text-sm text-white outline-none transition focus:border-gilt/50 focus:ring-2 focus:ring-gilt/15 [color-scheme:dark]"
      />
    </label>
  );
}

function Row({
  label,
  value,
  muted = false,
}: {
  label: string;
  value: string;
  muted?: boolean;
}) {
  return (
    <div className="flex items-center justify-between">
      <span className={muted ? "text-white/40" : "text-white/60"}>{label}</span>
      <span className={muted ? "text-white/55" : "text-white/85"}>{value}</span>
    </div>
  );
}
