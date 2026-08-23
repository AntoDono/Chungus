<script setup lang="ts">
withDefaults(defineProps<{
  lines?: number
  height?: string
  label?: string
}>(), {
  lines: 0,
  height: '10rem',
  label: 'Loading',
})
</script>

<template>
  <div class="hairline p-4" role="status" aria-live="polite">
    <p class="mb-3 text-[0.65rem] uppercase tracking-ledger text-paper-faint dark:text-night-faint">
      {{ label }}…
    </p>
    <div class="space-y-2">
      <div
        class="loading-shimmer rounded-sm bg-paper-rule/70 dark:bg-night-rule"
        :style="{ height }"
      />
      <div
        v-for="n in lines"
        :key="n"
        class="loading-shimmer h-3 rounded-sm bg-paper-rule/60 dark:bg-night-rule/80"
        :class="n === lines ? 'w-2/3' : 'w-full'"
      />
    </div>
  </div>
</template>
