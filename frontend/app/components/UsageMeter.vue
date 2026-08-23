<script setup lang="ts">
const props = defineProps<{ used: number; limit: number; label: string }>()
const pct = computed(() => {
  if (!props.limit) return 0
  return Math.min(100, Math.round((props.used / props.limit) * 100))
})
</script>

<template>
  <div>
    <div class="mb-1 flex justify-between text-[0.7rem] uppercase tracking-wider">
      <span>{{ props.label }}</span>
      <span class="tabular font-mono">{{ props.used }} / {{ props.limit }}</span>
    </div>
    <div class="h-px w-full bg-paper-rule dark:bg-night-rule">
      <div class="h-px bg-oxide" :style="{ width: `${pct}%` }" />
    </div>
  </div>
</template>
