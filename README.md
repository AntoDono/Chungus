# CHUNGUS

**Computing Hybrid Utilization Network for GPU Unified Scheduling**

Personal GPU inference gateway: OpenAI-compatible API, vLLM and Ollama backends, session-based dashboard, and API key management with rate limiting.

## Repository layout

| Path | Role |
|------|------|
| [`server.js`](server.js) | Public entrypoint — spawns Django, proxies APIs, serves the Nuxt static app |
| [`frontend/`](frontend/) | Nuxt UI (landing, docs, login, role-aware dashboard) |
| [`backend/`](backend/) | Django API (inference, `/internal` session API, Django admin) |

```
Browser → :3567 (gateway)
              ├─ /, /docs, /login, /dashboard → Nuxt (static or dev :3001)
              ├─ /v1/*, /api/v1/* → Django
              ├─ /internal/* → Django
              └─ /admin/* → Django admin
```

## Quick start

### Prerequisites

- Node.js 20+
- Python 3.13 + [Poetry](https://python-poetry.org/) (backend)
- CUDA GPU (for vLLM) or [Ollama](https://ollama.com/) (local models)

### Setup

```bash
# Gateway + frontend deps
npm install

# Backend deps
cd backend && poetry install && cd ..

# Environment (see each .env.example)
cp .env.example .env
cp backend/.env.example backend/.env
cp frontend/.env.example frontend/.env
```

### Run (production-style)

```bash
npm run build    # nuxt generate → frontend/.output/public
npm start        # gateway on http://localhost:3567, Django on 127.0.0.1:8000
```

### Run (development)

```bash
# Terminal 1 — Nuxt HMR
npm run frontend:dev

# Terminal 2 — gateway proxies pages to :3001
npm run dev
```

Open **http://localhost:3567**. Django admin: **http://localhost:3567/admin/**.

### First-time backend

```bash
cd backend
poetry run python manage.py migrate
poetry run python manage.py createsuperuser
```

Create API keys and models via the dashboard (admin role) or Django admin.

## Public API

Bearer auth on `/v1/*` (gateway also accepts `/api/v1/*` as an alias):

- `POST /v1/chat/completions` — chat, streaming, thinking (Ollama), multimodal images
- `POST /v1/embeddings`
- `GET /v1/models`

Responses include `X-RateLimit-*` headers; `429` responses include `Retry-After`.

Interactive docs: **http://localhost:3567/docs**

## Configuration

| File | Purpose |
|------|---------|
| `.env.example` | Gateway (`PORT`, Django bind, dev proxy) |
| `backend/.env.example` | Django, HuggingFace, CUDA, vLLM, Ollama |
| `frontend/.env.example` | Nuxt dev port |

## Scripts

| Command | Description |
|---------|-------------|
| `npm start` | Build not required if `frontend/.output/public` exists; spawns Django + gateway |
| `npm run build` | Generate static frontend |
| `npm run dev` | Gateway + `NUXT_DEV=1` (proxy to Nuxt :3001) |
| `npm run frontend:dev` | Nuxt dev server only |

## Author

**Youwei Zhen** — [youweizhen.com](https://youweizhen.com) · [GitHub](https://github.com/antodono)
