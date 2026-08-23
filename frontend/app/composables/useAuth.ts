import type { AuthUser } from '~/types/api'
import { api, readCsrfToken, unwrapUser } from './useApi'

export function useAuth() {
  const user = useState<AuthUser | null>('auth-user', () => null)
  const ready = useState('auth-ready', () => false)

  async function refresh() {
    try {
      const payload = await api<AuthUser | { user: AuthUser }>('/internal/auth/me')
      user.value = unwrapUser(payload) as AuthUser
    } catch {
      user.value = null
    } finally {
      ready.value = true
    }
  }

  async function login(username: string, password: string) {
    await readCsrfToken()
    const payload = await api<AuthUser | { user: AuthUser }>('/internal/auth/login', {
      method: 'POST',
      body: { username, password },
    })
    user.value = unwrapUser(payload) as AuthUser
    return user.value
  }

  async function logout() {
    try {
      await api('/internal/auth/logout', { method: 'POST' })
    } finally {
      user.value = null
      await navigateTo('/login')
    }
  }

  const isAdmin = computed(() => user.value?.role === 'admin')

  return { user, ready, isAdmin, refresh, login, logout }
}
