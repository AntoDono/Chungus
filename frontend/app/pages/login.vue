<script setup lang="ts">
const { user, login } = useAuth()
const username = ref('')
const password = ref('')
const error = ref('')
const pending = ref(false)

onMounted(() => {
  if (user.value) navigateTo('/dashboard')
})

async function onSubmit() {
  error.value = ''
  pending.value = true
  try {
    await login(username.value, password.value)
    await navigateTo('/dashboard')
  } catch (err: unknown) {
    const e = err as { data?: { error?: string; detail?: string }; statusCode?: number }
    error.value = e?.data?.error || e?.data?.detail || 'Credentials refused.'
  } finally {
    pending.value = false
  }
}
</script>

<template>
  <div class="mx-auto max-w-md stagger">
    <p class="text-[0.7rem] uppercase tracking-ledger text-paper-faint">Session</p>
    <h1 class="mt-2 font-display text-4xl">Sign the ledger</h1>
    <p class="mt-3 text-sm text-paper-faint dark:text-night-faint">
      Django session cookie, same origin. CSRF is fetched before the post.
    </p>
    <form class="mt-8 space-y-4" @submit.prevent="onSubmit">
      <label class="block">
        <span class="text-[0.65rem] uppercase tracking-ledger text-paper-faint">Username</span>
        <input
          v-model="username"
          class="mt-1 w-full border-0 border-b border-paper-rule bg-transparent py-2 outline-none focus:border-oxide dark:border-night-rule"
          autocomplete="username"
          required
        >
      </label>
      <label class="block">
        <span class="text-[0.65rem] uppercase tracking-ledger text-paper-faint">Password</span>
        <input
          v-model="password"
          type="password"
          class="mt-1 w-full border-0 border-b border-paper-rule bg-transparent py-2 outline-none focus:border-oxide dark:border-night-rule"
          autocomplete="current-password"
          required
        >
      </label>
      <p v-if="error" class="text-sm text-oxide">{{ error }}</p>
      <button
        type="submit"
        class="mt-4 border border-oxide px-5 py-2 text-xs uppercase tracking-ledger text-oxide hover:bg-oxide hover:text-paper disabled:opacity-40"
        :disabled="pending"
      >
        {{ pending ? 'Opening…' : 'Enter' }}
      </button>
    </form>
  </div>
</template>
