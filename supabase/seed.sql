-- =============================================================================
--  Hotel Rate Intelligence - seed data
--  Run AFTER schema.sql.
--
--  Real hotels, brands and destinations. The RATES, rate history and any
--  loyalty figures are ILLUSTRATIVE SAMPLE DATA for demonstration only - they
--  are not live or quoted prices.
-- =============================================================================

-- --- Brands ------------------------------------------------------------------
insert into public.brands (id, name, origin, founded, description) values
  ('aman', 'Aman', 'Switzerland', 1988, 'Pioneering intimate, design-led sanctuaries in extraordinary settings.'),
  ('belmond', 'Belmond', 'United Kingdom', 1976, 'A storied collection of legendary hotels, trains and journeys.'),
  ('four-seasons', 'Four Seasons', 'Canada', 1960, 'Defining modern luxury through intuitive, personalised service.'),
  ('mandarin-oriental', 'Mandarin Oriental', 'Hong Kong', 1963, 'Oriental heritage and award-winning spas in landmark city hotels.'),
  ('rosewood', 'Rosewood', 'United States', 1979, 'A Sense of Place philosophy rooted in each destination''s culture.'),
  ('jumeirah', 'Jumeirah', 'United Arab Emirates', 1997, 'Bold, iconic architecture and lavish Arabian hospitality.'),
  ('singita', 'Singita', 'South Africa', 1993, 'Conservation-led safari lodges across Africa''s great wildernesses.'),
  ('maybourne', 'Maybourne', 'United Kingdom', 1812, 'London''s grande dame hotels, the byword for British luxury.'),
  ('raffles', 'Raffles', 'Singapore', 1887, 'Colonial-era grandeur and legendary, gracious service.')
on conflict (id) do update set
  name = excluded.name, origin = excluded.origin,
  founded = excluded.founded, description = excluded.description;

-- --- Experience tags ---------------------------------------------------------
insert into public.tags (id, label, category) values
  ('beachfront', 'Beachfront', 'Setting'),
  ('overwater', 'Overwater', 'Setting'),
  ('island', 'Island', 'Setting'),
  ('lakeside', 'Lakeside', 'Setting'),
  ('clifftop', 'Clifftop', 'Setting'),
  ('urban', 'Urban', 'Setting'),
  ('safari', 'Safari', 'Setting'),
  ('waterfront', 'Waterfront', 'Setting'),
  ('palace', 'Palace', 'Style'),
  ('design-led', 'Design-Led', 'Style'),
  ('heritage', 'Heritage', 'Style'),
  ('contemporary', 'Contemporary', 'Style'),
  ('minimalist', 'Minimalist', 'Style'),
  ('art-deco', 'Art Deco', 'Style'),
  ('honeymoon', 'Honeymoon', 'Experience'),
  ('wellness', 'Wellness', 'Experience'),
  ('culinary', 'Culinary', 'Experience'),
  ('family', 'Family', 'Experience'),
  ('adventure', 'Adventure', 'Experience'),
  ('romance', 'Romance', 'Experience')
on conflict (id) do update set label = excluded.label, category = excluded.category;

-- --- Properties --------------------------------------------------------------
insert into public.properties
  (id, name, destination, country, description, star_rating, current_rate, avg_rate, currency, accent_from, accent_to, image_url, brand_id, tags)
values
  ('aman-tokyo', 'Aman Tokyo', 'Tokyo', 'Japan',
   'Urban sanctuary on the upper floors of Otemachi Tower, with onsen baths and city-wide views.',
   5, 1130, 1320, 'USD', '#1f2350', '#4a2d52',
   'https://images.unsplash.com/photo-1540959733332-eab4deabeeaf?auto=format&fit=crop&w=1600&q=80',
   'aman', array['urban','minimalist','design-led','wellness']),

  ('aman-venice', 'Aman Venice', 'Venice', 'Italy',
   'A sixteenth-century palazzo on the Grand Canal, with frescoed salons and a secret garden.',
   5, 1480, 1850, 'EUR', '#2a2440', '#6b4a6e',
   'https://images.unsplash.com/photo-1514890547357-a9ee288728e0?auto=format&fit=crop&w=1600&q=80',
   'aman', array['waterfront','heritage','design-led','romance','culinary']),

  ('belmond-caruso', 'Belmond Hotel Caruso', 'Amalfi Coast', 'Italy',
   'An eleventh-century palazzo above Ravello, with a cliff-edge infinity pool over the Tyrrhenian Sea.',
   5, 1490, 1520, 'EUR', '#0f3b34', '#3f7d5a',
   'https://images.unsplash.com/photo-1533104816931-20fa691ff6ca?auto=format&fit=crop&w=1600&q=80',
   'belmond', array['clifftop','heritage','romance','culinary','honeymoon']),

  ('belmond-cipriani', 'Belmond Hotel Cipriani', 'Venice', 'Italy',
   'A serene island retreat moments from St Mark''s Square, with a saltwater Olympic pool.',
   5, 1510, 1780, 'EUR', '#123040', '#356b7a',
   'https://images.unsplash.com/photo-1523906834658-6e24ef2386f9?auto=format&fit=crop&w=1600&q=80',
   'belmond', array['waterfront','heritage','romance','culinary']),

  ('four-seasons-bora-bora', 'Four Seasons Resort Bora Bora', 'Bora Bora', 'French Polynesia',
   'Overwater bungalows above a turquoise lagoon, framed by the silhouette of Mount Otemanu.',
   5, 1820, 2300, 'USD', '#0a4f5c', '#2aa7a0',
   'https://images.unsplash.com/photo-1518391846015-55a9cc003b25?auto=format&fit=crop&w=1600&q=80',
   'four-seasons', array['overwater','island','beachfront','honeymoon','romance']),

  ('four-seasons-george-v', 'Four Seasons George V', 'Paris', 'France',
   'A 1928 Art Deco landmark off the Champs-Elysees, with Michelin-starred dining and rooftop Eiffel views.',
   5, 1830, 1900, 'EUR', '#2c2418', '#6e5a38',
   'https://images.unsplash.com/photo-1502602898657-3e91760cbb34?auto=format&fit=crop&w=1600&q=80',
   'four-seasons', array['urban','palace','heritage','culinary']),

  ('mandarin-oriental-bangkok', 'Mandarin Oriental Bangkok', 'Bangkok', 'Thailand',
   'A riverside legend on the Chao Phraya, host to writers and royalty since 1876.',
   5, 690, 780, 'USD', '#2a1830', '#7a3f5a',
   'https://images.unsplash.com/photo-1563492065599-3520f775eeed?auto=format&fit=crop&w=1600&q=80',
   'mandarin-oriental', array['urban','waterfront','heritage','wellness','culinary']),

  ('rosewood-hong-kong', 'Rosewood Hong Kong', 'Hong Kong', 'China',
   'A vertical estate on the Kowloon waterfront with sweeping Victoria Harbour views.',
   5, 740, 920, 'USD', '#1a2433', '#41597a',
   'https://images.unsplash.com/photo-1536599018102-9f803c140fc1?auto=format&fit=crop&w=1600&q=80',
   'rosewood', array['urban','contemporary','design-led','wellness']),

  ('burj-al-arab', 'Burj Al Arab Jumeirah', 'Dubai', 'United Arab Emirates',
   'The sail-shaped icon of Jumeirah Beach, defined by gold-leaf suites and Arabian opulence.',
   5, 2100, 2750, 'USD', '#0b2a4a', '#1d6fa5',
   'https://images.unsplash.com/photo-1512453979798-5ea266f8880c?auto=format&fit=crop&w=1600&q=80',
   'jumeirah', array['beachfront','urban','contemporary','family']),

  ('singita-sasakwa', 'Singita Sasakwa Lodge', 'Serengeti', 'Tanzania',
   'An Edwardian-style safari lodge on a private hill, overlooking the Serengeti plains.',
   5, 2460, 2400, 'USD', '#3a2a12', '#9a6b2f',
   'https://images.unsplash.com/photo-1516026672322-bc52d61a55d5?auto=format&fit=crop&w=1600&q=80',
   'singita', array['safari','adventure','wellness','family']),

  ('claridges-london', 'Claridge''s', 'London', 'United Kingdom',
   'Art Deco grandeur in the heart of Mayfair, a byword for understated British luxury.',
   5, 815, 950, 'GBP', '#26282b', '#4a4f57',
   'https://images.unsplash.com/photo-1513635269975-59663e0ac1ad?auto=format&fit=crop&w=1600&q=80',
   'maybourne', array['urban','art-deco','heritage','palace']),

  ('raffles-singapore', 'Raffles Singapore', 'Singapore', 'Singapore',
   'A restored colonial icon of arcades and suites, birthplace of the Singapore Sling since 1887.',
   5, 1010, 1080, 'USD', '#173a2f', '#3f7d5e',
   'https://images.unsplash.com/photo-1525625293386-3f8f99389edd?auto=format&fit=crop&w=1600&q=80',
   'raffles', array['urban','heritage','palace','romance'])
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
  image_url    = excluded.image_url,
  brand_id     = excluded.brand_id,
  tags         = excluded.tags;

-- --- Rate history (nine weekly captures per property) ------------------------
insert into public.rate_history (property_id, captured_on, rate) values
  ('aman-tokyo','2026-04-27',1345),('aman-tokyo','2026-05-04',1280),('aman-tokyo','2026-05-11',1385),
  ('aman-tokyo','2026-05-18',1320),('aman-tokyo','2026-05-25',1265),('aman-tokyo','2026-06-01',1360),
  ('aman-tokyo','2026-06-08',1305),('aman-tokyo','2026-06-15',1335),('aman-tokyo','2026-06-22',1130),

  ('aman-venice','2026-04-27',1885),('aman-venice','2026-05-04',1795),('aman-venice','2026-05-11',1945),
  ('aman-venice','2026-05-18',1850),('aman-venice','2026-05-25',1775),('aman-venice','2026-06-01',1905),
  ('aman-venice','2026-06-08',1830),('aman-venice','2026-06-15',1870),('aman-venice','2026-06-22',1480),

  ('belmond-caruso','2026-04-27',1550),('belmond-caruso','2026-05-04',1475),('belmond-caruso','2026-05-11',1595),
  ('belmond-caruso','2026-05-18',1520),('belmond-caruso','2026-05-25',1460),('belmond-caruso','2026-06-01',1565),
  ('belmond-caruso','2026-06-08',1505),('belmond-caruso','2026-06-15',1535),('belmond-caruso','2026-06-22',1490),

  ('belmond-cipriani','2026-04-27',1815),('belmond-cipriani','2026-05-04',1725),('belmond-cipriani','2026-05-11',1870),
  ('belmond-cipriani','2026-05-18',1780),('belmond-cipriani','2026-05-25',1710),('belmond-cipriani','2026-06-01',1835),
  ('belmond-cipriani','2026-06-08',1760),('belmond-cipriani','2026-06-15',1800),('belmond-cipriani','2026-06-22',1510),

  ('four-seasons-bora-bora','2026-04-27',2345),('four-seasons-bora-bora','2026-05-04',2230),('four-seasons-bora-bora','2026-05-11',2415),
  ('four-seasons-bora-bora','2026-05-18',2300),('four-seasons-bora-bora','2026-05-25',2210),('four-seasons-bora-bora','2026-06-01',2370),
  ('four-seasons-bora-bora','2026-06-08',2275),('four-seasons-bora-bora','2026-06-15',2325),('four-seasons-bora-bora','2026-06-22',1820),

  ('four-seasons-george-v','2026-04-27',1940),('four-seasons-george-v','2026-05-04',1845),('four-seasons-george-v','2026-05-11',1995),
  ('four-seasons-george-v','2026-05-18',1900),('four-seasons-george-v','2026-05-25',1825),('four-seasons-george-v','2026-06-01',1955),
  ('four-seasons-george-v','2026-06-08',1880),('four-seasons-george-v','2026-06-15',1920),('four-seasons-george-v','2026-06-22',1830),

  ('mandarin-oriental-bangkok','2026-04-27',795),('mandarin-oriental-bangkok','2026-05-04',755),('mandarin-oriental-bangkok','2026-05-11',820),
  ('mandarin-oriental-bangkok','2026-05-18',780),('mandarin-oriental-bangkok','2026-05-25',750),('mandarin-oriental-bangkok','2026-06-01',805),
  ('mandarin-oriental-bangkok','2026-06-08',770),('mandarin-oriental-bangkok','2026-06-15',790),('mandarin-oriental-bangkok','2026-06-22',690),

  ('rosewood-hong-kong','2026-04-27',940),('rosewood-hong-kong','2026-05-04',890),('rosewood-hong-kong','2026-05-11',965),
  ('rosewood-hong-kong','2026-05-18',920),('rosewood-hong-kong','2026-05-25',885),('rosewood-hong-kong','2026-06-01',950),
  ('rosewood-hong-kong','2026-06-08',910),('rosewood-hong-kong','2026-06-15',930),('rosewood-hong-kong','2026-06-22',740),

  ('burj-al-arab','2026-04-27',2805),('burj-al-arab','2026-05-04',2670),('burj-al-arab','2026-05-11',2885),
  ('burj-al-arab','2026-05-18',2750),('burj-al-arab','2026-05-25',2640),('burj-al-arab','2026-06-01',2830),
  ('burj-al-arab','2026-06-08',2720),('burj-al-arab','2026-06-15',2775),('burj-al-arab','2026-06-22',2100),

  ('singita-sasakwa','2026-04-27',2450),('singita-sasakwa','2026-05-04',2330),('singita-sasakwa','2026-05-11',2520),
  ('singita-sasakwa','2026-05-18',2400),('singita-sasakwa','2026-05-25',2305),('singita-sasakwa','2026-06-01',2470),
  ('singita-sasakwa','2026-06-08',2375),('singita-sasakwa','2026-06-15',2425),('singita-sasakwa','2026-06-22',2460),

  ('claridges-london','2026-04-27',970),('claridges-london','2026-05-04',920),('claridges-london','2026-05-11',1000),
  ('claridges-london','2026-05-18',950),('claridges-london','2026-05-25',910),('claridges-london','2026-06-01',980),
  ('claridges-london','2026-06-08',940),('claridges-london','2026-06-15',960),('claridges-london','2026-06-22',815),

  ('raffles-singapore','2026-04-27',1100),('raffles-singapore','2026-05-04',1050),('raffles-singapore','2026-05-11',1135),
  ('raffles-singapore','2026-05-18',1080),('raffles-singapore','2026-05-25',1035),('raffles-singapore','2026-06-01',1110),
  ('raffles-singapore','2026-06-08',1070),('raffles-singapore','2026-06-15',1090),('raffles-singapore','2026-06-22',1010)
on conflict (property_id, captured_on) do update set rate = excluded.rate;
