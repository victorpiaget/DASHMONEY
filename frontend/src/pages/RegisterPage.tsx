import { type FormEvent, useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { register } from '../lib/api'
import { useAuth } from '../context/AuthContext'
import { useProfile } from '../context/ProfileContext'
import { workspaceApi } from '../lib/workspaceApi'

export default function RegisterPage() {
  const { login } = useAuth()
  const { selectProfile } = useProfile()
  const navigate = useNavigate()

  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [confirm, setConfirm] = useState('')
  const [error, setError] = useState<string | null>(null)
  const [loading, setLoading] = useState(false)

  const passwordMismatch = confirm.length > 0 && password !== confirm
  const passwordTooShort = password.length > 0 && password.length < 8

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault()
    if (password !== confirm) {
      setError('Les mots de passe ne correspondent pas.')
      return
    }
    if (password.length < 8) {
      setError('Le mot de passe doit contenir au moins 8 caractères.')
      return
    }
    setError(null)
    setLoading(true)
    try {
      await register(email.trim().toLowerCase(), password)
      await login(email.trim().toLowerCase(), password)
      // Auto-sélection du workspace/profil si un seul existe
      try {
        const me = await workspaceApi.me()
        if (me.workspaces.length === 1 && me.workspaces[0].profiles.length === 1) {
          const ws = me.workspaces[0]
          const profile = ws.profiles[0]
          selectProfile(profile.id, profile.display_name, ws.name)
          localStorage.setItem('dashmoney_onboarding', 'true')
          navigate('/', { replace: true })
          return
        }
      } catch {
        // Fallback
      }
      navigate('/select-workspace', { replace: true })
    } catch (err: unknown) {
      const detail = (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail
      if (typeof detail === 'string') {
        setError(detail)
      } else {
        setError('Une erreur est survenue lors de la création du compte.')
      }
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="min-h-screen flex items-center justify-center bg-gray-50 px-4">
      <div className="w-full max-w-[380px]">
        {/* Logo */}
        <div className="text-center mb-8">
          <div className="w-10 h-10 mx-auto mb-4 rounded-xl bg-gray-900 flex items-center justify-center">
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="white" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
              <path d="M12 2L2 7l10 5 10-5-10-5z" />
              <path d="M2 17l10 5 10-5" />
              <path d="M2 12l10 5 10-5" />
            </svg>
          </div>
          <h1 className="text-xl font-semibold tracking-tight text-gray-900">Créer un compte</h1>
          <p className="mt-1 text-sm text-gray-400">Commencez à suivre votre patrimoine</p>
        </div>

        <div className="bg-white rounded-2xl shadow-sm border border-gray-100 p-7">
          <form onSubmit={handleSubmit} className="space-y-4">
            <div>
              <label htmlFor="email" className="block text-xs font-medium text-gray-500 mb-1.5">
                Email
              </label>
              <input
                id="email"
                type="email"
                autoComplete="email"
                required
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                className="w-full px-3.5 py-2.5 rounded-xl border border-gray-200 text-sm text-gray-900 placeholder-gray-300 focus:outline-none focus:ring-2 focus:ring-gray-900 focus:border-transparent transition"
                placeholder="vous@example.com"
              />
            </div>

            <div>
              <label htmlFor="password" className="block text-xs font-medium text-gray-500 mb-1.5">
                Mot de passe
                <span className="ml-1 text-[10px] font-normal text-gray-300">(8 car. min.)</span>
              </label>
              <input
                id="password"
                type="password"
                autoComplete="new-password"
                required
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                className={`w-full px-3.5 py-2.5 rounded-xl border text-sm text-gray-900 placeholder-gray-300 focus:outline-none focus:ring-2 focus:border-transparent transition ${
                  passwordTooShort
                    ? 'border-amber-300 focus:ring-amber-400'
                    : 'border-gray-200 focus:ring-gray-900'
                }`}
                placeholder="••••••••"
              />
              {passwordTooShort && (
                <p className="mt-1.5 text-[11px] text-amber-600">Trop court — 8 caractères minimum.</p>
              )}
            </div>

            <div>
              <label htmlFor="confirm" className="block text-xs font-medium text-gray-500 mb-1.5">
                Confirmer le mot de passe
              </label>
              <input
                id="confirm"
                type="password"
                autoComplete="new-password"
                required
                value={confirm}
                onChange={(e) => setConfirm(e.target.value)}
                className={`w-full px-3.5 py-2.5 rounded-xl border text-sm text-gray-900 placeholder-gray-300 focus:outline-none focus:ring-2 focus:border-transparent transition ${
                  passwordMismatch
                    ? 'border-red-300 focus:ring-red-400'
                    : 'border-gray-200 focus:ring-gray-900'
                }`}
                placeholder="••••••••"
              />
              {passwordMismatch && (
                <p className="mt-1.5 text-[11px] text-red-500">Les mots de passe ne correspondent pas.</p>
              )}
            </div>

            {error && (
              <p className="text-sm text-red-600 bg-red-50 rounded-xl px-3.5 py-2.5">{error}</p>
            )}

            <button
              type="submit"
              disabled={loading || passwordMismatch || passwordTooShort}
              className="w-full py-2.5 px-4 bg-gray-900 text-white text-sm font-medium rounded-xl hover:bg-gray-800 focus:outline-none focus:ring-2 focus:ring-gray-900 focus:ring-offset-2 disabled:opacity-50 disabled:cursor-not-allowed transition-all active:scale-[0.98]"
            >
              {loading ? 'Création du compte…' : 'Créer mon compte'}
            </button>
          </form>
        </div>

        <p className="text-center text-sm text-gray-400 mt-6">
          Déjà un compte ?{' '}
          <Link to="/login" className="font-medium text-gray-900 hover:underline underline-offset-2">
            Se connecter
          </Link>
        </p>
      </div>
    </div>
  )
}
