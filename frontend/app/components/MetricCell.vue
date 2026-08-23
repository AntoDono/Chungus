<script setup lang="ts">
const props = defineProps<{ label: string; value: string | number; hint?: string }>()
</script>

<template>
  <div class="hairline bg-paper/40 px-4 py-4 dark:bg-night-muted/40">
    <p class="text-[0.65rem] uppercase tracking-ledger text-paper-faint dark:text-night-faint">{{ props.label }}</p>
    <p class="mt-2 font-display text-3xl tabular tracking-tight">{{ props.value }}</p>
    <p v-if="props.hint" class="mt-1 text-xs text-paper-faint dark:text-night-faint">{{ props.hint }}</p>
  </div>
</template>
