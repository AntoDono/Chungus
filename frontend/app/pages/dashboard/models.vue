<script setup lang="ts">
import type { ModelRecord } from '~/types/api'
import { emptyModelForm } from '~/types/api'

definePageMeta({ middleware: ['auth', 'admin'] })

const models = ref<ModelRecord[]>([])
const editing = ref<Partial<ModelRecord> | null>(null)
const error = ref('')
const saving = ref(false)
const loading = ref(true)

async function load() {
  if (!models.value.length) loading.value = true
  try {
    const payload = await api('/internal/admin/models')
    models.value = unwrapList<ModelRecord>(payload, ['models'])
  } finally {
    loading.value = false
  }
}

function openCreate() {
  editing.value = emptyModelForm()
}

function openEdit(model: ModelRecord) {
  editing.value = { ...model }
}

async function save() {
  if (!editing.value) return
  saving.value = true
  error.value = ''
  try {
    const body = editing.value
    if (body.id) {
      await api(`/internal/admin/models/${body.id}/update`, { method: 'POST', body })
    } else {
      await api('/internal/admin/models', { method: 'POST', body })
    }
    editing.value = null
    await load()
  } catch (err: unknown) {
    error.value = (err as { data?: { error?: string } }).data?.error || 'Save failed.'
  } finally {
    saving.value = false
  }
}

async function remove(id: number) {
  if (!confirm('Delete this model?')) return
  await api(`/internal/admin/models/${id}/delete`, { method: 'POST' })
  await load()
}

onMounted(load)
</script>

<template>
  <div>
    <div class="mb-8 flex items-end justify-between">
      <div>
        <p class="text-[0.7rem] uppercase tracking-ledger text-paper-faint">Admin</p>
        <h1 class="font-display text-4xl">Models</h1>
      </div>
      <button type="button" class="border border-oxide px-4 py-2 text-[0.7rem] uppercase tracking-ledger text-oxide" @click="openCreate">
        Add model
      </button>
    </div>

    <p v-if="error" class="mb-4 text-oxide">{{ error }}</p>
    <LoadingBlock v-if="loading" label="Loading models" height="8rem" />

    <div v-else class="hairline overflow-x-auto">
      <table class="min-w-full text-left text-sm">
        <thead class="text-[0.65rem] uppercase tracking-ledger text-paper-faint">
          <tr>
            <th class="px-3 py-2">Name</th>
            <th class="px-3 py-2">Provider</th>
            <th class="px-3 py-2">Type</th>
            <th class="px-3 py-2">Flags</th>
            <th class="px-3 py-2" />
          </tr>
        </thead>
        <tbody>
          <tr v-for="m in models" :key="m.id" class="border-t border-paper-rule dark:border-night-rule">
            <td class="px-3 py-2">{{ m.name }}</td>
            <td class="px-3 py-2 font-mono text-xs">{{ m.provider }}</td>
            <td class="px-3 py-2">{{ m.model_type }}</td>
            <td class="px-3 py-2 text-xs">
              <span v-if="m.is_default">default</span>
              <span v-if="m.alwayswarm"> · warm</span>
              <span v-if="!m.is_active" class="text-oxide"> · off</span>
            </td>
            <td class="px-3 py-2 text-right text-[0.7rem] uppercase tracking-wider">
              <button type="button" class="mr-3" @click="openEdit(m)">Edit</button>
              <button type="button" class="text-oxide" @click="remove(m.id)">Delete</button>
            </td>
          </tr>
        </tbody>
      </table>
    </div>

    <form v-if="editing" class="mt-8 grid gap-4 hairline p-5 sm:grid-cols-2" @submit.prevent="save">
      <h2 class="sm:col-span-2 font-display text-2xl">{{ editing.id ? 'Amend' : 'New plate' }}</h2>
      <label class="text-sm">Name
        <input v-model="editing.name" required class="mt-1 w-full border-b border-paper-rule bg-transparent py-1 outline-none dark:border-night-rule">
      </label>
      <label class="text-sm">Path
        <input v-model="editing.model_path" required class="mt-1 w-full border-b border-paper-rule bg-transparent py-1 font-mono text-xs outline-none dark:border-night-rule">
      </label>
      <label class="sm:col-span-2 text-sm">Description
        <input v-model="editing.description" class="mt-1 w-full border-b border-paper-rule bg-transparent py-1 outline-none dark:border-night-rule">
      </label>
      <label class="text-sm">Type
        <select v-model="editing.model_type" class="mt-1 w-full bg-transparent">
          <option value="chat">chat</option>
          <option value="embedding">embedding</option>
        </select>
      </label>
      <label class="text-sm">Provider
        <select v-model="editing.provider" class="mt-1 w-full bg-transparent">
          <option value="vllm">vllm</option>
          <option value="ollama">ollama</option>
        </select>
      </label>
      <label class="text-sm">Thinking mode
        <select v-model="editing.thinking_mode" class="mt-1 w-full bg-transparent">
          <option v-for="mode in ['default', 'low', 'medium', 'high', 'enabled', 'disabled', 'auto']" :key="mode" :value="mode">{{ mode }}</option>
        </select>
      </label>
      <label class="text-sm">Ollama URL
        <input v-model="editing.ollama_base_url" class="mt-1 w-full border-b border-paper-rule bg-transparent py-1 font-mono text-xs outline-none dark:border-night-rule">
      </label>
      <label class="text-sm">HF token
        <input v-model="editing.huggingface_token" class="mt-1 w-full border-b border-paper-rule bg-transparent py-1 font-mono text-xs outline-none dark:border-night-rule">
      </label>
      <label class="text-sm">Context
        <input v-model.number="editing.max_context_length" type="number" class="mt-1 w-full border-b border-paper-rule bg-transparent py-1 outline-none dark:border-night-rule">
      </label>
      <label class="text-sm">Temperature
        <input v-model.number="editing.default_temperature" type="number" step="0.01" class="mt-1 w-full border-b border-paper-rule bg-transparent py-1 outline-none dark:border-night-rule">
      </label>
      <label class="text-sm">Max tokens
        <input v-model.number="editing.default_max_tokens" type="number" class="mt-1 w-full border-b border-paper-rule bg-transparent py-1 outline-none dark:border-night-rule">
      </label>
      <label class="text-sm">top_p
        <input v-model.number="editing.default_top_p" type="number" step="0.01" class="mt-1 w-full border-b border-paper-rule bg-transparent py-1 outline-none dark:border-night-rule">
      </label>
      <label class="text-sm">top_k
        <input v-model.number="editing.default_top_k" type="number" class="mt-1 w-full border-b border-paper-rule bg-transparent py-1 outline-none dark:border-night-rule">
      </label>
      <label class="text-sm">min_p
        <input v-model.number="editing.default_min_p" type="number" step="0.01" class="mt-1 w-full border-b border-paper-rule bg-transparent py-1 outline-none dark:border-night-rule">
      </label>
      <label class="text-sm">presence penalty
        <input v-model.number="editing.default_presence_penalty" type="number" step="0.01" class="mt-1 w-full border-b border-paper-rule bg-transparent py-1 outline-none dark:border-night-rule">
      </label>
      <label class="text-sm">repetition penalty
        <input v-model.number="editing.default_repetition_penalty" type="number" step="0.01" class="mt-1 w-full border-b border-paper-rule bg-transparent py-1 outline-none dark:border-night-rule">
      </label>
      <label class="flex items-center gap-2 text-sm"><input v-model="editing.is_active" type="checkbox"> Active</label>
      <label class="flex items-center gap-2 text-sm"><input v-model="editing.is_default" type="checkbox"> Default</label>
      <label class="flex items-center gap-2 text-sm"><input v-model="editing.alwayswarm" type="checkbox"> Always warm</label>
      <div class="sm:col-span-2 flex gap-4">
        <button type="submit" class="border border-oxide px-4 py-2 text-[0.7rem] uppercase tracking-ledger text-oxide" :disabled="saving">
          Save
        </button>
        <button type="button" class="text-[0.7rem] uppercase tracking-ledger" @click="editing = null">Cancel</button>
      </div>
    </form>
  </div>
</template>
