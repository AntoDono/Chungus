<script setup lang="ts">
const props = defineProps<{
  points: Array<{ hour: string; count: number }>
}>()

const max = computed(() => Math.max(1, ...props.points.map((p) => Number(p.count) || 0)))
</script>

<template>
  <div class="hairline p-4">
    <p class="mb-4 text-[0.65rem] uppercase tracking-ledger text-paper-faint dark:text-night-faint">
      Requests · last 24h
    </p>
    <div v-if="!points.length" class="py-8 text-center text-sm text-paper-faint">No traffic yet.</div>
    <div v-else class="flex h-36 items-end gap-1">
      <div
        v-for="(point, i) in points"
        :key="i"
        class="group relative flex-1 bg-oxide/80 hover:bg-oxide"
        :style="{ height: `${(Number(point.count) / max) * 100}%`, minHeight: point.count ? '2px' : '0' }"
        :title="`${point.hour}: ${point.count}`"
      />
    </div>
  </div>
</template>
