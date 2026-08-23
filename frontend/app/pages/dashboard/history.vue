<script setup lang="ts">
import type { HistoryPage } from '~/types/api'

definePageMeta({ middleware: ['auth', 'admin'] })

const page = ref<HistoryPage | null>(null)
const loading = ref(true)
const filters = ref({ model_id: '', api_key_id: '', status: '' })

async function load(p = 1) {
  loading.value = true
  try {
    page.value = await api<HistoryPage>('/internal/admin/request-history', {
      query: {
        page: p,
        per_page: 50,
        model_id: filters.value.model_id || undefined,
        api_key_id: filters.value.api_key_id || undefined,
        status: filters.value.status || undefined,
      },
    })
  } finally {
    loading.value = false
  }
}

onMounted(() => load())
</script>

<template>
  <div>
    <p class="text-[0.7rem] uppercase tracking-ledger text-paper-faint">Admin</p>
    <h1 class="mb-6 font-display text-4xl">Global history</h1>
    <form class="mb-6 flex flex-wrap gap-4 text-sm" @submit.prevent="load(1)">
      <input v-model="filters.model_id" placeholder="model id" class="border-b border-paper-rule bg-transparent py-1 outline-none dark:border-night-rule">
      <input v-model="filters.api_key_id" placeholder="key id" class="border-b border-paper-rule bg-transparent py-1 outline-none dark:border-night-rule">
      <input v-model="filters.status" placeholder="status" class="border-b border-paper-rule bg-transparent py-1 outline-none dark:border-night-rule">
      <button type="submit" class="text-[0.7rem] uppercase tracking-ledger text-oxide">Filter</button>
    </form>
    <RequestTable
      :rows="page?.requests || []"
      :pagination="page?.pagination"
      :loading="loading"
      @page="load"
    />
  </div>
</template>
