<script setup lang="ts">
import type { PublicStats } from '~/types/api'

const stats = ref<PublicStats | null>(null)
const healthy = ref<boolean | null>(null)

onMounted(async () => {
  try {
    const health = await $fetch<{ status?: string }>('/internal/health', { credentials: 'include' })
    healthy.value = health?.status === 'ok'
  } catch {
    healthy.value = false
  }
  try {
    stats.value = await $fetch<PublicStats>('/internal/public/stats', { credentials: 'include' })
  } catch {
    stats.value = { total_requests: 0, total_tokens: 0 }
  }
})

function fmt(n: number | undefined) {
  return new Intl.NumberFormat().format(n || 0)
}
</script>

<template>
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

    <div class="mt-10 grid gap-px bg-paper-rule dark:bg-night-rule sm:grid-cols-3">
      <div class="bg-paper px-5 py-6 dark:bg-night">
        <p class="text-[0.65rem] uppercase tracking-ledger text-paper-faint">System</p>
        <p class="mt-2 font-display text-2xl">
          <span :class="healthy === false ? 'text-oxide' : ''">
            {{ healthy == null ? 'Listening…' : healthy ? 'On the bench' : 'Offline' }}
          </span>
        </p>
      </div>
      <div class="bg-paper px-5 py-6 dark:bg-night">
        <p class="text-[0.65rem] uppercase tracking-ledger text-paper-faint">Requests</p>
        <p class="mt-2 font-display text-2xl tabular">{{ fmt(stats?.total_requests) }}</p>
      </div>
      <div class="bg-paper px-5 py-6 dark:bg-night">
        <p class="text-[0.65rem] uppercase tracking-ledger text-paper-faint">Tokens</p>
        <p class="mt-2 font-display text-2xl tabular">{{ fmt(stats?.total_tokens) }}</p>
      </div>
    </div>

    <div class="mt-10 flex flex-wrap gap-6 text-sm uppercase tracking-wider">
      <NuxtLink to="/docs" class="border-b border-oxide pb-0.5 text-oxide no-underline">
        API ledger
      </NuxtLink>
      <NuxtLink to="/login" class="border-b border-transparent pb-0.5 hover:border-paper-ink dark:hover:border-night-ink">
        Sign in
      </NuxtLink>
    </div>
  </div>
</template>
