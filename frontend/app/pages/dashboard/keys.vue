<script setup lang="ts">
import type { AdminUser, ApiKeyRecord } from '~/types/api'

definePageMeta({ middleware: ['auth', 'admin'] })

const keys = ref<ApiKeyRecord[]>([])
const users = ref<AdminUser[]>([])
const error = ref('')
const createdSecret = ref('')
const form = ref({
  id: 0,
  name: '',
  description: '',
  is_active: true,
  rate_limit_per_minute: 60,
  rate_limit_per_hour: 1000,
  user_id: null as number | null,
})
const showForm = ref(false)
const loading = ref(true)

async function load() {
  if (!keys.value.length) loading.value = true
  try {
    const [keyPayload, userPayload] = await Promise.all([
      api('/internal/admin/keys'),
      api('/internal/admin/users'),
    ])
    keys.value = unwrapList<ApiKeyRecord>(keyPayload, ['keys', 'api_keys'])
    users.value = unwrapList<AdminUser>(userPayload, ['users'])
  } finally {
    loading.value = false
  }
}

function openCreate() {
  createdSecret.value = ''
  form.value = {
    id: 0,
    name: '',
    description: '',
    is_active: true,
    rate_limit_per_minute: 60,
    rate_limit_per_hour: 1000,
    user_id: null,
  }
  showForm.value = true
}

function openEdit(key: ApiKeyRecord) {
  createdSecret.value = ''
  form.value = {
    id: key.id,
    name: key.name,
    description: key.description,
    is_active: key.is_active,
    rate_limit_per_minute: key.rate_limit_per_minute,
    rate_limit_per_hour: key.rate_limit_per_hour,
    user_id: key.user_id ?? null,
  }
  showForm.value = true
}

async function save() {
  error.value = ''
  try {
    if (form.value.id) {
      await api(`/internal/admin/keys/${form.value.id}/update`, { method: 'POST', body: form.value })
    } else {
      const res = await api<{ key?: string; api_key?: { key?: string } }>('/internal/admin/keys', {
        method: 'POST',
        body: form.value,
      })
      createdSecret.value = res.key || res.api_key?.key || ''
    }
    showForm.value = Boolean(createdSecret.value)
    await load()
  } catch (err: unknown) {
    error.value = (err as { data?: { error?: string } }).data?.error || 'Save failed.'
  }
}

async function remove(id: number) {
  if (!confirm('Delete this key?')) return
  await api(`/internal/admin/keys/${id}/delete`, { method: 'POST' })
  await load()
}

onMounted(load)
</script>

<template>
  <div>
    <div class="mb-8 flex items-end justify-between">
      <div>
        <p class="text-[0.7rem] uppercase tracking-ledger text-paper-faint">Admin</p>
        <h1 class="font-display text-4xl">Keys</h1>
      </div>
      <button type="button" class="border border-oxide px-4 py-2 text-[0.7rem] uppercase tracking-ledger text-oxide" @click="openCreate">
        Issue key
      </button>
    </div>
    <p v-if="error" class="mb-4 text-oxide">{{ error }}</p>
    <LoadingBlock v-if="loading" label="Loading keys" height="8rem" />
    <p v-if="createdSecret" class="mb-4 hairline p-4 font-mono text-sm">
      Secret (shown once): {{ createdSecret }}
    </p>

    <div v-else class="hairline overflow-x-auto">
      <table class="min-w-full text-left text-sm">
        <thead class="text-[0.65rem] uppercase tracking-ledger text-paper-faint">
          <tr>
            <th class="px-3 py-2">Name</th>
            <th class="px-3 py-2">Owner</th>
            <th class="px-3 py-2">Preview</th>
            <th class="px-3 py-2">RPM / RPH</th>
            <th class="px-3 py-2" />
          </tr>
        </thead>
        <tbody>
          <tr v-for="k in keys" :key="k.id" class="border-t border-paper-rule dark:border-night-rule">
            <td class="px-3 py-2">{{ k.name }}</td>
            <td class="px-3 py-2">{{ k.username || k.user_id || '—' }}</td>
            <td class="px-3 py-2 font-mono text-xs">{{ k.key_preview || k.key }}</td>
            <td class="px-3 py-2 font-mono text-xs tabular">{{ k.rate_limit_per_minute }} / {{ k.rate_limit_per_hour }}</td>
            <td class="px-3 py-2 text-right text-[0.7rem] uppercase tracking-wider">
              <button type="button" class="mr-3" @click="openEdit(k)">Edit</button>
              <button type="button" class="text-oxide" @click="remove(k.id)">Delete</button>
            </td>
          </tr>
        </tbody>
      </table>
    </div>

    <form v-if="showForm" class="mt-8 grid gap-4 hairline p-5 sm:grid-cols-2" @submit.prevent="save">
      <h2 class="sm:col-span-2 font-display text-2xl">{{ form.id ? 'Amend key' : 'New key' }}</h2>
      <label class="text-sm">Name
        <input v-model="form.name" required class="mt-1 w-full border-b border-paper-rule bg-transparent py-1 outline-none dark:border-night-rule">
      </label>
      <label class="text-sm">Owner
        <select v-model.number="form.user_id" class="mt-1 w-full bg-transparent">
          <option :value="null">Unassigned</option>
          <option v-for="u in users" :key="u.id" :value="u.id">{{ u.username }}</option>
        </select>
      </label>
      <label class="sm:col-span-2 text-sm">Description
        <input v-model="form.description" class="mt-1 w-full border-b border-paper-rule bg-transparent py-1 outline-none dark:border-night-rule">
      </label>
      <label class="text-sm">RPM
        <input v-model.number="form.rate_limit_per_minute" type="number" class="mt-1 w-full border-b border-paper-rule bg-transparent py-1 outline-none dark:border-night-rule">
      </label>
      <label class="text-sm">RPH
        <input v-model.number="form.rate_limit_per_hour" type="number" class="mt-1 w-full border-b border-paper-rule bg-transparent py-1 outline-none dark:border-night-rule">
      </label>
      <label class="flex items-center gap-2 text-sm"><input v-model="form.is_active" type="checkbox"> Active</label>
      <div class="sm:col-span-2 flex gap-4">
        <button type="submit" class="border border-oxide px-4 py-2 text-[0.7rem] uppercase tracking-ledger text-oxide">Save</button>
        <button type="button" class="text-[0.7rem] uppercase tracking-ledger" @click="showForm = false">Cancel</button>
      </div>
    </form>
  </div>
</template>
