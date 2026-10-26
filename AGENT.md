# AGENT.md — Chungus agent guide

Instructions for AI agents (and humans) working in this repo. Read this before making changes.

## How to search this file

Every rule is one line with a tag: `[AREA-NN]`. One rule per line, so grep returns complete rules.

```bash
grep -n "\[GIT-"   AGENT.md   # git rules
grep -n "\[CPP-"   AGENT.md   # C++ rules
grep -n "\[PY-"    AGENT.md   # Python / Django rules
grep -n "\[FE-"    AGENT.md   # frontend rules
grep -n "\[ENG-"   AGENT.md   # inference engine rules
grep -n "\[BENCH-" AGENT.md   # benchmarking rules
grep -n "\[DOC-"   AGENT.md   # documentation / this file
grep -n "\[MEM-"   AGENT.md   # maintaining this file
grep -n "\["       AGENT.md   # every rule
```

Areas: `GIT`, `MEM`, `GEN`, `CPP`, `PY`, `FE`, `ENG`, `BENCH`, `DOC`.

---

## Maintaining this file

- [MEM-01] Keep AGENT.md up to date: when the user states a new preference, convention, or correction, add it here as a tagged rule in the same change.
- [MEM-02] When a rule turns out wrong or outdated, edit or delete it; never leave contradicting rules.
- [MEM-03] When the folder structure changes (new top-level dir, moved module, new service), update "Repository structure" below.
- [MEM-04] One rule per line, starting with `- [AREA-NN]`. Number new rules after the last one in that area; don't renumber existing rules.
- [MEM-05] New area: add its tag to the "How to search" list and the Areas line.

## Git

- [GIT-01] NEVER commit. Do not run `git commit`, `git commit --amend`, or anything else that creates commits.
- [GIT-02] Do not stage files (`git add`) either. Leave every change unstaged in the working tree so the user can review the file diffs and commit themselves.
- [GIT-03] Never rewrite history or discard work: no `git reset --hard`, `git rebase`, `git push --force`, `git checkout -- <file>`, `git stash drop`, `git clean` unless the user explicitly asks.
- [GIT-04] Branching and pushing are the user's job. Don't create branches or push unless asked.
- [GIT-05] At the end of a task, list the files you changed so the user knows what to review.
- [GIT-06] Git submodules (e.g. `engine/llama.cpp`): add or bump only when the plan step calls for it, and tell the user the pinned commit.

## General

- [GEN-01] `plan.md` is the roadmap. Work phase by phase; tick checkboxes (`- [x]`) in `plan.md` when an item is done and verified.
- [GEN-02] vLLM and Ollama are being removed from serving. Don't add new vLLM/Ollama serving code; they only belong in `bench/baselines/`.
- [GEN-03] Prefer small, reviewable diffs. Don't reformat or refactor unrelated code in the same change.
- [GEN-04] Don't delete or overwrite files you didn't create without understanding why they exist; ask if unsure.
- [GEN-05] Secrets stay in `.env` files (gitignored). Only `.env.example` files are tracked; update them when adding a new setting.
- [GEN-06] Comments explain why, not what. Keep them short.

## C++ (engine/)

- [CPP-01] Use C++23 (`set(CMAKE_CXX_STANDARD 23)`, `CMAKE_CXX_STANDARD_REQUIRED ON`). Note: there is no C++21; the user asked for "C++21+", so C++23 is the target unless the user says C++20.
- [CPP-02] `using namespace ...;` is allowed only in `.cpp` files, never in `.hpp`/`.h` headers. Headers use fully qualified names.
- [CPP-03] All Chungus C++ code lives in `namespace chungus { ... }` (sub-namespaces allowed, e.g. `chungus::cache`).
- [CPP-04] Headers use `#pragma once`.
- [CPP-05] File extensions: `.hpp` for headers, `.cpp` for sources.
- [CPP-06] Our code goes in `engine/src/` (and the forked server in `engine/server/`). Never edit files inside the `engine/llama.cpp/` submodule.
- [CPP-07] Use RAII and smart pointers for llama.cpp handles (`llama_model`, `llama_context`, `llama_sampler`), with custom deleters calling the matching `*_free` function. No raw `new`/`delete`.
- [CPP-08] Prefer `std::span`, `std::string_view`, `std::optional`, `std::expected` (C++23) over raw pointers + sizes, sentinel values, or out-params.
- [CPP-09] No exceptions across the HTTP / llama.cpp boundary; return `std::expected` or error codes there.
- [CPP-10] Every divergence from upstream `llama.cpp/tools/server` is recorded in `engine/server/DIVERGENCE.md`.
- [CPP-11] Keep our logic behind small hooks in the forked server so llama.cpp upgrades stay easy to rebase.
- [CPP-12] Unit tests for core data structures (radix cache, scheduler, eviction) go in `engine/tests/`.
- [CPP-13] Build must work for CUDA (Linux, 5090 Blackwell + 3090 Ampere: set `CMAKE_CUDA_ARCHITECTURES` to cover both) and Metal (macOS dev on M4 Pro).

## Python / Django (backend/)

- [PY-01] Python 3.13, dependencies through Poetry (`backend/pyproject.toml`). Run commands with `poetry run ...` from `backend/`.
- [PY-02] Tests: `cd backend && poetry run pytest`. Add or update tests with every backend change.
- [PY-03] Django talks to the inference engine over HTTP only (`backend/LLM/engine/`). No in-process model loading in Django.
- [PY-04] Schema changes need a migration (`poetry run python manage.py makemigrations LLM`); don't edit already-applied migrations.
- [PY-05] Keep slow work (DB writes for logging, stats) off the request hot path where possible.
- [PY-06] Use real token counts from the engine's `usage`; no character-based estimates.

## Frontend (frontend/)

- [FE-01] Nuxt 4 + Vue 3 + Tailwind, TypeScript. Package manager is bun (`bun install`, `bun run`).
- [FE-02] Typecheck with `bun run --cwd frontend typecheck` after frontend changes.
- [FE-03] API types live in `frontend/app/types/api.ts`; update them alongside backend serializer changes.
- [FE-04] Reuse existing components (`GpuStatus`, `MeterBar`, `MetricCell`, charts) before writing new ones.

## Inference engine

- [ENG-01] Serving stack is llama.cpp only: stock `llama-server` first (Phase 1), then `chungus-server` (our fork, Phase 2+).
- [ENG-02] Address GPUs by UUID, never by index; launch engine processes with `CUDA_DEVICE_ORDER=PCI_BUS_ID`.
- [ENG-03] GPU assignment comes from the database (dashboard), not from `CUDA_VISIBLE_DEVICES` in `.env`.
- [ENG-04] The draft model for speculative decoding goes on the same GPU as its target model.
- [ENG-05] Split a model across GPUs only when it doesn't fit on one card.

## Benchmarking

- [BENCH-01] No optimization counts as done without before/after numbers from `bench/`.
- [BENCH-02] Compare on the same GPU, same model family and comparable quant, same prompts; record GPU, power limit, quant, and llama.cpp commit.
- [BENCH-03] Report median and p95 for TTFT, time per output token, throughput; warm-up runs are discarded.
- [BENCH-04] vLLM and Ollama run only from `bench/baselines/`, in their own environment, never as Chungus dependencies.

## Documentation

- [DOC-01] Update `README.md` / `backend/README.md` / `.env.example` files when behaviour, setup, or settings change.
- [DOC-02] Docs and comments are written in plain, normal English (not compressed or shorthand style).

---

## Repository structure

Current state (before the engine work in `plan.md`):

```
Chungus/
├── AGENT.md              this file
├── plan.md               engine roadmap (phases, GPU management, benchmarking)
├── README.md             project overview and setup
├── server.js             public gateway (:3567): spawns Django, proxies /v1, /internal, /admin; serves Nuxt
├── package.json          gateway deps (http-proxy) + scripts (start, dev, build, frontend:*)
├── .env.example          gateway settings (PORT, Django bind, dev proxy)
├── .nvmrc                Node 22.19.0
├── db.sqlite3            tracked by git at the root (only backend/db.sqlite3 is gitignored); don't modify
│
├── backend/              Django project (Python 3.13, Poetry)
│   ├── Chungus/          Django settings, root urls, wsgi/asgi
│   ├── LLM/              main app
│   │   ├── models.py         APIKey, UserAPIKey, Model, LLMRequest (+ roles/groups via migrations)
│   │   ├── views.py          public OpenAI-compatible API: /v1/chat/completions, /v1/embeddings, /v1/models
│   │   ├── utils.py          engine calls (currently vLLM/Ollama), thinking modes, rate limiting, prompt formatting
│   │   ├── internal_views.py /internal session API for the dashboard (auth, keys, models, users, stats, GPU)
│   │   ├── gpu.py            nvidia-smi polling for the GPU dashboard (15 s cache)
│   │   ├── auth.py           API-key bearer auth
│   │   ├── session_auth.py   dashboard session auth / roles
│   │   ├── admin.py          Django admin
│   │   ├── management/commands/warmup_models.py   alwayswarm warmup (to be replaced by the engine manager)
│   │   ├── migrations/       0001–0013
│   │   └── tests.py
│   ├── tests.py, conftest.py pytest setup
│   ├── folding@home/setup.sh  folding@home client setup (everything else in that dir is gitignored)
│   ├── staticfiles/      collected Django admin static files
│   ├── pyproject.toml, poetry.lock
│   └── .env.example      Django, HF token, CUDA, vLLM, Ollama settings (vLLM/Ollama parts to be removed)
│
└── frontend/             Nuxt 4 app (bun)
    └── app/
        ├── pages/        index, docs, login, dashboard/{index,history,keys,models,users}
        ├── components/   GpuStatus, charts, meters, RequestTable, AppHeader, dashboard/*
        ├── composables/  useApi, useAuth, useChartJs, useChartTheme
        ├── middleware/   auth, admin
        ├── layouts/, plugins/, assets/css/
        └── types/api.ts  API response types
```

Request flow: `Browser → server.js :3567 → Django :8000 (/v1, /internal, /admin)`; pages are served from `frontend/.output/public` (or proxied to Nuxt dev on :3001 with `npm run dev`).

Planned additions (see `plan.md`): `engine/` (llama.cpp submodule, `chungus-server`, C++ radix cache/scheduler), `bench/` (harness, baselines, results), `backend/LLM/engine/` (HTTP client + engine manager), `frontend/app/pages/dashboard/gpus.vue`.
