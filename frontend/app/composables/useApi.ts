type HeaderMap = Record<string, string>

function cookieValue(name: string): string | null {
  if (!import.meta.client) return null
  const parts = document.cookie.split(';')
  for (const part of parts) {
    const [k, ...rest] = part.trim().split('=')
    if (k === name) return decodeURIComponent(rest.join('='))
  }
  return null
}

export function unwrapList<T>(payload: unknown, keys: string[]): T[] {
  if (Array.isArray(payload)) return payload as T[]
  if (payload && typeof payload === 'object') {
    const record = payload as Record<string, unknown>
    for (const key of keys) {
      const value = record[key]
      if (Array.isArray(value)) return value as T[]
    }
  }
  return []
}

export function unwrapUser(payload: unknown) {
  if (payload && typeof payload === 'object' && 'user' in payload) {
    return (payload as { user: unknown }).user
  }
  return payload
}

export async function readCsrfToken(): Promise<string> {
  const fromCookie = cookieValue('csrftoken')
  if (fromCookie) return fromCookie
  try {
    const data = await $fetch<{ csrfToken?: string; csrf_token?: string }>('/internal/auth/csrf', {
      credentials: 'include',
    })
    return data.csrfToken || data.csrf_token || cookieValue('csrftoken') || ''
  } catch {
    return cookieValue('csrftoken') || ''
  }
}

export async function api<T>(path: string, opts: Record<string, unknown> = {}): Promise<T> {
  const method = String(opts.method || 'GET').toUpperCase()
  const headers: HeaderMap = { ...((opts.headers as HeaderMap | undefined) || {}) }
  if (method !== 'GET' && method !== 'HEAD') {
    const token = await readCsrfToken()
    if (token) headers['X-CSRFToken'] = token
  }
  return await $fetch<T>(path, {
    credentials: 'include',
    ...opts,
    headers,
  } as Record<string, unknown>)
}
