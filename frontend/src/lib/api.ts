import axios from 'axios'

const BASE_URL = '/api'

export const api = axios.create({
  baseURL: BASE_URL,
  withCredentials: true, // envoie le cookie httpOnly refresh_token automatiquement
  paramsSerializer: (params) => {
    const sp = new URLSearchParams()
    for (const [key, value] of Object.entries(params)) {
      if (value === undefined || value === null) continue
      if (Array.isArray(value)) {
        for (const v of value) sp.append(key, String(v))
      } else {
        sp.append(key, String(value))
      }
    }
    return sp.toString()
  },
})

// Access token stocké en mémoire (jamais dans localStorage)
let _accessToken: string | null = null

export function setAccessToken(token: string | null) {
  _accessToken = token
}

export function getAccessToken(): string | null {
  return _accessToken
}

// Injecte l'access token dans chaque requête
api.interceptors.request.use((config) => {
  if (_accessToken) {
    config.headers.Authorization = `Bearer ${_accessToken}`
  }
  return config
})

// Sur 401, tente un refresh silencieux (une seule fois)
let _refreshPromise: Promise<string> | null = null

api.interceptors.response.use(
  (res) => res,
  async (error) => {
    const original = error.config
    if (error.response?.status === 401 && !original._retry) {
      original._retry = true
      try {
        if (!_refreshPromise) {
          _refreshPromise = refreshAccessToken().finally(() => {
            _refreshPromise = null
          })
        }
        const newToken = await _refreshPromise
        original.headers.Authorization = `Bearer ${newToken}`
        return api(original)
      } catch {
        setAccessToken(null)
        window.location.href = '/login'
        return Promise.reject(error)
      }
    }
    return Promise.reject(error)
  }
)

export async function refreshAccessToken(): Promise<string> {
  // Le cookie refresh_token est envoyé automatiquement (withCredentials)
  const res = await axios.post(`${BASE_URL}/auth/refresh`, null, {
    withCredentials: true,
  })
  const token = res.data.access_token
  setAccessToken(token)
  return token
}

export async function login(email: string, password: string): Promise<{ access_token: string; refresh_token: string }> {
  const res = await axios.post(`${BASE_URL}/auth/login`, { email, password }, { withCredentials: true })
  setAccessToken(res.data.access_token)
  return res.data
}

export async function logout(refreshToken: string): Promise<void> {
  await api.post('/auth/logout', { refresh_token: refreshToken })
  setAccessToken(null)
}
