<script setup lang="ts">
import { Chart, type ChartConfiguration } from 'chart.js'

ensureChartJs()

const props = withDefaults(defineProps<{
  title?: string
  slices: Array<{ name: string; value: number }>
  emptyText?: string
}>(), {
  title: 'Models · 24h',
  emptyText: 'Quiet bench.',
})

const { ink, faint, rule, oxide, glow, deep } = useChartTheme()
const palette = [glow, oxide, deep, '#74c69d', '#95d5b2', '#1b4332']
const canvas = ref<HTMLCanvasElement | null>(null)
let chart: Chart<'doughnut'> | null = null

function config(): ChartConfiguration<'doughnut'> {
  return {
    type: 'doughnut',
    data: {
      labels: props.slices.map((s) => s.name),
      datasets: [
        {
          data: props.slices.map((s) => Number(s.value) || 0),
          backgroundColor: props.slices.map((_, i) => palette[i % palette.length]),
          borderColor: rule.value,
          borderWidth: 1,
        },
      ],
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      animation: false,
      plugins: {
        legend: {
          position: 'right',
          labels: { color: faint.value, boxWidth: 10, font: { size: 10 } },
        },
        tooltip: {
          backgroundColor: '#141210',
          titleColor: ink.value,
          bodyColor: faint.value,
        },
      },
      cutout: '62%',
    },
  }
}

function paint() {
  if (!canvas.value || !props.slices.length) return
  chart?.destroy()
  chart = new Chart(canvas.value, config())
}

onMounted(() => nextTick(paint))
watch(
  () => [props.slices, faint.value],
  () => nextTick(paint),
  { deep: true },
)
onUnmounted(() => {
  chart?.destroy()
  chart = null
})
</script>

<template>
  <div class="hairline p-4">
    <p class="mb-4 text-[0.65rem] uppercase tracking-ledger text-paper-faint dark:text-night-faint">
      {{ title }}
    </p>
    <div v-if="!slices.length" class="py-8 text-center text-sm text-paper-faint">{{ emptyText }}</div>
    <div v-else class="relative h-52 w-full">
      <canvas ref="canvas" />
    </div>
  </div>
</template>
