<script setup lang="ts">
import type { HealthStatus, PublicStats } from '~/types/api'

const stats = ref<PublicStats | null>(null)
const healthy = ref<boolean | null>(null)
const latencyMs = ref<number | null>(null)
const uptimeSeconds = ref<number | null>(null)
const loading = ref(true)

onMounted(async () => {
  try {
    const started = performance.now()
    const health = await $fetch<HealthStatus>('/internal/health', { credentials: 'include' }).catch(() => null)
    latencyMs.value = Math.round(performance.now() - started)
    healthy.value = health?.status === 'ok'
    if (health?.uptime_seconds != null) uptimeSeconds.value = health.uptime_seconds

    const publicStats = await $fetch<PublicStats>('/internal/public/stats', { credentials: 'include' }).catch(() => null)
    stats.value = publicStats || { total_requests: 0, total_tokens: 0, hourly_requests: [] }
  } finally {
    loading.value = false
  }
})

function fmt(n: number | undefined) {
  return new Intl.NumberFormat().format(n || 0)
}

function fmtUptime(seconds: number | null) {
  if (seconds == null) return null
  const h = Math.floor(seconds / 3600)
  const m = Math.floor((seconds % 3600) / 60)
  if (h >= 24) {
    const d = Math.floor(h / 24)
    return `${d}d ${h % 24}h`
  }
  if (h > 0) return `${h}h ${m}m`
  if (m > 0) return `${m}m ${seconds % 60}s`
  return `${seconds}s`
}
</script>

<template>
  <div class="space-y-12">
    <div class="stagger">
      <p class="text-[0.7rem] uppercase tracking-ledger text-paper-faint dark:text-night-faint">
        Computing Hybrid Utilization Network for GPU Unified Scheduling
      </p>
      <h1 class="mt-6 font-display text-6xl font-semibold leading-[0.9] tracking-tight sm:text-8xl">
        CHUNGUS
      </h1>
      <p class="mt-6 max-w-xl text-lg leading-relaxed text-paper-faint dark:text-night-faint">
        Lab notebook for inference. Keys, rate limits, and a public OpenAI-compatible API —
        ruled in oxide on warm paper.
      </p>
    </div>

    <LoadingBlock v-if="loading" label="Reading the bench" height="6rem" :lines="1" />
    <template v-else>
      <div class="grid gap-px bg-paper-rule dark:bg-night-rule sm:grid-cols-3">
        <div class="bg-paper px-5 py-6 dark:bg-night">
          <p class="text-[0.65rem] uppercase tracking-ledger text-paper-faint">System</p>
          <p class="mt-2 font-display text-2xl tabular">
            <span :class="healthy === false ? 'text-[#b42318]' : ''">
              {{ healthy === false ? 'Offline' : latencyMs != null ? `${latencyMs} ms` : '—' }}
            </span>
          </p>
          <p class="mt-1 text-xs text-paper-faint">
            <template v-if="healthy === false">Health check failed</template>
            <template v-else>
              latency
              <span v-if="fmtUptime(uptimeSeconds)"> · up {{ fmtUptime(uptimeSeconds) }}</span>
            </template>
          </p>
        </div>
        <div class="bg-paper px-5 py-6 dark:bg-night">
          <p class="text-[0.65rem] uppercase tracking-ledger text-paper-faint">Requests</p>
          <p class="mt-2 font-display text-2xl tabular">{{ fmt(stats?.total_requests) }}</p>
          <p class="mt-1 text-xs text-paper-faint">{{ fmt(stats?.requests_24h) }} in 24h</p>
        </div>
        <div class="bg-paper px-5 py-6 dark:bg-night">
          <p class="text-[0.65rem] uppercase tracking-ledger text-paper-faint">Tokens</p>
          <p class="mt-2 font-display text-2xl tabular">{{ fmt(stats?.total_tokens) }}</p>
        </div>
      </div>

      <HourChart
        :points="stats?.hourly_requests || []"
        title="Throughput · last 24h"
      />
    </template>

    <GpuStatus />

    <div class="flex flex-wrap gap-6 text-sm uppercase tracking-wider">
      <NuxtLink to="/docs" class="border-b border-oxide pb-0.5 text-oxide no-underline">
        API docs
      </NuxtLink>
      <NuxtLink to="/login" class="border-b border-transparent pb-0.5 hover:border-paper-ink dark:hover:border-night-ink">
        Sign in
      </NuxtLink>
    </div>
  </div>
</template>
