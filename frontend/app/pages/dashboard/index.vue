<script setup lang="ts">
import type { ApiKeyRecord, ChartData, HistoryPage, UsageSnapshot } from '~/types/api'

const { user, isAdmin } = useAuth()
const keys = ref<ApiKeyRecord[]>([])
const usage = ref<UsageSnapshot | null>(null)
const history = ref<HistoryPage | null>(null)
const charts = ref<ChartData | null>(null)
const revealed = ref<Record<number, string>>({})
const error = ref('')

async function load(page = 1) {
  error.value = ''
  try {
    const [keyPayload, usagePayload, histPayload] = await Promise.all([
      api('/internal/me/keys'),
      api<UsageSnapshot>('/internal/me/usage'),
      api<HistoryPage>('/internal/me/requests', { query: { page, per_page: 20 } }),
    ])
    keys.value = unwrapList<ApiKeyRecord>(keyPayload, ['keys', 'api_keys'])
    usage.value = usagePayload
    history.value = histPayload
    if (isAdmin.value) {
      charts.value = await api<ChartData>('/internal/admin/chart-data')
    }
  } catch (err: unknown) {
    error.value = (err as { message?: string }).message || 'Could not load console.'
  }
}

async function reveal(id: number) {
  const data = await api<{ key: string }>(`/internal/me/keys/${id}/full`)
  revealed.value = { ...revealed.value, [id]: data.key }
}

async function copyKey(id: number) {
  let secret = revealed.value[id]
  if (!secret) {
    const data = await api<{ key: string }>(`/internal/me/keys/${id}/full`)
    secret = data.key
    revealed.value = { ...revealed.value, [id]: secret }
  }
  await navigator.clipboard.writeText(secret)
}

onMounted(() => load())
</script>

<template>
  <div class="space-y-10">
    <header class="stagger">
      <p class="text-[0.7rem] uppercase tracking-ledger text-paper-faint">
        {{ isAdmin ? 'Principal investigator' : 'Fellow' }} · {{ user?.username }}
      </p>
      <h1 class="mt-2 font-display text-4xl">Console</h1>
    </header>

    <p v-if="error" class="text-oxide">{{ error }}</p>

    <section v-if="isAdmin && charts" class="grid gap-4 md:grid-cols-2">
      <HourChart :points="charts.hourly_requests || []" />
      <div class="hairline p-4">
        <p class="mb-4 text-[0.65rem] uppercase tracking-ledger text-paper-faint">Models · 24h</p>
        <ul class="space-y-2 text-sm">
          <li v-for="m in charts.model_usage" :key="m.name" class="flex justify-between">
            <span>{{ m.name }}</span>
            <span class="font-mono tabular">{{ m.request_count }}</span>
          </li>
          <li v-if="!charts.model_usage?.length" class="text-paper-faint">Quiet bench.</li>
        </ul>
      </div>
    </section>

    <section class="grid gap-px bg-paper-rule dark:bg-night-rule sm:grid-cols-3">
      <MetricCell label="Requests" :value="usage?.total_requests ?? 0" hint="Owned keys" class="bg-paper dark:bg-night" />
      <MetricCell label="Tokens" :value="usage?.total_tokens ?? 0" class="bg-paper dark:bg-night" />
      <MetricCell label="Last 24h" :value="usage?.requests_24h ?? 0" class="bg-paper dark:bg-night" />
    </section>

    <section>
      <h2 class="mb-4 font-display text-2xl">Keys</h2>
      <div v-if="!keys.length" class="text-sm text-paper-faint">No keys bound to this account.</div>
      <div v-for="key in keys" :key="key.id" class="hairline mb-4 p-5">
        <div class="flex flex-wrap items-baseline justify-between gap-2">
          <h3 class="font-display text-xl">{{ key.name }}</h3>
          <span class="text-[0.65rem] uppercase tracking-ledger" :class="key.is_active ? 'text-oxide' : 'text-paper-faint'">
            {{ key.is_active ? 'Live' : 'Dormant' }}
          </span>
        </div>
        <p class="mt-1 text-sm text-paper-faint">{{ key.description || '—' }}</p>
        <p class="mt-3 font-mono text-sm">
          {{ revealed[key.id] || key.key_preview || '••••' }}
        </p>
        <div class="mt-3 flex gap-4 text-[0.7rem] uppercase tracking-wider">
          <button type="button" class="text-oxide" @click="reveal(key.id)">Reveal</button>
          <button type="button" @click="copyKey(key.id)">Copy</button>
        </div>
        <div class="mt-5 grid gap-4 sm:grid-cols-2">
          <UsageMeter
            :used="key.requests_this_minute ?? usage?.requests_this_minute ?? 0"
            :limit="key.rate_limit_per_minute"
            label="RPM"
          />
          <UsageMeter
            :used="key.requests_this_hour ?? usage?.requests_this_hour ?? 0"
            :limit="key.rate_limit_per_hour"
            label="RPH"
          />
        </div>
      </div>
    </section>

    <section>
      <h2 class="mb-4 font-display text-2xl">History</h2>
      <p class="mb-3 text-xs text-paper-faint">Prompts are omitted from this ledger.</p>
      <RequestTable
        :rows="history?.requests || []"
        :pagination="history?.pagination"
        @page="load"
      />
    </section>
  </div>
</template>
