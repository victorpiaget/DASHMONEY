import { NavLink, Outlet, useNavigate, useLocation } from 'react-router-dom'
import { useAuth } from '../../context/AuthContext'
import { useProfile } from '../../context/ProfileContext'
import { useCurrency, SUPPORTED_CURRENCIES } from '../../context/CurrencyContext'
import { useTheme } from '../../context/ThemeContext'

// ── SVG Icons ─────────────────────────────────────────────────────────────────

function Icon({ d, ...props }: { d: string } & React.SVGProps<SVGSVGElement>) {
  return (
    <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.75" strokeLinecap="round" strokeLinejoin="round" {...props}>
      <path d={d} />
    </svg>
  )
}

const NAV_ITEMS = [
  { to: '/', label: 'Dashboard', icon: <Icon d="M3 9l9-7 9 7v11a2 2 0 01-2 2H5a2 2 0 01-2-2z M9 22V12h6v10" /> },
  { to: '/accounts', label: 'Comptes', icon: <Icon d="M2 5a2 2 0 012-2h16a2 2 0 012 2v14a2 2 0 01-2 2H4a2 2 0 01-2-2V5z M2 10h20" /> },
  { to: '/transactions', label: 'Transactions', icon: <Icon d="M7 16V4m0 0L3 8m4-4l4 4 M17 8v12m0 0l4-4m-4 4l-4-4" /> },
  { to: '/transfers', label: 'Transferts', icon: <Icon d="M5 12h14 M12 5l7 7-7 7" /> },
  { to: '/portfolios', label: 'Portefeuilles', icon: <Icon d="M12 2v20 M17 5H9.5a3.5 3.5 0 000 7h5a3.5 3.5 0 010 7H6" /> },
  { to: '/categories', label: 'Catégories', icon: <Icon d="M4 6h16M4 10h16M4 14h10M4 18h6" /> },
  { to: '/budget', label: 'Budget', icon: <Icon d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2 M9 5a2 2 0 002 2h2a2 2 0 002-2 M9 5a2 2 0 012-2h2a2 2 0 012 2 M9 14l2 2 4-4" /> },
  { to: '/instruments', label: 'Actifs', icon: <Icon d="M22 12h-4l-3 9L9 3l-3 9H2" /> },
  { to: '/import', label: 'Import CSV', icon: <Icon d="M21 15v4a2 2 0 01-2 2H5a2 2 0 01-2-2v-4 M17 8l-5-5-5 5 M12 3v12" /> },
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
    <div className="flex h-screen bg-gray-50">

      {/* Sidebar */}
      <aside className="w-[232px] flex-shrink-0 flex flex-col bg-white border-r border-gray-100 transition-colors duration-200">

        {/* Logo + workspace/profil */}
        <div className="px-5 pt-5 pb-4 border-b border-gray-100">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              <div className="w-7 h-7 rounded-lg bg-gray-900 flex items-center justify-center">
                <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="white" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                  <path d="M12 2L2 7l10 5 10-5-10-5z" />
                  <path d="M2 17l10 5 10-5" />
                  <path d="M2 12l10 5 10-5" />
                </svg>
              </div>
              <span className="font-semibold text-gray-900 tracking-tight text-[15px]">DashMoney</span>
            </div>
            <button
              onClick={toggleTheme}
              title={theme === 'dark' ? 'Mode clair' : 'Mode sombre'}
              className="w-7 h-7 flex items-center justify-center rounded-lg text-gray-400 hover:text-gray-700 hover:bg-gray-100 transition-colors"
            >
              {theme === 'dark' ? (
                <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                  <circle cx="12" cy="12" r="5" /><line x1="12" y1="1" x2="12" y2="3" /><line x1="12" y1="21" x2="12" y2="23" /><line x1="4.22" y1="4.22" x2="5.64" y2="5.64" /><line x1="18.36" y1="18.36" x2="19.78" y2="19.78" /><line x1="1" y1="12" x2="3" y2="12" /><line x1="21" y1="12" x2="23" y2="12" /><line x1="4.22" y1="19.78" x2="5.64" y2="18.36" /><line x1="18.36" y1="5.64" x2="19.78" y2="4.22" />
                </svg>
              ) : (
                <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                  <path d="M21 12.79A9 9 0 1111.21 3 7 7 0 0021 12.79z" />
                </svg>
              )}
            </button>
          </div>
          {(workspaceName || profileName) && (
            <div className="mt-3 flex items-center justify-between gap-2">
              <div className="min-w-0">
                <p className="text-[10px] text-gray-400 uppercase tracking-wider font-medium truncate">{workspaceName}</p>
                <p className="text-xs font-semibold text-gray-700 truncate mt-0.5">{profileName}</p>
              </div>
              <button
                onClick={handleSwitchProfile}
                title="Changer de profil"
                className="flex-shrink-0 w-6 h-6 flex items-center justify-center rounded-md text-gray-400 hover:text-gray-700 hover:bg-gray-100 transition-colors border border-gray-200 hover:border-gray-300"
              >
                <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                  <polyline points="16 3 21 3 21 8" /><line x1="4" y1="20" x2="21" y2="3" /><polyline points="21 16 21 21 16 21" /><line x1="15" y1="15" x2="21" y2="21" />
                </svg>
              </button>
            </div>
          )}
        </div>

        {/* Navigation */}
        <nav className="flex-1 py-3 px-3 space-y-0.5 overflow-y-auto">
          {NAV_ITEMS.map(({ to, label, icon }) => (
            <NavLink
              key={to}
              to={to}
              end={to === '/'}
              className={({ isActive }) =>
                `flex items-center gap-2.5 px-3 py-[9px] rounded-lg text-[13px] font-medium transition-all duration-150 ${
                  isActive
                    ? 'bg-gray-900 text-white shadow-sm'
                    : 'text-gray-500 hover:bg-gray-50 hover:text-gray-900'
                }`
              }
            >
              <span className="flex-shrink-0 w-[18px]">{icon}</span>
              {label}
            </NavLink>
          ))}
        </nav>

        {/* Sélecteur de devise */}
        <div className="px-4 pb-2 border-t border-gray-100 pt-3">
          <p className="text-[10px] font-medium text-gray-400 uppercase tracking-wider mb-1.5">
            Devise
            {isError && <span className="ml-1 text-amber-500" title="Taux non disponibles">!</span>}
          </p>
          <select
            value={displayCurrency}
            onChange={(e) => setDisplayCurrency(e.target.value)}
            className="w-full px-2.5 py-1.5 rounded-lg border border-gray-200 text-xs text-gray-600 bg-white focus:outline-none focus:ring-2 focus:ring-gray-900 focus:border-transparent transition cursor-pointer"
          >
            {SUPPORTED_CURRENCIES.map((c) => (
              <option key={c.code} value={c.code}>
                {c.symbol} {c.code} — {c.label}
              </option>
            ))}
          </select>
        </div>

        {/* Logout */}
        <div className="p-3 border-t border-gray-100">
          <button
            onClick={logout}
            className="w-full flex items-center gap-2.5 px-3 py-2 rounded-lg text-[13px] font-medium text-gray-400 hover:bg-gray-50 hover:text-gray-700 transition-colors"
          >
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.75" strokeLinecap="round" strokeLinejoin="round">
              <path d="M9 21H5a2 2 0 01-2-2V5a2 2 0 012-2h4" /><polyline points="16 17 21 12 16 7" /><line x1="21" y1="12" x2="9" y2="12" />
            </svg>
            Déconnexion
          </button>
        </div>
      </aside>

      {/* Contenu principal */}
      <main className="flex-1 overflow-auto">
        <div key={location.pathname} className="page-transition h-full">
          <Outlet />
        </div>
      </main>
    </div>
  )
}
