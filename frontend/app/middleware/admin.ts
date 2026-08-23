export default defineNuxtRouteMiddleware(async () => {
  const { user, refresh, isAdmin } = useAuth()
  if (!user.value) await refresh()
  if (!user.value) return navigateTo('/login')
  if (!isAdmin.value) return navigateTo('/dashboard')
})
