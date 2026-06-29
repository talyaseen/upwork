// Image helpers. All photography is from the free Unsplash CDN
// (images.unsplash.com); URLs are loaded by the browser at runtime, never at
// build time. A gradient + blur placeholder always sits behind each photo so
// the UI degrades gracefully if an image is ever unavailable.

/** Build a sized Unsplash URL from a photo id. */
export function unsplash(id: string, width = 1600): string {
  return `https://images.unsplash.com/photo-${id}?auto=format&fit=crop&w=${width}&q=80`;
}

/**
 * A tiny base64-encoded SVG gradient used as the blur placeholder for
 * next/image, derived from a property's accent colours.
 */
export function blurDataURL(from: string, to: string): string {
  const svg = `<svg xmlns='http://www.w3.org/2000/svg' width='8' height='8'><defs><linearGradient id='g' x1='0' y1='0' x2='1' y2='1'><stop offset='0%' stop-color='${from}'/><stop offset='100%' stop-color='${to}'/></linearGradient></defs><rect width='8' height='8' fill='url(#g)'/></svg>`;
  return `data:image/svg+xml;base64,${Buffer.from(svg).toString("base64")}`;
}

/** Wide, cinematic homepage hero image. */
export const HERO_IMAGE = unsplash("1566073771259-6a8506099945", 2000);
export const HERO_BLUR = blurDataURL("#0a0a0f", "#2a2336");
