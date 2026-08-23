# CHUNGUS Frontend

Nuxt 4 static SPA for the CHUNGUS atelier console: landing, API docs, session login, and a role-aware dashboard.

## Stack

- Nuxt 4 (`ssr: false`, static generate)
- Tailwind CSS
- `@nuxt/icon`, `@nuxtjs/color-mode` (light default, dark mode)

All API calls are **same-origin** through the gateway (`/internal/*`). The browser never talks to Django on `:8000` directly.

## Routes

| Path | Access | Description |
|------|--------|-------------|
| `/` | Public | Landing, public stats |
| `/docs` | Public | API reference (auth, rate limits, endpoints) |
| `/login` | Public | Django session login |
| `/dashboard` | Auth | Usage, keys (user); models/keys/users/history (admin) |

Middleware: `auth` redirects unauthenticated users to `/login`; `admin` blocks non-admin routes.

## Setup

```bash
npm install
cp .env.example .env   # optional — NUXT_PORT, etc.
```

## Development

**Through the gateway (recommended):**

```bash
# repo root
npm run frontend:dev   # this app on :3001
npm run dev            # gateway on :3567 → proxies pages to :3001
```

**Frontend only** (API calls will fail unless gateway or Django is proxied):

```bash
npm run dev            # http://localhost:3001
```

## Production build

```bash
npm run generate       # output: .output/public
```

The root `npm run build` runs this automatically. The gateway serves `frontend/.output/public` with SPA fallback.

## Project structure

```
app/
  composables/   useApi, useAuth, useInternalApi
  middleware/    auth, admin
  pages/         index, docs, login, dashboard/*
  components/    layout, charts, dashboard panels
  assets/css/    main.css (design tokens)
```

## Configuration

See `.env.example`. Default Nuxt dev port is **3001** to match gateway `NUXT_PORT`.

## Typecheck

```bash
npm run typecheck
```
