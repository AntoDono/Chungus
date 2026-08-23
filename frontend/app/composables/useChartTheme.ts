export function useChartTheme() {
  const colorMode = useColorMode()
  const dark = computed(() => colorMode.value === 'dark')

  return {
    dark,
    ink: computed(() => (dark.value ? '#efe6d8' : '#1c1814')),
    faint: computed(() => (dark.value ? '#9a9083' : '#6f675c')),
    rule: computed(() => (dark.value ? '#2e2923' : '#d9cfc0')),
    oxide: '#2d6a4f',
    glow: '#52b788',
    deep: '#1b4332',
  }
}
