import type { Property } from "@/lib/types";

export interface BookingLink {
  partner: string;
  url: string;
}

/**
 * Build affiliate-style deep links to the major OTAs. The tracking params
 * (`aff`, `pid`) are illustrative placeholders for a demo - in production they
 * would carry your real affiliate / partner identifiers.
 */
export function bookingLinks(property: Property): BookingLink[] {
  const pid = encodeURIComponent(property.id);
  const query = encodeURIComponent(`${property.name} ${property.destination}`);
  const aff = "demo";

  return [
    {
      partner: "Trip.com",
      url: `https://www.trip.com/hotels/list?city=&keyword=${query}&aff=${aff}&pid=${pid}`,
    },
    {
      partner: "Booking.com",
      url: `https://www.booking.com/searchresults.html?ss=${query}&aff=${aff}&pid=${pid}`,
    },
    {
      partner: "Agoda",
      url: `https://www.agoda.com/search?q=${query}&aff=${aff}&pid=${pid}`,
    },
  ];
}
