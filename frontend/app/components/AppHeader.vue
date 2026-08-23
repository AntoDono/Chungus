<script setup lang="ts">
const route = useRoute()
const { user, logout, isAdmin } = useAuth()
const colorMode = useColorMode()

const links = computed(() => {
  const base = [
    { to: '/', label: 'Index' },
    { to: '/docs', label: 'Docs' },
  ]
  if (user.value) base.push({ to: '/dashboard', label: 'Console' })
  else base.push({ to: '/login', label: 'Sign in' })
  return base
})

function toggleTheme() {
  colorMode.preference = colorMode.value === 'dark' ? 'light' : 'dark'
}
</script>

<template>
  <header class="border-b border-paper-rule dark:border-night-rule">
    <div class="mx-auto flex max-w-6xl items-center justify-between gap-4 px-6 py-4">
      <NuxtLink to="/" class="group flex items-baseline gap-3 no-underline">
        <span class="font-display text-2xl font-semibold tracking-tight text-paper-ink dark:text-night-ink">
          CHUNGUS
        </span>
        <span class="hidden text-[0.65rem] uppercase tracking-ledger text-paper-faint dark:text-night-faint sm:inline">
          Atelier console
        </span>
      </NuxtLink>
      <nav class="flex items-center gap-1 text-[0.8rem] uppercase tracking-wider">
        <NuxtLink
          v-for="link in links"
          :key="link.to"
          :to="link.to"
          class="px-2.5 py-1 text-paper-faint no-underline hover:text-oxide dark:text-night-faint"
          :class="{ 'text-oxide': route.path === link.to || (link.to !== '/' && route.path.startsWith(link.to)) }"
        >
          {{ link.label }}
        </NuxtLink>
        <button
          type="button"
          class="ml-2 px-2 py-1 text-paper-faint hover:text-oxide dark:text-night-faint"
          :aria-label="colorMode.value === 'dark' ? 'Switch to light' : 'Switch to dark'"
          @click="toggleTheme"
        >
          <Icon :name="colorMode.value === 'dark' ? 'ph:sun-dim' : 'ph:moon'" class="size-4" />
        </button>
        <button
          v-if="user"
          type="button"
          class="px-2 py-1 text-paper-faint hover:text-oxide dark:text-night-faint"
          @click="logout"
        >
          Sign out
        </button>
      </nav>
    </div>
    <div
      v-if="user && route.path.startsWith('/dashboard')"
      class="mx-auto flex max-w-6xl gap-4 overflow-x-auto px-6 pb-3 text-[0.72rem] uppercase tracking-wider text-paper-faint dark:text-night-faint"
    >
      <NuxtLink to="/dashboard" class="hover:text-oxide" :class="{ 'text-oxide': route.path === '/dashboard' }">Overview</NuxtLink>
      <template v-if="isAdmin">
        <NuxtLink to="/dashboard/models" class="hover:text-oxide" :class="{ 'text-oxide': route.path.startsWith('/dashboard/models') }">Models</NuxtLink>
        <NuxtLink to="/dashboard/keys" class="hover:text-oxide" :class="{ 'text-oxide': route.path.startsWith('/dashboard/keys') }">Keys</NuxtLink>
        <NuxtLink to="/dashboard/users" class="hover:text-oxide" :class="{ 'text-oxide': route.path.startsWith('/dashboard/users') }">Users</NuxtLink>
        <NuxtLink to="/dashboard/history" class="hover:text-oxide" :class="{ 'text-oxide': route.path.startsWith('/dashboard/history') }">History</NuxtLink>
      </template>
    </div>
  </header>
</template>
