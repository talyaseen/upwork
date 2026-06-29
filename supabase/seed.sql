-- =============================================================================
--  Hotel Rate Intelligence - seed data
--  Run AFTER schema.sql.
--
--  Eight real, iconic luxury hotels with real destinations. The RATES and the
--  rate history are ILLUSTRATIVE SAMPLE DATA for demonstration only - they are
--  not live or quoted prices.
-- =============================================================================

insert into public.properties
  (id, name, destination, country, description, star_rating, current_rate, avg_rate, currency, accent_from, accent_to, image_url)
values
  ('aman-tokyo', 'Aman Tokyo', 'Tokyo', 'Japan',
   'Urban sanctuary on the upper floors of Otemachi Tower, with onsen baths and city-wide views.',
   5, 1180, 1320, 'USD', '#1f2350', '#4a2d52',
   'https://images.unsplash.com/photo-1540959733332-eab4deabeeaf?auto=format&fit=crop&w=1600&q=80'),

  ('ritz-paris', 'The Ritz Paris', 'Paris', 'France',
   'The legendary Place Vendome palace hotel, redefining Parisian elegance since 1898.',
   5, 1650, 1700, 'EUR', '#3a2c20', '#7c5a3a',
   'https://images.unsplash.com/photo-1502602898657-3e91760cbb34?auto=format&fit=crop&w=1600&q=80'),

  ('burj-al-arab', 'Burj Al Arab Jumeirah', 'Dubai', 'United Arab Emirates',
   'The sail-shaped icon of Jumeirah Beach, defined by gold-leaf suites and Arabian opulence.',
   5, 2100, 2750, 'USD', '#0b2a4a', '#1d6fa5',
   'https://images.unsplash.com/photo-1512453979798-5ea266f8880c?auto=format&fit=crop&w=1600&q=80'),

  ('belmond-caruso', 'Belmond Hotel Caruso', 'Amalfi Coast', 'Italy',
   'An eleventh-century palazzo above Ravello, with a cliff-edge infinity pool over the Tyrrhenian Sea.',
   5, 1490, 1520, 'EUR', '#0f3b34', '#3f7d5a',
   'https://images.unsplash.com/photo-1533104816931-20fa691ff6ca?auto=format&fit=crop&w=1600&q=80'),

  ('four-seasons-bora-bora', 'Four Seasons Resort Bora Bora', 'Bora Bora', 'French Polynesia',
   'Overwater bungalows above a turquoise lagoon, framed by the silhouette of Mount Otemanu.',
   5, 1880, 2300, 'USD', '#0a4f5c', '#2aa7a0',
   'https://images.unsplash.com/photo-1518391846015-55a9cc003b25?auto=format&fit=crop&w=1600&q=80'),

  ('the-plaza-ny', 'The Plaza', 'New York', 'United States',
   'A Beaux-Arts landmark on Fifth Avenue overlooking Central Park since 1907.',
   5, 925, 1010, 'USD', '#2a2730', '#5c4a63',
   'https://images.unsplash.com/photo-1496417263034-38ec4f0b665a?auto=format&fit=crop&w=1600&q=80'),

  ('claridges-london', 'Claridge''s', 'London', 'United Kingdom',
   'Art Deco grandeur in the heart of Mayfair, a byword for understated British luxury.',
   5, 780, 950, 'GBP', '#26282b', '#4a4f57',
   'https://images.unsplash.com/photo-1513635269975-59663e0ac1ad?auto=format&fit=crop&w=1600&q=80'),

  ('singita-sasakwa', 'Singita Sasakwa Lodge', 'Serengeti', 'Tanzania',
   'An Edwardian-style safari lodge on a private hill, overlooking the Serengeti plains.',
   5, 2450, 2400, 'USD', '#3a2a12', '#9a6b2f',
   'https://images.unsplash.com/photo-1516026672322-bc52d61a55d5?auto=format&fit=crop&w=1600&q=80')
on conflict (id) do update set
  name         = excluded.name,
  destination  = excluded.destination,
  country      = excluded.country,
  description  = excluded.description,
  star_rating  = excluded.star_rating,
  current_rate = excluded.current_rate,
  avg_rate     = excluded.avg_rate,
  currency     = excluded.currency,
  accent_from  = excluded.accent_from,
  accent_to    = excluded.accent_to,
  image_url    = excluded.image_url;

-- ---------------------------------------------------------------------------
--  rate_history - nine weekly captures per property; the final point is "today"
--  and equals the property's current_rate.
-- ---------------------------------------------------------------------------
insert into public.rate_history (property_id, captured_on, rate) values
  ('aman-tokyo', '2026-04-27', 1345), ('aman-tokyo', '2026-05-04', 1295),
  ('aman-tokyo', '2026-05-11', 1385), ('aman-tokyo', '2026-05-18', 1320),
  ('aman-tokyo', '2026-05-25', 1265), ('aman-tokyo', '2026-06-01', 1360),
  ('aman-tokyo', '2026-06-08', 1305), ('aman-tokyo', '2026-06-15', 1335),
  ('aman-tokyo', '2026-06-22', 1180),

  ('ritz-paris', '2026-04-27', 1735), ('ritz-paris', '2026-05-04', 1665),
  ('ritz-paris', '2026-05-11', 1785), ('ritz-paris', '2026-05-18', 1700),
  ('ritz-paris', '2026-05-25', 1630), ('ritz-paris', '2026-06-01', 1750),
  ('ritz-paris', '2026-06-08', 1685), ('ritz-paris', '2026-06-15', 1715),
  ('ritz-paris', '2026-06-22', 1650),

  ('burj-al-arab', '2026-04-27', 2805), ('burj-al-arab', '2026-05-04', 2695),
  ('burj-al-arab', '2026-05-11', 2885), ('burj-al-arab', '2026-05-18', 2750),
  ('burj-al-arab', '2026-05-25', 2640), ('burj-al-arab', '2026-06-01', 2830),
  ('burj-al-arab', '2026-06-08', 2720), ('burj-al-arab', '2026-06-15', 2775),
  ('burj-al-arab', '2026-06-22', 2100),

  ('belmond-caruso', '2026-04-27', 1550), ('belmond-caruso', '2026-05-04', 1490),
  ('belmond-caruso', '2026-05-11', 1595), ('belmond-caruso', '2026-05-18', 1520),
  ('belmond-caruso', '2026-05-25', 1460), ('belmond-caruso', '2026-06-01', 1565),
  ('belmond-caruso', '2026-06-08', 1505), ('belmond-caruso', '2026-06-15', 1535),
  ('belmond-caruso', '2026-06-22', 1490),

  ('four-seasons-bora-bora', '2026-04-27', 2345), ('four-seasons-bora-bora', '2026-05-04', 2255),
  ('four-seasons-bora-bora', '2026-05-11', 2415), ('four-seasons-bora-bora', '2026-05-18', 2300),
  ('four-seasons-bora-bora', '2026-05-25', 2210), ('four-seasons-bora-bora', '2026-06-01', 2370),
  ('four-seasons-bora-bora', '2026-06-08', 2275), ('four-seasons-bora-bora', '2026-06-15', 2325),
  ('four-seasons-bora-bora', '2026-06-22', 1880),

  ('the-plaza-ny', '2026-04-27', 1030), ('the-plaza-ny', '2026-05-04', 990),
  ('the-plaza-ny', '2026-05-11', 1060), ('the-plaza-ny', '2026-05-18', 1010),
  ('the-plaza-ny', '2026-05-25', 970), ('the-plaza-ny', '2026-06-01', 1040),
  ('the-plaza-ny', '2026-06-08', 1000), ('the-plaza-ny', '2026-06-15', 1020),
  ('the-plaza-ny', '2026-06-22', 925),

  ('claridges-london', '2026-04-27', 970), ('claridges-london', '2026-05-04', 930),
  ('claridges-london', '2026-05-11', 995), ('claridges-london', '2026-05-18', 950),
  ('claridges-london', '2026-05-25', 910), ('claridges-london', '2026-06-01', 980),
  ('claridges-london', '2026-06-08', 940), ('claridges-london', '2026-06-15', 960),
  ('claridges-london', '2026-06-22', 780),

  ('singita-sasakwa', '2026-04-27', 2450), ('singita-sasakwa', '2026-05-04', 2350),
  ('singita-sasakwa', '2026-05-11', 2520), ('singita-sasakwa', '2026-05-18', 2400),
  ('singita-sasakwa', '2026-05-25', 2305), ('singita-sasakwa', '2026-06-01', 2470),
  ('singita-sasakwa', '2026-06-08', 2375), ('singita-sasakwa', '2026-06-15', 2425),
  ('singita-sasakwa', '2026-06-22', 2450)
on conflict (property_id, captured_on) do update set rate = excluded.rate;
