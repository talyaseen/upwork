# AURUM - Rate Intelligence for Luxury Stays

A polished demo of a hotel rate-intelligence platform: it tracks the prepaid
nightly rate of the world's finest hotels, compares each rate to its historical
average, and raises a **Rate Alert** the moment a stay drops meaningfully below
its norm. Logged-in users save stays to a personal collection, and every
property links out to the major OTAs through affiliate-style booking links.

Built with the production stack it is meant to prove out: **Next.js (App
Router) + TypeScript + Tailwind CSS + Supabase** (Postgres, cookie-based auth
via `@supabase/ssr`, and Row Level Security).

> The hotels and destinations are real. The rates and rate history are
> illustrative sample data for demonstration only, not live or quoted prices.

---

## Features

- **Homepage feed** (`/`) - a responsive grid of luxury properties showing the
  current prepaid rate, its historical average, and a live rate signal. Stays
  are sorted by today's value against their average.
- **Property detail** (`/property/[id]`) - current vs historical rate, an inline
  SVG rate-history sparkline, a dated rate-history list, save-to-collection, and
  booking buttons.
- **Authentication** - email / password sign up and login using Supabase with
  cookie-based sessions (`@supabase/ssr`) and middleware-refreshed tokens.
- **Collection** (`/collection`) - a per-user saved set persisted to Supabase
  and protected by Row Level Security (each row owned by `auth.uid()`). This
  route is middleware-protected.
- **Booking links** - affiliate-style deep links to Trip.com, Booking.com, and
  Agoda with tracking params, working for anonymous and authenticated visitors.

### Runs with zero configuration

With no Supabase keys set, the app starts in **demo mode**: it serves bundled
illustrative sample data (the same dataset as `supabase/seed.sql`) so you can
preview the full UI instantly. Add Supabase keys to switch to live data, auth,
and collections. No network calls are made at build time.

---

## Tech stack

| Layer      | Choice                                              |
| ---------- | --------------------------------------------------- |
| Framework  | Next.js 15 (App Router, Server Actions)             |
| Language   | TypeScript (strict)                                 |
| Styling    | Tailwind CSS 3                                       |
| Backend    | Supabase (Postgres, Auth, Row Level Security)       |
| Auth glue  | `@supabase/ssr` (cookie sessions + middleware)      |
| Imagery    | `next/image` + Unsplash CDN, gradient/blur fallback |
| Charts     | Hand-rolled inline SVG sparkline (no chart library) |

---

## Local setup

### 1. Install

```bash
npm install
```

### 2. Configure environment (optional, but needed for auth + collections)

```bash
cp .env.local.example .env.local
```

Then fill in the two values from your Supabase project
(**Dashboard → Project Settings → API**):

```
NEXT_PUBLIC_SUPABASE_URL=https://your-project-ref.supabase.co
NEXT_PUBLIC_SUPABASE_ANON_KEY=your-anon-public-key
```

Both keys are safe to expose to the browser; access is governed by Row Level
Security. Never put the `service_role` key in this file.

### 3. Apply the database schema + seed

In the Supabase dashboard, open the **SQL Editor** and run, in order:

1. `supabase/schema.sql` - creates the `properties`, `rate_history`, and
   `collections` tables and their RLS policies.
2. `supabase/seed.sql` - inserts the eight sample properties and their rate
   history.

(Or, with the Supabase CLI: `supabase db push` after copying the SQL into a
migration.)

### 4. Run

```bash
npm run dev
```

Open <http://localhost:3000>.

---

## Scripts

| Command             | Purpose                          |
| ------------------- | -------------------------------- |
| `npm run dev`       | Start the dev server             |
| `npm run build`     | Production build                 |
| `npm run start`     | Serve the production build       |
| `npm run lint`      | ESLint (next/core-web-vitals)    |
| `npm run typecheck` | `tsc --noEmit` strict type-check |

---

## Deploy to Vercel

1. Push this repo to GitHub / GitLab / Bitbucket.
2. In Vercel, **Add New → Project** and import the repo. Vercel auto-detects
   Next.js; no build settings to change.
3. Under **Settings → Environment Variables**, add the two variables:
   - `NEXT_PUBLIC_SUPABASE_URL`
   - `NEXT_PUBLIC_SUPABASE_ANON_KEY`
4. Deploy. (Apply `supabase/schema.sql` + `supabase/seed.sql` to your Supabase
   project first, as above.)
5. In Supabase **Authentication → URL Configuration**, add your Vercel domain to
   the allowed redirect URLs.

---

## Project structure

```
.
├── middleware.ts                 # refreshes the Supabase session, guards /collection
├── supabase/
│   ├── schema.sql                # tables + RLS policies
│   └── seed.sql                  # 8 sample luxury hotels + rate history
└── src/
    ├── app/
    │   ├── layout.tsx            # shell: header, footer, fonts, metadata
    │   ├── page.tsx             # homepage feed
    │   ├── property/[id]/page.tsx
    │   ├── collection/page.tsx
    │   ├── login/ · signup/     # auth pages (Server Actions)
    │   └── auth/actions.ts      # login / signup / signout / toggleSaved
    ├── components/              # UI (cards, badges, sparkline, header, ...)
    └── lib/
        ├── supabase/            # browser, server, and middleware clients
        ├── data.ts              # repository: Supabase first, demo-data fallback
        ├── demo-data.ts         # bundled sample dataset (mirrors seed.sql)
        ├── rates.ts             # rate-signal math
        ├── booking.ts           # affiliate link builder
        └── types.ts
```

---

## How the rate signal works

For each property we compare the **current prepaid rate** to its **historical
average**:

```
delta = (current - average) / average
```

A property whose current rate is **10% or more** below its average earns a
**Rate Alert** (for example `Rate Alert -18% vs avg`). The threshold lives in
`src/lib/rates.ts`.

---

## Notes

- Demo data is clearly illustrative and centralised in `supabase/seed.sql` and
  `src/lib/demo-data.ts`.
- The data layer degrades gracefully: if Supabase is unconfigured or a query
  fails, it falls back to the bundled dataset so the UI always renders.
- Photography is loaded at runtime from the free Unsplash CDN via `next/image`
  (host allow-listed in `next.config.mjs`). Each photo sits over a gradient and
  blur placeholder derived from the property's accent colours, so nothing
  renders broken if an image is ever unavailable.
- No real Supabase or third-party network calls happen during `npm run build`.
