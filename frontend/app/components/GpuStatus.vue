<script setup lang="ts">
import type { GpuStatusPayload } from '~/types/api'

const props = withDefaults(defineProps<{
  pollMs?: number
}>(), {
  pollMs: 15000,
})

const payload = ref<GpuStatusPayload | null>(null)
const loading = ref(true)
const error = ref('')

let timer = 0
let inFlight = false
let aborted = false

async function refresh() {
  if (inFlight || aborted || (typeof document !== 'undefined' && document.hidden)) return
  inFlight = true
  try {
    payload.value = await $fetch<GpuStatusPayload>('/internal/public/gpu', { credentials: 'include' })
    error.value = payload.value.error || ''
  } catch (err: unknown) {
    if (!aborted) error.value = (err as { message?: string }).message || 'GPU telemetry unavailable.'
  } finally {
    inFlight = false
    loading.value = false
  }
}

function onVisibility() {
  if (!document.hidden) refresh()
}

onMounted(() => {
  refresh()
  timer = window.setInterval(refresh, props.pollMs)
  document.addEventListener('visibilitychange', onVisibility)
})
onUnmounted(() => {
  aborted = true
  if (timer) window.clearInterval(timer)
  document.removeEventListener('visibilitychange', onVisibility)
})

function fmt(n: number | null | undefined, suffix = '') {
  if (n == null || Number.isNaN(Number(n))) return '—'
  const value = Number(n)
  const shown = Number.isInteger(value) ? value.toString() : value.toFixed(1)
  return suffix ? `${shown}${suffix}` : shown
}

function isEnabled(gpu: { in_use?: boolean }) {
  if (!payload.value?.cuda_visible_devices) return true
  return gpu.in_use === true
}
</script>

<template>
  <section>
    <div class="mb-4 flex items-end justify-between gap-4">
      <div>
        <p class="text-[0.65rem] uppercase tracking-ledger text-paper-faint dark:text-night-faint">Hardware</p>
        <h2 class="font-display text-2xl">GPU status</h2>
      </div>
      <p class="text-right text-[0.65rem] uppercase tracking-ledger text-paper-faint">
        <span v-if="payload?.cuda_visible_devices">CUDA_VISIBLE_DEVICES={{ payload.cuda_visible_devices }}</span>
        <span v-else>CUDA_VISIBLE_DEVICES unset · all enabled</span>
        <span v-if="payload?.collected_at" class="mt-1 block">{{ new Date(payload.collected_at).toLocaleTimeString() }}</span>
      </p>
    </div>

    <LoadingBlock v-if="loading" label="Reading GPUs" height="8rem" />
    <p v-else-if="error && !payload?.gpus?.length" class="hairline p-4 text-sm text-oxide">{{ error }}</p>
    <p v-else-if="!payload?.available" class="hairline p-4 text-sm text-paper-faint">
      No NVIDIA devices reported.
    </p>
    <div v-else class="grid gap-4 md:grid-cols-2">
      <article
        v-for="gpu in payload.gpus"
        :key="gpu.uuid || gpu.index"
        class="border p-4"
        :class="isEnabled(gpu) ? 'border-oxide' : 'border-[#b42318]'"
      >
        <div class="flex items-baseline justify-between gap-3">
          <div>
            <p
              class="text-[0.65rem] uppercase tracking-ledger"
              :class="isEnabled(gpu) ? 'text-oxide' : 'text-[#b42318]'"
            >
              {{ isEnabled(gpu) ? 'Enabled' : 'Disabled' }}
            </p>
            <h3 class="font-display text-lg leading-tight">{{ gpu.name }}</h3>
          </div>
          <span class="font-mono text-[0.65rem] text-paper-faint">#{{ gpu.index }} · {{ gpu.pstate || '—' }}</span>
        </div>

        <div class="mt-5 flex items-end justify-around gap-4">
          <GaugePie label="Util" :value="gpu.utilization_gpu" :display="fmt(gpu.utilization_gpu, '%')" />
          <GaugePie
            label="VRAM"
            :value="gpu.memory_pct"
            :display="gpu.memory_pct != null ? `${Math.round(gpu.memory_pct)}%` : '—'"
          />
          <GaugePie
            label="Power"
            :value="gpu.power_draw_w"
            :max="gpu.power_limit_w || 100"
            :display="fmt(gpu.power_draw_w, 'W')"
          />
          <MeterBar
            vertical
            label="Temp"
            :value="gpu.temperature_c"
            :max="100"
            :display="fmt(gpu.temperature_c, '°C')"
          />
          <MeterBar
            vertical
            label="Fan"
            :value="gpu.fan_speed_pct"
            :display="fmt(gpu.fan_speed_pct, '%')"
          />
        </div>

        <dl class="mt-5 grid grid-cols-2 gap-x-4 gap-y-2 text-xs sm:grid-cols-3">
          <div>
            <dt class="text-[0.65rem] uppercase tracking-ledger text-paper-faint">Voltage</dt>
            <dd class="mt-0.5 font-mono tabular">
              {{ gpu.voltage_mv != null ? `${fmt(gpu.voltage_mv)} mV` : '—' }}
            </dd>
          </div>
          <div>
            <dt class="text-[0.65rem] uppercase tracking-ledger text-paper-faint">Core</dt>
            <dd class="mt-0.5 font-mono tabular">{{ fmt(gpu.clock_graphics_mhz, ' MHz') }}</dd>
          </div>
          <div>
            <dt class="text-[0.65rem] uppercase tracking-ledger text-paper-faint">Mem clk</dt>
            <dd class="mt-0.5 font-mono tabular">{{ fmt(gpu.clock_memory_mhz, ' MHz') }}</dd>
          </div>
          <div class="sm:col-span-3">
            <dt class="text-[0.65rem] uppercase tracking-ledger text-paper-faint">PCIe</dt>
            <dd class="mt-0.5 font-mono tabular">
              {{ gpu.pcie_gen != null ? `Gen ${gpu.pcie_gen}` : '—' }}
              <span v-if="gpu.pcie_width"> ×{{ gpu.pcie_width }}</span>
              <span class="text-paper-faint"> · {{ fmt(gpu.memory_used_mb) }}/{{ fmt(gpu.memory_total_mb) }} MB</span>
            </dd>
          </div>
        </dl>
      </article>
    </div>
  </section>
</template>
