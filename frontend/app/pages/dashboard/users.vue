<script setup lang="ts">
import type { AdminUser, Role } from '~/types/api'

definePageMeta({ middleware: ['auth', 'admin'] })

const users = ref<AdminUser[]>([])
const error = ref('')
const minted = ref('')
const form = ref({ username: '', password: '', role: 'user' as Role })

async function load() {
  const payload = await api('/internal/admin/users')
  users.value = unwrapList<AdminUser>(payload, ['users'])
}

async function createUser() {
  error.value = ''
  minted.value = ''
  try {
    const res = await api<{ key?: string; api_key?: { key?: string } }>('/internal/admin/users', {
      method: 'POST',
      body: form.value,
    })
    minted.value = res.key || res.api_key?.key || ''
    form.value = { username: '', password: '', role: 'user' }
    await load()
  } catch (err: unknown) {
    error.value = (err as { data?: { error?: string } }).data?.error || 'Create failed.'
  }
}

async function setRole(user: AdminUser, role: Role) {
  await api(`/internal/admin/users/${user.id}/update`, { method: 'POST', body: { role } })
  await load()
}

async function deactivate(user: AdminUser) {
  await api(`/internal/admin/users/${user.id}/update`, {
    method: 'POST',
    body: { is_active: false },
  })
  await load()
}

onMounted(load)
</script>

<template>
  <div>
    <p class="text-[0.7rem] uppercase tracking-ledger text-paper-faint">Admin</p>
    <h1 class="mb-8 font-display text-4xl">Fellows</h1>
    <p v-if="error" class="mb-4 text-oxide">{{ error }}</p>
    <p v-if="minted" class="mb-4 hairline p-4 font-mono text-sm">Minted key (shown once): {{ minted }}</p>

    <form class="mb-10 grid gap-4 hairline p-5 sm:grid-cols-3" @submit.prevent="createUser">
      <label class="text-sm">Username
        <input v-model="form.username" required class="mt-1 w-full border-b border-paper-rule bg-transparent py-1 outline-none dark:border-night-rule">
      </label>
      <label class="text-sm">Password
        <input v-model="form.password" type="password" required class="mt-1 w-full border-b border-paper-rule bg-transparent py-1 outline-none dark:border-night-rule">
      </label>
      <label class="text-sm">Role
        <select v-model="form.role" class="mt-1 w-full bg-transparent">
          <option value="user">user</option>
          <option value="admin">admin</option>
        </select>
      </label>
      <button type="submit" class="border border-oxide px-4 py-2 text-[0.7rem] uppercase tracking-ledger text-oxide sm:col-span-3">
        Create fellow (auto-issues a key)
      </button>
    </form>

    <div class="hairline overflow-x-auto">
      <table class="min-w-full text-left text-sm">
        <thead class="text-[0.65rem] uppercase tracking-ledger text-paper-faint">
          <tr>
            <th class="px-3 py-2">Username</th>
            <th class="px-3 py-2">Role</th>
            <th class="px-3 py-2">Active</th>
            <th class="px-3 py-2" />
          </tr>
        </thead>
        <tbody>
          <tr v-for="u in users" :key="u.id" class="border-t border-paper-rule dark:border-night-rule">
            <td class="px-3 py-2">{{ u.username }}</td>
            <td class="px-3 py-2">
              <select :value="u.role" class="bg-transparent" @change="setRole(u, ($event.target as HTMLSelectElement).value as Role)">
                <option value="user">user</option>
                <option value="admin">admin</option>
              </select>
            </td>
            <td class="px-3 py-2">{{ u.is_active === false ? 'no' : 'yes' }}</td>
            <td class="px-3 py-2 text-right">
              <button type="button" class="text-[0.7rem] uppercase tracking-wider text-oxide" @click="deactivate(u)">
                Deactivate
              </button>
            </td>
          </tr>
        </tbody>
      </table>
    </div>
  </div>
</template>
