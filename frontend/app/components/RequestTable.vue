<script setup lang="ts">
import type { HistoryItem, Pagination } from '~/types/api'

defineProps<{
  rows: HistoryItem[]
  pagination?: Pagination | null
  loading?: boolean
}>()

const emit = defineEmits<{ page: [number] }>()

function fmt(ts: string | null) {
  if (!ts) return '—'
  return new Date(ts).toLocaleString()
}
</script>

<template>
  <div class="hairline overflow-x-auto">
    <table class="min-w-full text-left text-sm">
      <thead class="border-b border-paper-rule text-[0.65rem] uppercase tracking-ledger text-paper-faint dark:border-night-rule dark:text-night-faint">
        <tr>
          <th class="px-3 py-2 font-medium">When</th>
          <th class="px-3 py-2 font-medium">Model</th>
          <th class="px-3 py-2 font-medium">Key</th>
          <th class="px-3 py-2 font-medium">Status</th>
          <th class="px-3 py-2 font-medium">Tokens</th>
        </tr>
      </thead>
      <tbody>
        <tr v-if="loading">
          <td colspan="5" class="px-3 py-8 text-center text-paper-faint">Loading…</td>
        </tr>
        <tr v-else-if="!rows.length">
          <td colspan="5" class="px-3 py-8 text-center text-paper-faint">No requests recorded.</td>
        </tr>
        <tr
          v-for="row in rows"
          :key="row.id"
          class="border-b border-paper-rule/70 last:border-0 dark:border-night-rule/70"
        >
          <td class="whitespace-nowrap px-3 py-2 font-mono text-xs tabular">{{ fmt(row.created_at) }}</td>
          <td class="px-3 py-2">{{ row.model_name }}</td>
          <td class="px-3 py-2">{{ row.api_key_name }}</td>
          <td class="px-3 py-2">
            <span :class="row.status === 'failed' ? 'text-oxide' : ''">{{ row.status }}</span>
          </td>
          <td class="px-3 py-2 font-mono text-xs tabular">{{ row.total_tokens }}</td>
        </tr>
      </tbody>
    </table>
    <div
      v-if="pagination && pagination.total_pages > 1"
      class="flex items-center justify-between border-t border-paper-rule px-3 py-2 text-xs dark:border-night-rule"
    >
      <span class="tabular text-paper-faint">{{ pagination.page }} / {{ pagination.total_pages }}</span>
      <div class="flex gap-3">
        <button
          type="button"
          :disabled="!pagination.has_previous"
          class="uppercase tracking-wider disabled:opacity-30"
          @click="emit('page', pagination.page - 1)"
        >
          Prev
        </button>
        <button
          type="button"
          :disabled="!pagination.has_next"
          class="uppercase tracking-wider disabled:opacity-30"
          @click="emit('page', pagination.page + 1)"
        >
          Next
        </button>
      </div>
    </div>
  </div>
</template>
