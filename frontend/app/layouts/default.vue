<script setup lang="ts">
</script>

<template>
  <div class="min-h-screen">
    <AppHeader />
    <main class="mx-auto max-w-6xl px-6 py-10">
      <slot />
    </main>
    <footer class="mx-auto max-w-6xl px-6 pb-10 pt-4 text-[0.7rem] uppercase tracking-ledger text-paper-faint dark:text-night-faint">
      <div class="flex flex-wrap justify-between gap-2 border-t border-paper-rule pt-4 dark:border-night-rule">
        <span>Vol. I · GPU atelier</span>
        <a href="https://foldingathome.org" class="hover:text-oxide" rel="noreferrer" target="_blank">Folding@home</a>
      </div>
    </footer>
  </div>
</template>
