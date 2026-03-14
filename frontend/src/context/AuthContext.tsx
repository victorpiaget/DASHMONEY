import { createContext, useContext, useEffect, useState, type ReactNode } from 'react'
import { login as apiLogin, logout as apiLogout, refreshAccessToken, setAccessToken } from '../lib/api'

interface AuthState {
  isAuthenticated: boolean
  isLoading: boolean
  login: (email: string, password: string) => Promise<void>
  logout: () => Promise<void>
}

const AuthContext = createContext<AuthState | null>(null)

export function AuthProvider({ children }: { children: ReactNode }) {
  const [isAuthenticated, setIsAuthenticated] = useState(false)
  const [isLoading, setIsLoading] = useState(true)
  // Refresh token gardé en mémoire pour le logout
  const [refreshToken, setRefreshToken] = useState<string | null>(null)

  // Au démarrage : tente un refresh silencieux via le cookie httpOnly
  useEffect(() => {
    refreshAccessToken()
      .then(() => setIsAuthenticated(true))
      .catch(() => setIsAuthenticated(false))
      .finally(() => setIsLoading(false))
  }, [])

  const login = async (email: string, password: string) => {
    const data = await apiLogin(email, password)
    setRefreshToken(data.refresh_token)
    setIsAuthenticated(true)
  }

  const logout = async () => {
    if (refreshToken) {
      await apiLogout(refreshToken).catch(() => {})
    } else {
      setAccessToken(null)
    }
    setRefreshToken(null)
    setIsAuthenticated(false)
  }

  return (
    <AuthContext.Provider value={{ isAuthenticated, isLoading, login, logout }}>
      {children}
    </AuthContext.Provider>
  )
}

export function useAuth(): AuthState {
  const ctx = useContext(AuthContext)
  if (!ctx) throw new Error('useAuth must be used within AuthProvider')
  return ctx
}
