export interface User {
  sub: string
  id: string
  name: string | null
  email: string | null
  roles: string[]
}

// The session lives in the backend (opaque cookie): the browser only ever
// learns who the user is, through GET /api/me, once, then cached.
export function useUser() {
  const user = useState<User | null>('user', () => null)
  const loading = useState('user-loading', () => false)
  const loaded = useState('user-loaded', () => false)

  async function refresh(): Promise<User | null> {
    loading.value = true
    try {
      const response = await fetch('/api/me', { headers: { Accept: 'application/json' } })
      user.value = response.ok ? ((await response.json()) as User) : null
    } finally {
      loading.value = false
      loaded.value = true
    }
    return user.value
  }

  async function logout(): Promise<void> {
    const response = await fetch('/auth/logout', { method: 'POST' })
    const { redirect } = (await response.json()) as { redirect: string }
    user.value = null
    window.location.href = redirect
  }

  return { user, loading, loaded, refresh, logout }
}
