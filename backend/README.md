# CHUNGUS Backend

Django 5 API for LLM inference, API key auth, session dashboard APIs, and admin. No server-rendered UI — the Nuxt app in `../frontend` is the web interface.

## Features

- OpenAI-compatible `/v1` API (chat, embeddings, models)
- Providers: **vLLM** (GPU) and **Ollama**
- API keys with per-minute / per-hour rate limits and usage headers
- Session + CSRF `/internal` API for the dashboard
- Roles via Django **Groups** (`user`, `admin`); `UserAPIKey` maps users to keys
- Model warmup background task (every 3 minutes for `alwayswarm` models)
- Django admin at `/admin/` (fallback)

## Requirements

- Python 3.13
- Poetry
- Optional: CUDA + vLLM, or Ollama on the host

## Setup

```bash
poetry install
cp .env.example .env
poetry run python manage.py migrate
poetry run python manage.py createsuperuser
```

Configure vLLM, Ollama, and Django in `.env` — see `.env.example` for `HF_TOKEN`, `CUDA_VISIBLE_DEVICES`, `OLLAMA_HOST`, and optional `VLLM_*` variables.

## Run standalone (without gateway)

```bash
poetry run python manage.py runserver 127.0.0.1:8000
```

In normal use, the repo root `server.js` spawns this process and proxies traffic.

## API surfaces

### Public LLM API (Bearer token)

| Method | Path | Notes |
|--------|------|-------|
| `POST` | `/v1/chat/completions` | Streaming, thinking (Ollama), images |
| `POST` | `/v1/embeddings` | |
| `GET` | `/v1/models` | |

Rate-limit headers: `X-RateLimit-Limit-Minute`, `X-RateLimit-Remaining-Minute`, `X-RateLimit-Limit-Hour`, `X-RateLimit-Remaining-Hour`. `429` includes `Retry-After`.

### Internal API (session cookie + CSRF)

Public: `GET /internal/health`, `GET /internal/public/stats`, auth csrf/login/logout.

Authenticated: `GET /internal/auth/me`, `GET /internal/me/keys`, `GET /internal/me/usage`, `GET /internal/me/requests`, …

Admin group: `GET|POST /internal/admin/models`, keys, users, chart-data, request-history.

Login flow: `GET /internal/auth/csrf` → `POST /internal/auth/login` with `X-CSRFToken`.

### Django admin

`/admin/` — full ORM access, user groups, model config.

## Models (database)

Configured in dashboard or admin:

- **Model** — `provider` (`vllm` | `ollama`), `model_type` (`chat` | `embedding`), path, sampling defaults, `thinking_mode`, `alwayswarm`, `is_default`
- **APIKey** — rate limits, usage counters
- **UserAPIKey** — user ↔ key ownership
- **LLMRequest** — request log

Per-model Ollama URL defaults from `OLLAMA_HOST` in `.env` when `ollama_base_url` is empty on the row.

## Project structure

```
Chungus/          Django settings, urls
LLM/
  views.py        /v1 handlers
  internal_views.py /internal handlers
  session_auth.py   groups, require_admin
  utils.py          vLLM / Ollama engines
  models.py
  management/commands/warmup_models.py
```

## Tests

```bash
poetry run python manage.py test LLM.tests
```

## Environment

Copy `backend/.env.example` → `backend/.env`. Key variables:

| Variable | Purpose |
|----------|---------|
| `DEBUG`, `SECRET_KEY`, `ALLOWED_HOSTS`, `CSRF_TRUSTED_ORIGINS` | Django |
| `HF_TOKEN` / `HUGGINGFACE_TOKEN` | Gated HuggingFace models (vLLM) |
| `CUDA_VISIBLE_DEVICES` | GPU selection |
| `OLLAMA_HOST` | Default Ollama base URL |
| `VLLM_*` | Optional vLLM worker tuning (see `.env.example`) |

Sampling defaults (`temperature`, `max_tokens`, `top_p`, …) are stored per **Model** row in the database and can be overridden per request.
