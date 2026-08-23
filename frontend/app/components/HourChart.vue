<script setup lang="ts">
import { Chart, type ChartConfiguration } from 'chart.js'

ensureChartJs()

const props = withDefaults(defineProps<{
  points: Array<{ hour: string; count: number; tokens?: number }>
  title?: string
  showTokens?: boolean
}>(), {
  title: 'Requests · last 24h',
  showTokens: true,
})

const { ink, faint, rule, oxide, glow } = useChartTheme()
const canvas = ref<HTMLCanvasElement | null>(null)
let chart: Chart<'line'> | null = null

function tick(hour: string) {
  const d = new Date(hour)
  if (Number.isNaN(d.getTime())) return hour
  return d.toLocaleTimeString([], { hour: 'numeric' })
}

const empty = computed(() => !props.points.some((p) => Number(p.count) || Number(p.tokens)))

function config(): ChartConfiguration<'line'> {
  return {
    type: 'line',
    data: {
      labels: props.points.map((p) => tick(p.hour)),
      datasets: [
        {
          label: 'Requests',
          data: props.points.map((p) => Number(p.count) || 0),
          borderColor: glow,
          backgroundColor: 'rgba(82, 183, 136, 0.18)',
          fill: true,
          tension: 0.35,
          pointRadius: 0,
          pointHoverRadius: 4,
          borderWidth: 2,
          yAxisID: 'y',
        },
        ...(props.showTokens
          ? [{
              label: 'Tokens',
              data: props.points.map((p) => Number(p.tokens) || 0),
              borderColor: oxide,
              backgroundColor: 'transparent',
              fill: false,
              tension: 0.35,
              pointRadius: 0,
              pointHoverRadius: 4,
              borderWidth: 1.5,
              borderDash: [4, 3],
              yAxisID: 'y1' as const,
            }]
          : []),
      ],
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      animation: false,
      plugins: {
        legend: {
          display: props.showTokens,
          labels: { color: faint.value, boxWidth: 10, font: { size: 10 } },
        },
        tooltip: {
          backgroundColor: '#141210',
          titleColor: ink.value,
          bodyColor: faint.value,
          borderColor: rule.value,
          borderWidth: 1,
        },
      },
      scales: {
        x: {
          grid: { color: rule.value },
          ticks: { color: faint.value, maxRotation: 0, autoSkip: true, maxTicksLimit: 8 },
        },
        y: {
          beginAtZero: true,
          grid: { color: rule.value },
          ticks: { color: faint.value, precision: 0 },
        },
        ...(props.showTokens
          ? {
              y1: {
                beginAtZero: true,
                position: 'right' as const,
                grid: { drawOnChartArea: false },
                ticks: { color: faint.value, precision: 0 },
              },
            }
          : {}),
      },
    },
  }
}

function paint() {
  if (!canvas.value || empty.value) return
  chart?.destroy()
  chart = new Chart(canvas.value, config())
}

onMounted(() => nextTick(paint))
watch(
  () => [props.points, props.showTokens, faint.value],
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
    <div v-if="empty" class="py-8 text-center text-sm text-paper-faint">No traffic yet.</div>
    <div v-else class="relative h-52 w-full">
      <canvas ref="canvas" />
    </div>
  </div>
</template>
