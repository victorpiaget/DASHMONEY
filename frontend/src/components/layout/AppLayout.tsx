import { NavLink, Outlet, useNavigate, useLocation } from 'react-router-dom'
import { useAuth } from '../../context/AuthContext'
import { useProfile } from '../../context/ProfileContext'
import { useCurrency, SUPPORTED_CURRENCIES } from '../../context/CurrencyContext'
import { useTheme } from '../../context/ThemeContext'

const NAV_ITEMS = [
  { to: '/', label: 'Dashboard', icon: '◈' },
  { to: '/accounts', label: 'Comptes', icon: '◉' },
  { to: '/transactions', label: 'Transactions', icon: '⇌' },
  { to: '/transfers', label: 'Transferts', icon: '⇄' },
  { to: '/portfolios', label: 'Portefeuilles', icon: '◎' },
  { to: '/categories', label: 'Catégories', icon: '⊟' },
  { to: '/instruments', label: 'Actifs', icon: '◫' },
  { to: '/import', label: 'Import CSV', icon: '↑' },
]

export default function AppLayout() {
  const { logout } = useAuth()
  const { profileName, workspaceName, clearProfile } = useProfile()
  const { displayCurrency, setDisplayCurrency, isError } = useCurrency()
  const { theme, toggleTheme } = useTheme()
  const navigate = useNavigate()
  const location = useLocation()

  const handleSwitchProfile = () => {
    clearProfile()
    navigate('/select-workspace')
  }

  return (
    <div className="flex h-screen bg-gray-50 dark:bg-slate-900 transition-colors duration-300">

      {/* Sidebar */}
      <aside className="w-56 flex-shrink-0 flex flex-col bg-white dark:bg-slate-800 border-r border-gray-100 dark:border-slate-700 transition-colors duration-300">

        {/* Logo + contexte workspace/profil */}
        <div className="px-5 py-4 border-b border-gray-100 dark:border-slate-700">
          <div className="flex items-center justify-between">
            <span className="font-semibold text-gray-900 dark:text-slate-100 tracking-tight text-sm">DashMoney</span>
            <button
              onClick={toggleTheme}
              title={theme === 'dark' ? 'Passer en mode clair' : 'Passer en mode sombre'}
              className="w-7 h-7 flex items-center justify-center rounded-md text-gray-400 dark:text-slate-500 hover:text-gray-700 dark:hover:text-slate-300 hover:bg-gray-100 dark:hover:bg-slate-700 transition-colors text-sm"
            >
              {theme === 'dark' ? '☀' : '◑'}
            </button>
          </div>
          {(workspaceName || profileName) && (
            <div className="mt-2.5 flex items-center justify-between">
              <div className="min-w-0">
                <p className="text-[10px] text-gray-400 dark:text-slate-500 uppercase tracking-wider font-medium truncate">{workspaceName}</p>
                <p className="text-xs font-semibold text-gray-700 dark:text-slate-300 truncate mt-0.5">{profileName}</p>
              </div>
              <button
                onClick={handleSwitchProfile}
                title="Changer de profil"
                className="ml-2 text-[10px] text-gray-400 dark:text-slate-500 hover:text-gray-700 dark:hover:text-slate-300 transition-colors flex-shrink-0 border border-gray-200 dark:border-slate-600 rounded-md px-1.5 py-0.5 hover:border-gray-400 dark:hover:border-slate-400"
              >
                ⇄
              </button>
            </div>
          )}
        </div>

        {/* Navigation */}
        <nav className="flex-1 py-4 px-3 space-y-0.5">
          {NAV_ITEMS.map(({ to, label, icon }) => (
            <NavLink
              key={to}
              to={to}
              end={to === '/'}
              className={({ isActive }) =>
                `flex items-center gap-3 px-3 py-2 rounded-lg text-sm font-medium transition-all duration-150 ${
                  isActive
                    ? 'bg-gray-900 dark:bg-slate-600 text-white'
                    : 'text-gray-600 dark:text-slate-400 hover:bg-gray-50 dark:hover:bg-slate-700 hover:text-gray-900 dark:hover:text-slate-100'
                }`
              }
            >
              <span className="text-base leading-none">{icon}</span>
              {label}
            </NavLink>
          ))}
        </nav>

        {/* Sélecteur de devise */}
        <div className="px-3 pb-2 border-t border-gray-100 dark:border-slate-700 pt-3">
          <p className="text-[10px] font-medium text-gray-400 dark:text-slate-500 uppercase tracking-wider px-1 mb-1.5">
            Devise d'affichage
            {isError && <span className="ml-1 text-amber-500" title="Taux non disponibles">⚠</span>}
          </p>
          <select
            value={displayCurrency}
            onChange={(e) => setDisplayCurrency(e.target.value)}
            className="w-full px-2.5 py-1.5 rounded-lg border border-gray-200 dark:border-slate-600 text-xs text-gray-700 dark:text-slate-300 bg-white dark:bg-slate-700 focus:outline-none focus:ring-2 focus:ring-gray-900 dark:focus:ring-slate-400 focus:border-transparent transition"
          >
            {SUPPORTED_CURRENCIES.map((c) => (
              <option key={c.code} value={c.code}>
                {c.symbol} {c.code} — {c.label}
              </option>
            ))}
          </select>
        </div>

        {/* Logout */}
        <div className="p-3 border-t border-gray-100 dark:border-slate-700">
          <button
            onClick={logout}
            className="w-full flex items-center gap-3 px-3 py-2 rounded-lg text-sm font-medium text-gray-500 dark:text-slate-400 hover:bg-gray-50 dark:hover:bg-slate-700 hover:text-gray-900 dark:hover:text-slate-100 transition-colors active:scale-[0.98]"
          >
            <span className="text-base leading-none">→</span>
            Déconnexion
          </button>
        </div>
      </aside>

      {/* Contenu principal avec transition de page */}
      <main className="flex-1 overflow-auto">
        <div key={location.pathname} className="page-transition h-full">
          <Outlet />
        </div>
      </main>
    </div>
  )
}
