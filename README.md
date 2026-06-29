# AURUM - Rate Intelligence for Luxury Stays

A polished, animated demo of a luxury-hotel **rate-intelligence platform**. It
tracks the prepaid nightly rate of the world's finest hotels, grades each rate
against its own history across **five intelligence levels**, surfaces market
intelligence (brand league tables, destination analysis, seasonality and a
rate-versus-signal view), and wraps it all in a loyalty programme, a saved
collection and a rate-alert system.

Built with the production stack it is meant to prove out: **Next.js (App
Router) + TypeScript + Tailwind CSS + Supabase** (Postgres, cookie-based auth
via `@supabase/ssr`, Row Level Security), with **Framer Motion** throughout.

> The hotels, brands and destinations are real. The rates, rate history and
> loyalty figures are illustrative sample data for demonstration only, not live
> or quoted prices.

---

## Feature tour

| Area | Route | What it does |
| --- | --- | --- |
| **Briefing** | `/` | The daily feed of luxury stays with live rate signals, filterable by ~20 thematic experience tags. Cinematic ken-burns hero, animated counters, staggered card reveals. |
| **The View** | `/the-view` | Market intelligence: an animated **brand league table**, **destination analysis**, a **seasonal heat map**, and a **rate-vs-signal scatter plot**. |
| **Collection** | `/collection` | A signed-in user's saved stays, persisted to Supabase and protected by Row Level Security. |
| **Reserve** | `/reserve` | A loyalty dashboard: tier ladder, animated credit counter, progress to the next tier, activity and privileges (sample membership). |
| **Property Intelligence** | `/property/[id]` | Per-property rate history (inline SVG sparkline), signal + intelligence level, brand and destination comparison, and booking buttons. |
| **Alerts** | `/alerts` | Alert preferences (threshold, frequency, channels, interests) plus a styled **weekly digest email** preview. |
| **Auth** | `/login`, `/signup` | Supabase email / password with cookie sessions and middleware-refreshed tokens. |

### Cross-cutting

- **Five intelligence levels** - every rate is graded L1 (at market) to L5
  (exceptional, 20%+ below its historical average). Levels are badged on cards
  and the property page, and explained on the Briefing.
- **Thematic experience tags** - ~20 tags (Setting / Style / Experience). The
  Briefing feed filters by tag with animated enter/exit transitions.
- **Affiliate booking links** - deep links to Trip.com, Booking.com and Agoda
  with tracking params, for anonymous and authenticated visitors alike.
- **Motion** - Framer Motion route transitions, scroll-reveals, staggered
  grids, animated counters, animated charts, micro-interactions and shimmer
  skeletons. Honors the OS "reduce motion" setting via `MotionConfig`.

### Runs with zero configuration

With no Supabase keys set, the app starts in **demo mode**: it serves bundled
illustrative sample data (the same dataset as `supabase/seed.sql`) so you can
preview the full UI instantly. Add Supabase keys to switch on live data, auth
and saved collections. No external calls are made at build time.

---

## Tech stack

| Layer      | Choice                                              |
| ---------- | --------------------------------------------------- |
| Framework  | Next.js 15 (App Router, Server Actions)             |
| Language   | TypeScript (strict)                                 |
| Styling    | Tailwind CSS 3                                       |
| Animation  | Framer Motion                                       |
| Backend    | Supabase (Postgres, Auth, Row Level Security)       |
| Auth glue  | `@supabase/ssr` (cookie sessions + middleware)      |
| Imagery    | `next/image` + Unsplash CDN, gradient/blur fallback |
| Charts     | Hand-rolled SVG + Framer Motion (no chart library)  |

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

Fill in the two values from your Supabase project
(**Dashboard -> Project Settings -> API**):

```
NEXT_PUBLIC_SUPABASE_URL=https://your-project-ref.supabase.co
NEXT_PUBLIC_SUPABASE_ANON_KEY=your-anon-public-key
```

Both keys are safe to expose to the browser; access is governed by Row Level
Security. Never put the `service_role` key in this file.

### 3. Apply the database schema + seed

In the Supabase dashboard **SQL Editor**, run in order:

1. `supabase/schema.sql` - tables (`properties`, `rate_history`, `collections`,
   `brands`, `tags`) and their RLS policies.
2. `supabase/seed.sql` - the brands, tags, twelve sample properties and their
   rate history.

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
2. In Vercel, **Add New -> Project** and import the repo. Next.js is
   auto-detected; no build settings to change.
3. Under **Settings -> Environment Variables**, add:
   - `NEXT_PUBLIC_SUPABASE_URL`
   - `NEXT_PUBLIC_SUPABASE_ANON_KEY`
4. Deploy. (Apply `supabase/schema.sql` + `supabase/seed.sql` to your Supabase
   project first.)
5. In Supabase **Authentication -> URL Configuration**, add your Vercel domain.

---

## Project structure

```
.
├── middleware.ts                 # refreshes the Supabase session, guards /collection
├── supabase/
│   ├── schema.sql                # tables + RLS (properties, rate_history, collections, brands, tags)
│   └── seed.sql                  # brands, tags, 12 properties + rate history
└── src/
    ├── app/
    │   ├── layout.tsx · template.tsx   # shell + route transitions
    │   ├── page.tsx                    # Briefing (feed + tag filter)
    │   ├── the-view/                   # market intelligence
    │   ├── reserve/                    # loyalty dashboard
    │   ├── alerts/                     # alert preferences + email preview
    │   ├── collection/                 # saved stays (RLS)
    │   ├── property/[id]/              # property intelligence (+ loading skeleton)
    │   ├── login/ · signup/            # auth pages (Server Actions)
    │   └── auth/actions.ts             # login / signup / signout / toggleSaved
    ├── components/                     # cards, charts, motion primitives, dashboards
    └── lib/
        ├── supabase/                   # browser, server, middleware clients
        ├── data.ts                     # repository: Supabase first, demo-data fallback
        ├── demo-data.ts                # bundled sample dataset (mirrors seed.sql)
        ├── analytics.ts                # brand / destination / scatter / seasonality
        ├── intelligence.ts             # the five intelligence levels
        ├── rates.ts · booking.ts · images.ts · format.ts · types.ts
```

---

## How the signal works

For each property we compare the **current prepaid rate** to its **historical
average**:

```
delta = (current - average) / average
```

The percentage below average maps to an intelligence level:

| Level | Below average | Meaning |
| ----- | ------------- | ------- |
| L5 | 20%+   | Exceptional |
| L4 | 12-20% | Strong (raises a **Rate Alert**) |
| L3 | 6-12%  | Notable |
| L2 | 2-6%   | Fair value |
| L1 | < 2%   | At market |

Thresholds live in `src/lib/intelligence.ts` and `src/lib/rates.ts`.

---

## Notes

- Sample data is centralised in `supabase/seed.sql` and `src/lib/demo-data.ts`.
  Loyalty and seasonality figures are computed sample data shown for
  illustration.
- The data layer degrades gracefully: if Supabase is unconfigured or a query
  fails, it falls back to the bundled dataset so the UI always renders.
- Photography loads at runtime from the free Unsplash CDN via `next/image`
  (host allow-listed in `next.config.mjs`); each photo sits over a gradient and
  blur placeholder so nothing renders broken.
- No real Supabase or third-party network calls happen during `npm run build`.
