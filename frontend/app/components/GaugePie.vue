<script setup lang="ts">
const props = withDefaults(defineProps<{
  label: string
  value: number | null | undefined
  max?: number
  display?: string
}>(), {
  max: 100,
})

const pct = computed(() => {
  if (props.value == null || !props.max) return 0
  return Math.min(100, Math.max(0, (Number(props.value) / props.max) * 100))
})

const sweep = computed(() => `${pct.value * 3.6}deg`)
</script>

<template>
  <div class="flex flex-col items-center gap-2">
    <div
      class="relative size-[4.75rem] rounded-full"
      :style="{ background: `conic-gradient(#52b788 ${sweep}, rgb(46 41 35 / 0.9) 0)` }"
      role="img"
      :aria-label="`${label} ${display || `${Math.round(pct)}%`}`"
    >
      <div class="absolute inset-[0.55rem] rounded-full bg-paper dark:bg-night" />
      <span class="absolute inset-0 grid place-items-center font-mono text-[0.7rem] tabular">
        {{ display || `${Math.round(pct)}%` }}
      </span>
    </div>
    <p class="text-[0.65rem] uppercase tracking-ledger text-paper-faint">{{ label }}</p>
  </div>
</template>
