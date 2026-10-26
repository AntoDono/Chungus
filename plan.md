# Chungus Engine Plan

## Objective

Replace vLLM and Ollama as serving backends with an in-house inference stack built on llama.cpp.

- **Serving:** only `chungus-server` (our fork of `llama-server`, built on llama.cpp).
- **vLLM / Ollama:** removed from the serving path entirely. They exist only inside the benchmark harness, as comparison baselines.
- **Django stays** as the gateway (auth, API keys, rate limits, logging, dashboard) and talks to `chungus-server` over HTTP.
- **Second goal:** learn how LLM inference optimization works by building the scheduler, KV cache, speculative decoding and structured output ourselves, and measuring every change.

Traffic is personal-scale (one user plus a few concurrent agents), so the target is **lowest latency for one user and good behaviour at 2–8 concurrent requests**, not datacenter throughput.

## Non-goals

- Writing our own model forward pass or CUDA kernels. llama.cpp/ggml provides those (flash attention, quantized matmuls, CUDA graphs).
- Matching vLLM at 32+ concurrent requests.
- Multi-node serving.

---

## Architecture

```
Browser / API clients
      │
      ▼
server.js gateway (:3567) ── Nuxt dashboard
      │
      ▼
Django (auth, rate limits, request logging, model registry, engine manager)
      │  HTTP (OpenAI-compatible + /chungus/* extensions), streamed SSE passthrough
      ▼
chungus-server  (one process per loaded model, pinned to a GPU via CUDA_VISIBLE_DEVICES)
 ├─ HTTP layer        forked from llama.cpp tools/server
 ├─ Scheduler         custom server loop: continuous batching, chunked prefill, priorities
 ├─ RadixCache        native C++: token-prefix tree → shared KV cells, LRU eviction
 ├─ KV tiering        VRAM → host RAM → disk (llama_state_seq_get/set_data)
 ├─ Speculative       none | draft model | n-gram lookup
 ├─ Structured output JSON schema / GBNF grammar sampling, jump-forward
 └─ libllama / ggml   llama.cpp as a git submodule, unmodified → CUDA (prod) / Metal (dev on M4 Pro)
```

### Repository layout (new)

```
engine/
  llama.cpp/            git submodule, pinned commit, never edited in place
  server/               our fork of llama.cpp/tools/server (chungus-server)
  src/                  our C++ additions: radix_cache.*, scheduler.*, kv_tier.*, ...
  tests/                C++ unit tests (radix tree, eviction, scheduler policies)
  CMakeLists.txt        builds chungus-server, linking llama + common from the submodule
bench/
  harness/              load generator + metrics collection (Python)
  baselines/            scripts to launch vLLM / Ollama / stock llama-server for comparison
  results/              JSON results + generated reports (gitignored except summaries)
backend/LLM/engine/     Django-side engine manager + HTTP client
```

The submodule stays pristine so upgrading llama.cpp is `git submodule update` plus rebasing our server fork.

### Hardware layout

| GPU | VRAM | Bandwidth | Role |
|---|---|---|---|
| RTX 5090 | 32 GB | 1792 GB/s | Main chat model + draft model (same card) |
| RTX 3090 #1 | 24 GB | 936 GB/s | Embeddings, small/fast router model, or a second chat model |
| RTX 3090 #2 | 24 GB | 936 GB/s | Optional: split with the 5090 for 70B-class models (`--tensor-split`) |
| RTX 3060 | 12 GB | 360 GB/s | Not used for serving (too slow); fine for benchmark baselines or embeddings |

Rule: split a model across GPUs only when it does not fit on one card. Layer split adds capacity, not speed.

These roles are defaults only. The real assignment is set in the dashboard (see GPU management) and stored in the database.

---

## GPU management (dashboard)

The dashboard decides which GPUs Chungus may use at all, and which GPU(s) each model runs on. This replaces `CUDA_VISIBLE_DEVICES` in `.env` as the source of truth.

### Concepts

- **GPU registry.** Every GPU detected by `nvidia-smi` gets a row, keyed by **UUID** (indexes can change after a reboot or driver update; UUIDs don't).
- **Chungus pool.** Each GPU is either **enabled** (Chungus may place models on it) or **disabled** (reserved for something else, e.g. folding@home, gaming, or benchmark baselines). Disabled GPUs are never touched.
- **Model placement.** Each model is assigned one GPU, or an ordered list of GPUs plus a `tensor_split` for models too big for one card. Only enabled GPUs can be selected. The draft model (speculative decoding) always goes on the target model's first GPU.
- **VRAM budget.** Per GPU: total VRAM, an optional reserved amount (headroom for the desktop or other processes), and the sum of estimated VRAM of assigned models (weights + KV cache at `n_ctx` + draft model + compute buffers).

### Data model

- [ ] `GPU`: `uuid` (unique), `index` (last seen), `name`, `vram_total_mb`, `enabled` (in Chungus pool), `reserved_mb`, `label`/notes, `last_seen_at`.
- [ ] `ModelPlacement` (or ordered M2M on `Model`): model → GPU(s) with order and split ratio.
- [ ] Sync job: on startup and from the dashboard "Rescan" button, upsert GPUs from `nvidia-smi`; mark missing GPUs as offline instead of deleting them.

### Engine manager behaviour

- [ ] Launch each model process with `CUDA_DEVICE_ORDER=PCI_BUS_ID` and `CUDA_VISIBLE_DEVICES=<uuids of assigned GPUs>`, plus `--tensor-split` when there are several.
- [ ] **Fit check before launch:** reject a placement if estimated VRAM exceeds `vram_total - reserved - already assigned`, with a clear message ("needs 26.1 GB, 21.4 GB free on RTX 3090 #1").
- [ ] **Reassigning a model** to another GPU = drain in-flight requests (or wait up to a timeout), stop the process, start it on the new GPU(s), health check, then route traffic again.
- [ ] **Disabling a GPU** that has models on it: the dashboard warns and lists them; on confirm, those models are stopped (or moved if the user picks a new GPU).
- [ ] GPU disappears or errors (Xid, OOM): affected models go to `error` state, visible in the dashboard.

### Dashboard page (`frontend/app/pages/dashboard/gpus.vue`)

- [ ] One card per GPU: name, UUID, enabled toggle, live utilization / VRAM / temperature / power (reuses `GpuStatus` and `backend/LLM/gpu.py`), VRAM bar split into **reserved / assigned by model / free**.
- [ ] Models listed on each GPU card with status (`stopped | loading | ready | draining | error`) and estimated vs actual VRAM.
- [ ] Assign model → GPU(s) from the GPU card or the models page; multi-GPU selection shows a `tensor_split` input with a suggested split based on bandwidth and VRAM.
- [ ] "Rescan GPUs" button and an "Apply" step that shows which processes will restart before doing it.
- [ ] Models page (`dashboard/models.vue`): GPU selector limited to enabled GPUs; speculative mode selector (`model only | draft | n-gram`).

### Benchmarks and the pool

- [ ] The bench harness reads the registry: it runs baselines (vLLM / Ollama / stock `llama-server`) only on a GPU chosen explicitly, and warns if that GPU currently serves a Chungus model.

---

## Phases

Each phase ends with a benchmark run against the previous phase. No phase is "done" without numbers.

### Phase 0 — Foundations and baseline

- [ ] Add llama.cpp as a submodule under `engine/llama.cpp`, pin a commit.
- [ ] Build scripts for CUDA (`-DGGML_CUDA=ON`) and Metal (macOS dev).
- [ ] Run stock `llama-server` with one model on the 5090.
- [ ] Bench harness v0 (see Benchmarking): run it against stock `llama-server`, vLLM, and Ollama on the same model and GPU. These are the baselines every later phase is compared against.

**Done when:** baseline report exists for at least one model at concurrency 1/2/4/8.

### Phase 1 — Django on llama.cpp, remove vLLM and Ollama

Django talks to stock `llama-server` first, so the gateway migration is separate from engine work.

Gateway:

- [ ] `backend/LLM/engine/client.py`: HTTP client for chat completions, embeddings, tokenize, metrics, slots.
- [ ] Real streaming: forward upstream SSE straight through (replaces the fake 5-character chunking in `views.py`).
- [ ] Switch gunicorn to gevent (or ASGI) workers so long streams don't block every other request.
- [ ] Chat templates applied by the server (`--jinja`). Delete `format_messages_for_prompt` (`"User: ...\n\nAssistant: ..."`).
- [ ] Real token counts from the server's `usage`; store `timings` (prompt tok/s, decode tok/s, `cache_n`, draft acceptance) in `LLMRequest.response_metadata`. Delete `count_tokens_approximate`.
- [ ] Thinking: map the existing `thinking` levels to `--reasoning-format`, `chat_template_kwargs.enable_thinking` and the reasoning budget.
- [ ] Images: `--mmproj` for vision models, pass OpenAI `image_url` parts through.
- [ ] Embeddings: `--embedding` server instance, batched requests (no per-text loop).
- [ ] Move rate-limit counting to an in-memory or cache-backed counter; write `LLMRequest` rows off the hot path.

Engine manager (`backend/LLM/engine/manager.py`):

- [ ] Start/stop one server process per active model with the right GPU, port and flags.
- [ ] Health checks (`/health`), restart on crash, unload idle models, VRAM budget per GPU.
- [ ] Replaces `alwayswarm` and the `warmup_models` command (models stay loaded; `--mlock`).
- [ ] GPU registry, Chungus GPU pool, per-model placement, fit checks and the GPU dashboard page (full spec in GPU management). `CUDA_VISIBLE_DEVICES` is removed from `backend/.env.example`.

Data model (`Model`):

- [ ] Remove `provider`, `ollama_base_url`, `huggingface_token` usage tied to vLLM.
- [ ] Add: `gguf_source` (HF `repo:quant` or local path), GPU placement (see GPU management), `tensor_split`, `n_ctx`, `n_parallel`, `kv_unified`, `cache_type_k/v`, `flash_attn`, `mmproj_source`, `extra_args`.
- [ ] Add speculative fields: `spec_mode` (`none | draft | ngram`), `draft_source`, `draft_max`, `draft_min`.
- [ ] Migration that converts existing rows (or drops them with a clear note).

Removal:

- [ ] Remove `vllm` and `ollama` from `backend/pyproject.toml`; regenerate `poetry.lock`.
- [ ] Remove vLLM/Ollama code paths from `utils.py`, `views.py`, `admin.py`, `internal_views.py`, `tests.py`, `warmup_models.py`.
- [ ] Update dashboard (`frontend/app/pages/dashboard/models.vue`, `frontend/app/types/api.ts`), docs page (`frontend/app/pages/docs.vue`), `README.md`, `backend/README.md`, `backend/.env.example`.
- [ ] vLLM/Ollama remain installable only through `bench/baselines/` (separate env).

**Done when:** `grep -ri "vllm\|ollama" backend frontend` only hits historical migrations; all API endpoints work through llama.cpp with real streaming; tests pass.

### Phase 2 — Fork llama-server into chungus-server

- [ ] Copy `tools/server` into `engine/server`, build it against the submodule as `chungus-server`.
- [ ] Behaviour identical to stock `llama-server` (same bench numbers within noise).
- [ ] Add `/chungus/metrics` (JSON): slots, KV usage, cache hit tokens, queue depth, acceptance rate.
- [ ] Django switches from stock `llama-server` to `chungus-server`.
- [ ] Document every divergence from upstream in `engine/server/DIVERGENCE.md` to keep rebases manageable.

**Done when:** Django runs on `chungus-server` with no regressions.

### Phase 3 — Custom server loop and batching

Replace the slot-based loop with our own scheduler.

- [ ] Request lifecycle: `waiting → prefilling → decoding → finished/aborted`, with cancellation when the client disconnects.
- [ ] One `llama_batch` per step: prefill chunks for new requests plus one decode token per running request.
- [ ] Chunked prefill with a per-step token budget, so long prompts don't stall running streams.
- [ ] Dynamic concurrency instead of a fixed `-np` slot count; sequence IDs allocated from a pool (`n_seq_max`).
- [ ] Scheduling policies: FCFS, longest-cached-prefix-first (needs Phase 4), per-API-key priority passed from Django.
- [ ] Backpressure: when KV memory is full, pause, evict or reject (503 + `Retry-After`) with a clear policy.

**Done when:** time per output token at concurrency 4 is no worse than stock `llama-server`, and time to first token for a short request stays low while a long prompt is prefilling.

### Phase 4 — KV cache: radix tree, LRU, tiering

All native C++ in `engine/src/`.

RadixCache:

- [ ] Radix tree keyed by token IDs. Each node: token span, owning sequence ID, reference count, last access time.
- [ ] `match_prefix(tokens)`, `insert(tokens, seq)`, `evict_lru(n_tokens)`.
- [ ] Sharing via llama.cpp cell tags: a new request with a cached prefix gets a new sequence ID and `llama_memory_seq_cp(src, dst, 0, prefix_len)`. The prefix is stored once.
- [ ] Eviction via `llama_memory_seq_rm`, never freeing cells another live node still references.
- [ ] Sequence-ID recycling, because `n_seq_max` caps the number of distinct cached paths.
- [ ] Unit tests for insert/match/split/evict and reference counting.

KV tiering and settings:

- [ ] Evicted prefixes spill to host RAM, then disk (`llama_state_seq_get_data` / `set_data`), restored on a hit.
- [ ] Quantized KV cache (`q8_0`) as a per-model setting; measure quality and speed.
- [ ] Context management when a conversation approaches `n_ctx` (context shift or summarisation hook).

Metrics:

- [ ] Cache hit tokens / prompt tokens per request, tree size, evictions, restores. Shown in the dashboard.

**Done when:** a repeated long system prompt shows near-zero prefill on later requests, 4 concurrent requests sharing a prefix use one copy of its KV, and the hit rate is visible in the dashboard.

### Phase 5 — Speculative decoding

- [ ] Modes per model, selectable in the dashboard: **model only**, **draft model**, **n-gram lookup**.
- [ ] Draft model on the same GPU as the target; tokenizer/vocab compatibility check at load time.
- [ ] Verify step: batch the draft tokens, read logits at every guessed position, accept/reject (greedy, and rejection sampling for temperature > 0).
- [ ] KV rollback of rejected positions in both target and draft contexts.
- [ ] Adaptive `draft_max` based on recent acceptance rate.
- [ ] Interaction with batching: speculative decoding per request inside the continuous batch.
- [ ] Metrics: acceptance rate, tokens per target pass, speedup vs model-only.

**Done when:** single-user decode tok/s improves on code/JSON workloads with identical output distribution, and acceptance rate is visible per request.

### Phase 6 — Structured output

- [ ] OpenAI `response_format` (`json_object`, `json_schema`) and raw GBNF grammars, passed from Django.
- [ ] Grammar sampler in the per-request sampler chain.
- [ ] Jump-forward decoding: when the grammar allows only one continuation, append those tokens without sampling.
- [ ] Optional "reason, then constrain" mode: free-form thinking, grammar applied only to the final answer.
- [ ] Tool calling output validated against the tool schema.

**Done when:** schema-constrained requests always return valid JSON, and jump-forward measurably reduces model passes on schema-heavy outputs.

### Phase 7 — Application-level features (gateway)

- [ ] Cache-friendly prompt assembly: stable content first (system, tools, documents), changing content last.
- [ ] Model routing: small model on the 3090 for simple tasks, main model on the 5090 for hard ones.
- [ ] Thinking budgets per request / per API key.
- [ ] Exact-match response cache for temperature-0 requests.
- [ ] Per-token logprobs view in the dashboard (`n_probs`), for transparency.

---

## Benchmarking

Built in Phase 0 and run at the end of every phase.

**Engines compared:** `chungus-server` (current phase), stock `llama-server`, vLLM, Ollama. vLLM and Ollama run only here, in their own environments under `bench/baselines/`.

**Fairness rules:**

- Same model weights family and comparable quantization (GGUF Q4_K_M vs AWQ/GPTQ 4-bit for vLLM; note the difference in the report).
- Same GPU, nothing else running on it, fixed power limit and clocks recorded.
- Same prompts, same `max_tokens`, temperature 0 unless the test is about sampling.
- Warm-up runs discarded; each configuration repeated at least 3 times; report median and p95.

**Metrics:**

| Metric | Meaning |
|---|---|
| TTFT | Time to first token |
| ITL / TPOT | Time per output token after the first |
| Decode tok/s | Single-stream generation speed |
| Prefill tok/s | Prompt processing speed |
| Throughput | Total output tok/s across all concurrent requests |
| Cache hit rate | Cached prompt tokens / total prompt tokens |
| Acceptance rate | Accepted draft tokens / proposed (speculative only) |
| VRAM | Peak memory per GPU |

**Workloads:**

- Short chat (≈200-token prompt, 256 output).
- Long context (8k–32k prompt, 256 output).
- Shared prefix (many requests, same 2k system prompt, different questions).
- Multi-turn conversation replay (growing history).
- Code/JSON generation (speculative decoding and structured output).
- Concurrency sweep: 1, 2, 4, 8.

**Tools:** our harness in `bench/harness/` (async OpenAI-compatible client that records per-token timestamps), plus `llama-bench` for raw kernel numbers, plus a roofline check: `bandwidth / bytes read per token` as the theoretical decode ceiling.

**Output:** JSON per run in `bench/results/`, a markdown summary per phase, and charts in the dashboard later.

---

## Risks

- **llama.cpp API churn.** The C API and server code change often (e.g. `llama_kv_self_`* → `llama_memory_*` in 2025). Mitigation: pinned submodule, `DIVERGENCE.md`, upgrade deliberately.
- **Server fork drift.** The more we change `tools/server`, the harder rebases get. Mitigation: keep our logic in `engine/src/` behind small hooks.
- **Sequence ID limits.** `n_seq_max` bounds concurrent and cached sequences; radix design must recycle IDs.
- **Mixed GPUs.** 5090 (Blackwell) and 3090 (Ampere) need a CUDA build that targets both architectures.
- **GPU identity.** CUDA and `nvidia-smi` can order devices differently. Mitigation: always address GPUs by UUID and set `CUDA_DEVICE_ORDER=PCI_BUS_ID`.
- **VRAM estimates.** The fit check is an estimate; real usage can be higher (compute buffers, fragmentation). Mitigation: compare estimate vs actual after load and show both in the dashboard.
- **Quality regressions from quantization or KV quantization.** Mitigation: perplexity checks with `llama-perplexity` per model/quant.

## Open questions

- Which models to serve first (main chat, draft, embedding)?
- Keep the current DB rows for models/requests, or start fresh after the migration?
- Engine manager in Django or in `server.js`?

## References

- llama.cpp: `tools/server/`, `examples/simple/`, `examples/speculative/`, `include/llama.h`
- SGLang paper (RadixAttention) and `sglang/srt/mem_cache/radix_cache.py`
- vLLM paper (PagedAttention); Orca paper (iteration-level scheduling)
- Speculative decoding: Leviathan et al. 2023; Chen et al. 2023; EAGLE
- FlashAttention 1/2, Flash-Decoding
- XGrammar / Outlines (constrained decoding); SGLang jump-forward decoding
