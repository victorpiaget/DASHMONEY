import { useState, type FormEvent } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { usePortfolios, useCreatePortfolio, useDeletePortfolio } from '../hooks/usePortfolios'
import type { PortfolioType } from '../lib/portfoliosApi'

// ── Constantes ─────────────────────────────────────────────────────────────────

const TYPE_LABELS: Record<string, string> = {
  PEA: 'PEA',
  CTO: 'CTO',
  CRYPTO_EXCHANGE: 'Crypto Exchange',
  WALLET: 'Wallet',
  OTHER: 'Autre',
}

const TYPE_COLORS: Record<string, string> = {
  PEA: 'bg-blue-50 text-blue-700',
  CTO: 'bg-violet-50 text-violet-700',
  CRYPTO_EXCHANGE: 'bg-orange-50 text-orange-700',
  WALLET: 'bg-yellow-50 text-yellow-700',
  OTHER: 'bg-gray-100 text-gray-600',
}

const CURRENCIES = ['EUR', 'USD', 'BTC', 'USDT']
const PORTFOLIO_TYPES: PortfolioType[] = ['PEA', 'CTO', 'CRYPTO_EXCHANGE', 'WALLET', 'OTHER']

const today = () => new Date().toISOString().slice(0, 10)

// ── Page ───────────────────────────────────────────────────────────────────────

export default function PortfoliosPage() {
  const navigate = useNavigate()
  const { data: portfolios = [], isLoading } = usePortfolios()
  const createPortfolio = useCreatePortfolio()
  const deletePortfolio = useDeletePortfolio()

  const [showModal, setShowModal] = useState(false)
  const [confirmDelete, setConfirmDelete] = useState<string | null>(null)

  // Form state
  const [name, setName] = useState('')
  const [currency, setCurrency] = useState('EUR')
  const [portfolioType, setPortfolioType] = useState<PortfolioType>('CTO')
  const [openedOn, setOpenedOn] = useState(today)
  const [formError, setFormError] = useState('')

  const resetForm = () => {
    setName('')
    setCurrency('EUR')
    setPortfolioType('CTO')
    setOpenedOn(today())
    setFormError('')
  }

  const handleCreate = async (e: FormEvent) => {
    e.preventDefault()
    if (!name.trim()) { setFormError('Le nom est requis'); return }
    try {
      await createPortfolio.mutateAsync({ name: name.trim(), currency, portfolio_type: portfolioType, opened_on: openedOn })
      setShowModal(false)
      resetForm()
    } catch {
      setFormError('Erreur lors de la création')
    }
  }

  const handleDelete = async (id: string) => {
    await deletePortfolio.mutateAsync(id)
    setConfirmDelete(null)
  }

  return (
    <div className="p-8">
      {/* Header */}
      <div className="flex items-center justify-between mb-8">
        <div>
          <h1 className="text-xl font-semibold text-gray-900">Portefeuilles</h1>
          <p className="text-sm text-gray-500 mt-1">Actions, ETF, Crypto</p>
        </div>
        <div className="flex items-center gap-3">
          <button
            onClick={() => navigate('/portfolios/compare')}
            className="flex items-center gap-2 px-4 py-2 border border-gray-200 text-gray-700 text-sm font-medium rounded-xl hover:shadow-sm transition-all active:scale-[0.98]"
          >
            <span className="text-base leading-none">⊞</span>
            Vue comparée
          </button>
          <button
            onClick={() => setShowModal(true)}
            className="flex items-center gap-2 px-4 py-2 bg-gray-900 text-white text-sm font-medium rounded-xl hover:bg-gray-800 transition-all active:scale-[0.98]"
          >
            <span className="text-base leading-none">+</span>
            Nouveau portefeuille
          </button>
        </div>
      </div>

      {/* Liste */}
      {isLoading ? (
        <div className="flex justify-center py-16">
          <div className="w-6 h-6 border-2 border-gray-200 border-t-gray-700 rounded-full animate-spin" />
        </div>
      ) : portfolios.length === 0 ? (
        <div className="flex flex-col items-center justify-center py-24 text-center">
          <p className="text-4xl mb-4">◎</p>
          <p className="text-sm font-medium text-gray-700">Aucun portefeuille</p>
          <p className="text-sm text-gray-500 mt-1">Créez votre premier portefeuille pour suivre vos actifs</p>
        </div>
      ) : (
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-5">
          {portfolios.map((p) => (
            <div key={p.id} className="group bg-white rounded-xl border border-gray-100 hover:shadow-md transition-all">
              <Link to={`/portfolios/${p.id}`} className="block p-6">
                <div className="flex items-start justify-between mb-4">
                  <span className={`text-[11px] font-semibold px-2.5 py-1 rounded-md ${TYPE_COLORS[p.portfolio_type] ?? TYPE_COLORS.OTHER}`}>
                    {TYPE_LABELS[p.portfolio_type] ?? p.portfolio_type}
                  </span>
                  <span className="text-xs text-gray-500 font-semibold">{p.currency}</span>
                </div>
                <p className="text-base font-semibold text-gray-900 mb-1.5">{p.name}</p>
                <p className="text-xs text-gray-500">Ouvert le {new Date(p.opened_on + 'T00:00:00').toLocaleDateString('fr-FR')}</p>
              </Link>

              <div className="px-6 pb-5 flex items-center justify-between border-t border-gray-100 pt-4">
                <Link
                  to={`/portfolios/${p.id}/analyse`}
                  className="text-xs font-medium text-gray-600 hover:text-gray-900 transition-colors"
                >
                  Analyse →
                </Link>
                <button
                  onClick={(e) => { e.preventDefault(); setConfirmDelete(p.id) }}
                  className="text-xs font-medium text-gray-400 hover:text-red-500 transition-colors opacity-0 group-hover:opacity-100"
                >
                  Supprimer
                </button>
              </div>
            </div>
          ))}
        </div>
      )}

      {/* Modal création */}
      {showModal && (
        <div className="fixed inset-0 bg-black/20 backdrop-blur-sm z-50 flex items-center justify-center p-4">
          <div className="bg-white rounded-2xl shadow-xl w-full max-w-md">
            <div className="px-6 py-5 border-b border-gray-100 flex items-center justify-between">
              <h2 className="text-base font-semibold text-gray-900">Nouveau portefeuille</h2>
              <button onClick={() => { setShowModal(false); resetForm() }} className="text-gray-400 hover:text-gray-600 text-lg leading-none transition-colors">×</button>
            </div>
            <form onSubmit={handleCreate} className="px-6 py-5 space-y-4">
              <div>
                <label className="block text-xs font-semibold text-gray-700 mb-2">Nom</label>
                <input
                  value={name}
                  onChange={(e) => setName(e.target.value)}
                  placeholder="Mon PEA, Binance..."
                  className="w-full border border-gray-200 rounded-lg px-3 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-gray-900 focus:border-transparent transition-all"
                  autoFocus
                />
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block text-xs font-semibold text-gray-700 mb-2">Type</label>
                  <select
                    value={portfolioType}
                    onChange={(e) => setPortfolioType(e.target.value as PortfolioType)}
                    className="w-full border border-gray-200 rounded-lg px-3 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-gray-900 focus:border-transparent transition-all"
                  >
                    {PORTFOLIO_TYPES.map((t) => (
                      <option key={t} value={t}>{TYPE_LABELS[t]}</option>
                    ))}
                  </select>
                </div>
                <div>
                  <label className="block text-xs font-semibold text-gray-700 mb-2">Devise</label>
                  <select
                    value={currency}
                    onChange={(e) => setCurrency(e.target.value)}
                    className="w-full border border-gray-200 rounded-lg px-3 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-gray-900 focus:border-transparent transition-all"
                  >
                    {CURRENCIES.map((c) => <option key={c} value={c}>{c}</option>)}
                  </select>
                </div>
              </div>

              <div>
                <label className="block text-xs font-semibold text-gray-700 mb-2">Date d'ouverture</label>
                <input
                  type="date"
                  value={openedOn}
                  onChange={(e) => setOpenedOn(e.target.value)}
                  className="w-full border border-gray-200 rounded-lg px-3 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-gray-900 focus:border-transparent transition-all"
                />
              </div>

              {formError && <p className="text-xs font-medium text-red-600 mt-2">{formError}</p>}

              <div className="flex justify-end gap-3 pt-2">
                <button type="button" onClick={() => { setShowModal(false); resetForm() }} className="px-4 py-2.5 text-sm font-medium text-gray-700 hover:bg-gray-50 rounded-lg transition-colors">
                  Annuler
                </button>
                <button
                  type="submit"
                  disabled={createPortfolio.isPending}
                  className="px-4 py-2.5 bg-gray-900 text-white text-sm font-medium rounded-lg hover:bg-gray-800 disabled:opacity-60 transition-all active:scale-[0.98]"
                >
                  {createPortfolio.isPending ? 'Création…' : 'Créer'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Confirm delete */}
      {confirmDelete && (
        <div className="fixed inset-0 bg-black/20 backdrop-blur-sm z-50 flex items-center justify-center p-4">
          <div className="bg-white rounded-2xl shadow-xl w-full max-w-sm p-6">
            <p className="text-sm font-semibold text-gray-900 mb-2">Supprimer ce portefeuille ?</p>
            <p className="text-sm text-gray-600 mb-6">Tous les trades associés seront supprimés.</p>
            <div className="flex justify-end gap-3">
              <button onClick={() => setConfirmDelete(null)} className="px-4 py-2.5 text-sm font-medium text-gray-700 hover:bg-gray-50 rounded-lg transition-colors">
                Annuler
              </button>
              <button
                onClick={() => handleDelete(confirmDelete)}
                disabled={deletePortfolio.isPending}
                className="px-4 py-2.5 bg-red-600 text-white text-sm font-medium rounded-lg hover:bg-red-700 disabled:opacity-60 transition-all active:scale-[0.98]"
              >
                {deletePortfolio.isPending ? 'Suppression…' : 'Supprimer'}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
