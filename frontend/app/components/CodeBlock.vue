<script setup lang="ts">
const props = defineProps<{ code: string }>()
const copied = ref(false)

async function copy() {
  await navigator.clipboard.writeText(props.code)
  copied.value = true
  setTimeout(() => {
    copied.value = false
  }, 1400)
}
</script>

<template>
  <div class="relative hairline bg-paper-muted/50 dark:bg-night-muted">
    <button
      type="button"
      class="absolute right-2 top-2 text-[0.65rem] uppercase tracking-wider text-oxide hover:underline"
      @click="copy"
    >
      {{ copied ? 'Copied' : 'Copy' }}
    </button>
    <pre class="overflow-x-auto p-4 pr-16 font-mono text-[0.78rem] leading-relaxed">{{ props.code }}</pre>
  </div>
</template>
