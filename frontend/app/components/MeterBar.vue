<script setup lang="ts">
const props = withDefaults(defineProps<{
  label: string
  value: number | null | undefined
  max?: number
  display?: string
  vertical?: boolean
}>(), {
  max: 100,
  vertical: false,
})

const pct = computed(() => {
  if (props.value == null || !props.max) return 0
  return Math.min(100, Math.max(0, (Number(props.value) / props.max) * 100))
})
</script>

<template>
  <div v-if="vertical" class="flex flex-col items-center gap-2">
    <p class="font-mono text-[0.7rem] tabular">{{ display || '—' }}</p>
    <div class="flex h-24 w-3 items-end overflow-hidden bg-paper-rule dark:bg-night-rule">
      <div class="w-full bg-oxide transition-[height] duration-300" :style="{ height: `${pct}%` }" />
    </div>
    <p class="text-[0.65rem] uppercase tracking-ledger text-paper-faint">{{ label }}</p>
  </div>
  <div v-else>
    <div class="mb-1 flex items-baseline justify-between gap-3">
      <p class="text-[0.65rem] uppercase tracking-ledger text-paper-faint">{{ label }}</p>
      <p class="font-mono text-xs tabular">{{ display || '—' }}</p>
    </div>
    <div class="h-2 overflow-hidden bg-paper-rule dark:bg-night-rule">
      <div class="h-full bg-oxide transition-[width] duration-300" :style="{ width: `${pct}%` }" />
    </div>
  </div>
</template>
