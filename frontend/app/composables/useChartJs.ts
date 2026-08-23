import {
  Chart,
  CategoryScale,
  LinearScale,
  PointElement,
  LineElement,
  LineController,
  BarElement,
  BarController,
  ArcElement,
  DoughnutController,
  Filler,
  Tooltip,
  Legend,
} from 'chart.js'

let registered = false

export function ensureChartJs() {
  if (registered) return
  Chart.register(
    CategoryScale,
    LinearScale,
    PointElement,
    LineElement,
    LineController,
    BarElement,
    BarController,
    ArcElement,
    DoughnutController,
    Filler,
    Tooltip,
    Legend,
  )
  Chart.defaults.font.family = 'IBM Plex Sans, ui-sans-serif, system-ui, sans-serif'
  Chart.defaults.font.size = 11
  registered = true
}
