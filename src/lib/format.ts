/** Format a nightly rate as a whole-number currency amount (no decimals). */
export function formatRate(amount: number, currency = "USD"): string {
  try {
    return new Intl.NumberFormat("en-US", {
      style: "currency",
      currency,
      maximumFractionDigits: 0,
    }).format(amount);
  } catch {
    // Unknown currency code - fall back to a plain number with the code.
    return `${currency} ${Math.round(amount).toLocaleString("en-US")}`;
  }
}

/** Short, readable date like "22 Jun" for rate-history rows / axes. */
export function formatShortDate(iso: string): string {
  const d = new Date(`${iso}T00:00:00Z`);
  if (Number.isNaN(d.getTime())) return iso;
  return new Intl.DateTimeFormat("en-GB", {
    day: "2-digit",
    month: "short",
    timeZone: "UTC",
  }).format(d);
}
