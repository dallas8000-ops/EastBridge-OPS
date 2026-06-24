import { createContext, useCallback, useContext, useEffect, useMemo, useState, type ReactNode } from 'react'
import { API_BASE } from './api'

const TOKEN_KEY = 'eastbridge_access'
const ORG_KEY = 'eastbridge_org'

interface AuthUser {
  id: number
  username: string
  email: string
  memberships: Array<{
    id: number
    role: string
    organization: { id: number; name: string; slug: string; origin_country: string }
  }>
}

interface AuthContextValue {
  user: AuthUser | null
  token: string | null
  organizationId: number | null
  login: (username: string, password: string) => Promise<void>
  logout: () => void
  setOrganizationId: (id: number) => void
  authHeaders: () => Record<string, string>
}

const AuthContext = createContext<AuthContextValue | null>(null)

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<AuthUser | null>(null)
  const [token, setToken] = useState<string | null>(() => localStorage.getItem(TOKEN_KEY))
  const [organizationId, setOrganizationIdState] = useState<number | null>(() => {
    const stored = localStorage.getItem(ORG_KEY)
    return stored ? Number(stored) : null
  })

  const apiBase = API_BASE

  const authHeaders = useCallback(() => {
    const headers: Record<string, string> = { 'Content-Type': 'application/json' }
    if (token) headers.Authorization = `Bearer ${token}`
    if (organizationId) headers['X-Organization-ID'] = String(organizationId)
    return headers
  }, [token, organizationId])

  const setOrganizationId = useCallback((id: number) => {
    setOrganizationIdState(id)
    localStorage.setItem(ORG_KEY, String(id))
  }, [])

  const logout = useCallback(() => {
    setUser(null)
    setToken(null)
    localStorage.removeItem(TOKEN_KEY)
    localStorage.removeItem(ORG_KEY)
  }, [])

  const login = useCallback(async (username: string, password: string) => {
    const res = await fetch(`${apiBase}/auth/login/`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ username, password }),
    })
    if (!res.ok) throw new Error('Invalid credentials')
    const data = await res.json()
    setToken(data.access)
    localStorage.setItem(TOKEN_KEY, data.access)

    const meRes = await fetch(`${apiBase}/auth/me/`, {
      headers: { Authorization: `Bearer ${data.access}` },
    })
    if (meRes.ok) {
      const me = await meRes.json()
      setUser(me)
      if (me.memberships?.[0]?.organization?.id) {
        setOrganizationId(me.memberships[0].organization.id)
      }
    }
  }, [apiBase, setOrganizationId])

  useEffect(() => {
    if (!token) return
    fetch(`${apiBase}/auth/me/`, { headers: { Authorization: `Bearer ${token}` } })
      .then((r) => (r.ok ? r.json() : null))
      .then((me) => {
        if (me) {
          setUser(me)
          if (!organizationId && me.memberships?.[0]?.organization?.id) {
            setOrganizationId(me.memberships[0].organization.id)
          }
        } else {
          logout()
        }
      })
      .catch(() => logout())
  }, [token, apiBase, organizationId, logout, setOrganizationId])

  const value = useMemo(
    () => ({ user, token, organizationId, login, logout, setOrganizationId, authHeaders }),
    [user, token, organizationId, login, logout, setOrganizationId, authHeaders],
  )

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>
}

export function useAuth() {
  const ctx = useContext(AuthContext)
  if (!ctx) throw new Error('useAuth must be used within AuthProvider')
  return ctx
}
