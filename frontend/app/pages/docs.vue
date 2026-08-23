<script setup lang="ts">
const sections = [
  { id: 'auth', label: 'Auth' },
  { id: 'rate', label: 'Rate limits' },
  { id: 'chat', label: 'Chat' },
  { id: 'stream', label: 'Streaming' },
  { id: 'thinking', label: 'Thinking' },
  { id: 'embed', label: 'Embeddings' },
  { id: 'models', label: 'Models' },
  { id: 'errors', label: 'Errors' },
]

const origin = computed(() => (import.meta.client ? window.location.origin : 'https://host'))
const v1 = computed(() => `${origin.value}/v1`)

const rateLimitBody = `{
  "error": {
    "message": "Rate limit exceeded",
    "type": "rate_limit_error",
    "code": "rate_limit_exceeded"
  }
}`

const chatCurl = computed(
  () => `curl -s ${v1.value}/chat/completions \\
  -H 'Authorization: Bearer YOUR_API_KEY' \\
  -H 'Content-Type: application/json' \\
  -d '{
    "model": "llama-2-7b-chat",
    "messages": [{"role": "user", "content": "Hello"}],
    "temperature": 0.7,
    "max_tokens": 512
  }'`,
)

const streamCurl = computed(
  () => `curl -N ${v1.value}/chat/completions \\
  -H 'Authorization: Bearer YOUR_API_KEY' \\
  -H 'Content-Type: application/json' \\
  -d '{"model": "llama-2-7b-chat", "stream": true, "messages": [{"role": "user", "content": "Hi"}]}'`,
)

const embedCurl = computed(
  () => `curl ${v1.value}/embeddings \\
  -H 'Authorization: Bearer YOUR_API_KEY' \\
  -H 'Content-Type: application/json' \\
  -d '{"model": "nomic-embed-text", "input": "Your text here"}'`,
)
</script>

<template>
  <div class="lg:grid lg:grid-cols-[200px_minmax(0,1fr)] lg:gap-10">
    <aside class="mb-10 lg:sticky lg:top-6 lg:mb-0 lg:self-start">
      <p class="text-[0.65rem] uppercase tracking-ledger text-paper-faint">Contents</p>
      <nav class="mt-3 flex flex-wrap gap-x-4 gap-y-2 text-sm lg:flex-col">
        <a
          v-for="s in sections"
          :key="s.id"
          :href="`#${s.id}`"
          class="text-paper-faint no-underline hover:text-oxide"
        >{{ s.label }}</a>
      </nav>
    </aside>

    <article class="space-y-16 text-[0.95rem] leading-relaxed">
      <header>
        <p class="text-[0.7rem] uppercase tracking-ledger text-paper-faint">Reference</p>
        <h1 class="mt-2 font-display text-5xl">API docs</h1>
        <p class="mt-4 max-w-2xl text-paper-faint dark:text-night-faint">
          Canonical paths are <code class="font-mono text-oxide">/v1/…</code>.
          The gateway also accepts <code class="font-mono">/api/v1/…</code> and rewrites to
          <code class="font-mono">/v1</code>. Bearer tokens on the public LLM API;
          dashboard session cookies stay on <code class="font-mono">/internal</code>.
        </p>
      </header>

      <section id="auth">
        <h2 class="font-display text-3xl">Authentication</h2>
        <p class="mt-3">Every public inference call needs</p>
        <CodeBlock :code="'Authorization: Bearer YOUR_API_KEY'" />
        <p class="mt-3 text-paper-faint">Missing or unknown keys return 401 with an OpenAI-shaped error object.</p>
      </section>

      <section id="rate">
        <h2 class="font-display text-3xl">Rate limiting</h2>
        <p class="mt-3">
          Limits are per API key: requests per minute (RPM) and per hour (RPH). When either bucket is exhausted the API returns
          <span class="font-mono text-oxide">429</span>.
        </p>
        <p class="mt-4 text-[0.65rem] uppercase tracking-ledger text-paper-faint">Response headers</p>
        <ul class="mt-2 space-y-1 font-mono text-sm">
          <li>X-RateLimit-Limit-Minute</li>
          <li>X-RateLimit-Remaining-Minute</li>
          <li>X-RateLimit-Limit-Hour</li>
          <li>X-RateLimit-Remaining-Hour</li>
          <li>Retry-After <span class="font-sans text-paper-faint">(seconds, on 429)</span></li>
        </ul>
        <p class="mt-4 text-[0.65rem] uppercase tracking-ledger text-paper-faint">429 body</p>
        <CodeBlock :code="rateLimitBody" />
      </section>

      <section id="chat">
        <h2 class="font-display text-3xl">Chat completions</h2>
        <p class="mt-2 font-mono text-sm text-oxide">POST {{ v1 }}/chat/completions</p>
        <p class="mt-3">OpenAI-compatible. Fields: <span class="font-mono">model</span>, <span class="font-mono">messages</span>, <span class="font-mono">stream</span>, sampling knobs, optional <span class="font-mono">thinking</span>.</p>
        <CodeBlock :code="chatCurl" />
      </section>

      <section id="stream">
        <h2 class="font-display text-3xl">Streaming</h2>
        <p class="mt-3">Set <span class="font-mono">stream: true</span>. The gateway preserves SSE. Chunks are <span class="font-mono">data: {json}</span> lines ending with <span class="font-mono">data: [DONE]</span>.</p>
        <CodeBlock :code="streamCurl" />
      </section>

      <section id="thinking">
        <h2 class="font-display text-3xl">Thinking</h2>
        <p class="mt-3">
          Ollama thinking models accept <span class="font-mono">thinking</span>:
          <span class="font-mono">default | low | medium | high | max | true | false</span>
          (also enabled/disabled). Trace is <span class="font-mono">message.thinking</span> or
          <span class="font-mono">delta.thinking</span>. vLLM ignores it. Resolution: request → model <span class="font-mono">thinking_mode</span> → default.
        </p>
      </section>

      <section id="embed">
        <h2 class="font-display text-3xl">Embeddings</h2>
        <p class="mt-2 font-mono text-sm text-oxide">POST {{ v1 }}/embeddings</p>
        <CodeBlock :code="embedCurl" />
      </section>

      <section id="models">
        <h2 class="font-display text-3xl">Models</h2>
        <p class="mt-2 font-mono text-sm text-oxide">GET {{ v1 }}/models</p>
        <p class="mt-3">Lists active models. If a requested name is missing, traffic routes to the type’s <span class="font-mono">is_default</span> model (or the first active by name). Response <span class="font-mono">model</span> is the one actually used.</p>
      </section>

      <section id="errors">
        <h2 class="font-display text-3xl">Errors</h2>
        <div class="mt-4 overflow-x-auto">
          <table class="w-full text-left text-sm">
            <thead class="text-[0.65rem] uppercase tracking-ledger text-paper-faint">
              <tr>
                <th class="py-2">HTTP</th>
                <th>Code</th>
                <th>Meaning</th>
              </tr>
            </thead>
            <tbody class="font-mono text-xs">
              <tr class="border-t border-paper-rule dark:border-night-rule"><td class="py-2">400</td><td>invalid_json / invalid_messages / invalid_thinking</td><td class="font-sans">Bad request</td></tr>
              <tr class="border-t border-paper-rule dark:border-night-rule"><td class="py-2">401</td><td>missing_api_key / invalid_api_key</td><td class="font-sans">Auth</td></tr>
              <tr class="border-t border-paper-rule dark:border-night-rule"><td class="py-2">404</td><td>model_not_found</td><td class="font-sans">No active model</td></tr>
              <tr class="border-t border-paper-rule dark:border-night-rule"><td class="py-2">429</td><td>rate_limit_exceeded</td><td class="font-sans">RPM / RPH</td></tr>
            </tbody>
          </table>
        </div>
      </section>
    </article>
  </div>
</template>
