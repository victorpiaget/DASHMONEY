import { useState, useRef, type FormEvent, type DragEvent } from 'react'
import { Link, useParams } from 'react-router-dom'
import { usePortfolios, useTrades, useCreateTrade, usePatchTrade, useDeleteTrade, usePositions, useInstruments, useCreateInstrument, useImportBoursorama, useImportBinance } from '../hooks/usePortfolios'
import { useCurrency } from '../context/CurrencyContext'
import type { Trade, TradeSide, ImportBoursoramaResult } from '../lib/portfoliosApi'

// ── Constantes ─────────────────────────────────────────────────────────────────

const TYPE_LABELS: Record<string, string> = {
  PEA: 'PEA', CTO: 'CTO', CRYPTO_EXCHANGE: 'Crypto Exchange', WALLET: 'Wallet', OTHER: 'Autre',
}
const TYPE_COLORS: Record<string, string> = {
  PEA: 'bg-blue-50 text-blue-700',
  CTO: 'bg-violet-50 text-violet-700',
  CRYPTO_EXCHANGE: 'bg-orange-50 text-orange-700',
  WALLET: 'bg-yellow-50 text-yellow-700',
  OTHER: 'bg-gray-100 text-gray-600',
}
const SIDE_COLORS: Record<string, string> = {
  BUY: 'bg-emerald-50 text-emerald-700',
  SELL: 'bg-red-50 text-red-600',
}

function TradeSideBadge({ trade }: { trade: Trade }) {
  if (trade.trade_type === 'TRANSFER') {
    return (
      <span className="px-2 py-0.5 rounded text-[10px] font-semibold bg-blue-50 text-blue-600">
        {trade.side === 'BUY' ? '→ Reçu' : '→ Envoyé'}
      </span>
    )
  }
  return (
    <span className={`px-2 py-0.5 rounded text-[10px] font-semibold ${SIDE_COLORS[trade.side]}`}>
      {trade.side === 'BUY' ? 'Achat' : 'Vente'}
    </span>
  )
}
const KIND_LABELS = ['STOCK', 'ETF', 'CRYPTO', 'OTHER']
const CURRENCIES = ['EUR', 'USD', 'BTC', 'USDT', 'ETH']

type SortField = 'date' | 'instrument_symbol' | 'side' | 'quantity' | 'price' | 'fees'
type SortDir = 'asc' | 'desc'
type ModalMode = { type: 'create' } | { type: 'edit'; trade: Trade }

const today = () => new Date().toISOString().slice(0, 10)

// Affiche le nom de l'instrument si dispo, sinon le symbole
function instLabel(instruments: import('../lib/portfoliosApi').Instrument[], symbol: string): string {
  const inst = instruments.find((i) => i.symbol === symbol)
  return inst?.name || symbol
}

function formatNum(v: string, decimals = 2) {
  const n = parseFloat(v)
  if (isNaN(n)) return '—'
  return new Intl.NumberFormat('fr-FR', { minimumFractionDigits: 0, maximumFractionDigits: decimals }).format(n)
}

// ── Page ───────────────────────────────────────────────────────────────────────

export default function PortfolioDetailPage() {
  const { format } = useCurrency()
  const { id } = useParams<{ id: string }>()
  const { data: portfolios = [] } = usePortfolios()
  const portfolio = portfolios.find((p) => p.id === id)

  const { data: instruments = [] } = useInstruments()
  const createInstrument = useCreateInstrument()

  // Filtres + tri
  const [q, setQ] = useState('')
  const [sideFilter, setSideFilter] = useState<TradeSide | ''>('')
  const [symbolFilter, setSymbolFilter] = useState('')
  const [sortBy, setSortBy] = useState<SortField>('date')
  const [sortDir, setSortDir] = useState<SortDir>('desc')

  const tradeParams = {
    q: q || undefined,
    sides: sideFilter ? [sideFilter] : undefined,
    symbols: symbolFilter ? [symbolFilter] : undefined,
    sort_by: sortBy,
    sort_dir: sortDir,
  }

  const { data: trades = [], isLoading: tradesLoading } = useTrades(id ?? '', tradeParams)
  const { data: positions = [] } = usePositions(id ?? '')
  const createTrade = useCreateTrade(id ?? '')
  const patchTrade = usePatchTrade(id ?? '')
  const deleteTrade = useDeleteTrade(id ?? '')

  const [modal, setModal] = useState<ModalMode | null>(null)
  const [confirmDeleteId, setConfirmDeleteId] = useState<string | null>(null)

  // Import CSV
  const importBoursorama = useImportBoursorama(id ?? '')
  const importBinance = useImportBinance(id ?? '')
  const [showImport, setShowImport] = useState(false)
  const [importSource, setImportSource] = useState<'boursorama' | 'binance'>('boursorama')
  const [importFile, setImportFile] = useState<File | null>(null)
  const [importResult, setImportResult] = useState<ImportBoursoramaResult | null>(null)
  const [importError, setImportError] = useState('')
  const [isDragOver, setIsDragOver] = useState(false)
  const fileInputRef = useRef<HTMLInputElement>(null)

  const handleImportDrop = (e: DragEvent<HTMLDivElement>) => {
    e.preventDefault(); setIsDragOver(false)
    const f = e.dataTransfer.files[0]
    if (f) { setImportFile(f); setImportResult(null); setImportError('') }
  }

  const handleImportSubmit = async () => {
    if (!importFile) return
    setImportError('')
    setImportResult(null)
    try {
      const result = importSource === 'binance'
        ? await importBinance.mutateAsync(importFile)
        : await importBoursorama.mutateAsync(importFile)
      setImportResult(result)
      setImportFile(null)
    } catch (err: unknown) {
      const msg = (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail
      setImportError(msg ?? 'Erreur lors de l\'import')
    }
  }

  const closeImport = () => {
    setShowImport(false); setImportFile(null); setImportResult(null); setImportError(''); setIsDragOver(false)
  }

  // Form state trade
  const [tradeDate, setTradeDate] = useState(today())
  const [tradeSide, setTradeSide] = useState<TradeSide>('BUY')
  const [tradeSymbol, setTradeSymbol] = useState('')
  const [tradeQty, setTradeQty] = useState('')
  const [tradePrice, setTradePrice] = useState('')
  const [tradeFees, setTradeFees] = useState('0')
  const [tradeLabel, setTradeLabel] = useState('')
  const [tradeError, setTradeError] = useState('')

  // Form état nouvel instrument (intégré au modal)
  const [showNewInstrument, setShowNewInstrument] = useState(false)
  const [newInstSymbol, setNewInstSymbol] = useState('')
  const [newInstKind, setNewInstKind] = useState('STOCK')
  const [newInstCurrency, setNewInstCurrency] = useState(portfolio?.currency ?? 'EUR')

  const openCreate = () => {
    setTradeDate(today()); setTradeSide('BUY'); setTradeSymbol(''); setTradeQty('')
    setTradePrice(''); setTradeFees('0'); setTradeLabel(''); setTradeError('')
    setShowNewInstrument(false)
    setModal({ type: 'create' })
  }

  const openEdit = (t: Trade) => {
    setTradeDate(t.date); setTradeSide(t.side); setTradeSymbol(t.instrument_symbol)
    setTradeQty(t.quantity); setTradePrice(t.price); setTradeFees(t.fees)
    setTradeLabel(t.label ?? ''); setTradeError('')
    setShowNewInstrument(false)
    setModal({ type: 'edit', trade: t })
  }

  const handleSubmitTrade = async (e: FormEvent) => {
    e.preventDefault()
    if (!tradeSymbol.trim() || !tradeQty || !tradePrice) {
      setTradeError('Symbole, quantité et prix sont requis')
      return
    }
    try {
      const payload = {
        date: tradeDate, side: tradeSide, instrument_symbol: tradeSymbol.toUpperCase().trim(),
        quantity: tradeQty, price: tradePrice, fees: tradeFees || '0',
        label: tradeLabel || undefined,
      }
      if (modal?.type === 'create') {
        await createTrade.mutateAsync(payload)
      } else if (modal?.type === 'edit') {
        await patchTrade.mutateAsync({ tradeId: modal.trade.id, payload: { date: tradeDate, quantity: tradeQty, price: tradePrice, fees: tradeFees || '0', label: tradeLabel || undefined } })
      }
      setModal(null)
    } catch (err: unknown) {
      const msg = (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail
      setTradeError(msg ?? 'Erreur')
    }
  }

  const handleCreateInstrument = async (e: FormEvent) => {
    e.preventDefault()
    if (!newInstSymbol.trim()) return
    await createInstrument.mutateAsync({ symbol: newInstSymbol.toUpperCase().trim(), kind: newInstKind, currency: newInstCurrency })
    setTradeSymbol(newInstSymbol.toUpperCase().trim())
    setShowNewInstrument(false)
  }

  const handleSort = (col: SortField) => {
    if (sortBy === col) setSortDir((d) => (d === 'asc' ? 'desc' : 'asc'))
    else { setSortBy(col); setSortDir('asc') }
  }

  const sortIcon = (col: SortField) => sortBy === col ? (sortDir === 'asc' ? ' ↑' : ' ↓') : ''

  // Calcul du total d'un trade
  const tradeTotal = (t: Trade) => {
    const gross = parseFloat(t.quantity) * parseFloat(t.price)
    const fees = parseFloat(t.fees)
    return t.side === 'BUY' ? -(gross + fees) : gross - fees
  }

  // Symboles distincts dans les trades (pour le filtre)
  const symbols = [...new Set(trades.map((t) => t.instrument_symbol))].sort()

  return (
    <div className="p-8">
      {/* Header */}
      <div className="mb-6">
        <Link to="/portfolios" className="text-xs text-gray-400 hover:text-gray-700 transition-colors mb-4 inline-block">
          ← Portefeuilles
        </Link>
        <div className="flex items-start justify-between">
          <div>
            <div className="flex items-center gap-2 mb-1">
              <h1 className="text-2xl font-semibold text-gray-900">{portfolio?.name ?? '…'}</h1>
              {portfolio && (
                <span className={`text-[11px] font-semibold px-2 py-0.5 rounded-md ${TYPE_COLORS[portfolio.portfolio_type] ?? TYPE_COLORS.OTHER}`}>
                  {TYPE_LABELS[portfolio.portfolio_type] ?? portfolio.portfolio_type}
                </span>
              )}
            </div>
            <p className="text-sm text-gray-400">{portfolio?.currency} · {positions.length} position{positions.length !== 1 ? 's' : ''}</p>
          </div>
          <Link
            to={`/portfolios/${id}/analyse`}
            className="flex items-center gap-1.5 px-3 py-1.5 bg-gray-100 text-gray-600 text-xs font-medium rounded-lg hover:bg-gray-200 transition-colors"
          >
            Analyse →
          </Link>
        </div>
      </div>

      {/* Positions actuelles */}
      {positions.length > 0 && (
        <div className="bg-white rounded-xl border border-gray-100 shadow-sm mb-6">
          <div className="px-5 py-4 border-b border-gray-50">
            <h2 className="text-sm font-medium text-gray-900">Positions actuelles</h2>
          </div>
          <div className="px-5 py-3 flex flex-wrap gap-2">
            {positions.map((pos) => (
              <div key={pos.instrument_symbol} className="flex items-center gap-2 bg-gray-50 rounded-lg px-3 py-1.5">
                <span className="text-xs font-semibold text-gray-800">{instLabel(instruments, pos.instrument_symbol)}</span>
                <span className="text-xs text-gray-400 font-mono text-[10px]">{pos.instrument_symbol}</span>
                <span className="text-xs text-gray-500">{formatNum(pos.quantity, 6)}</span>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Trades */}
      <div>
        <div className="flex items-center justify-between mb-3">
          <h2 className="text-sm font-medium text-gray-900">
            Trades
            {trades.length > 0 && <span className="ml-2 text-xs font-normal text-gray-400">{trades.length}</span>}
          </h2>
          <div className="flex items-center gap-2">
            <button
              onClick={() => setShowImport(true)}
              className="flex items-center gap-1.5 px-3 py-1.5 bg-white border border-gray-200 text-gray-600 text-xs font-medium rounded-lg hover:bg-gray-50 transition-colors"
            >
              ↑ Importer CSV
            </button>
            <button
              onClick={openCreate}
              className="flex items-center gap-1.5 px-3 py-1.5 bg-gray-900 text-white text-xs font-medium rounded-lg hover:bg-gray-800 transition-colors"
            >
              <span className="text-sm leading-none">+</span>
              Nouveau trade
            </button>
          </div>
        </div>

        {/* Filtres */}
        <div className="flex flex-wrap gap-2 mb-4">
          <input
            value={q}
            onChange={(e) => setQ(e.target.value)}
            placeholder="Rechercher…"
            className="border border-gray-200 rounded-lg px-3 py-1.5 text-xs focus:outline-none focus:ring-1 focus:ring-gray-900 w-44"
          />
          <select
            value={sideFilter}
            onChange={(e) => setSideFilter(e.target.value as TradeSide | '')}
            className="border border-gray-200 rounded-lg px-3 py-1.5 text-xs focus:outline-none focus:ring-1 focus:ring-gray-900"
          >
            <option value="">Tous les sens</option>
            <option value="BUY">Achat</option>
            <option value="SELL">Vente</option>
          </select>
          {symbols.length > 0 && (
            <select
              value={symbolFilter}
              onChange={(e) => setSymbolFilter(e.target.value)}
              className="border border-gray-200 rounded-lg px-3 py-1.5 text-xs focus:outline-none focus:ring-1 focus:ring-gray-900"
            >
              <option value="">Tous les instruments</option>
              {symbols.map((s) => <option key={s} value={s}>{s}</option>)}
            </select>
          )}
        </div>

        {/* Table */}
        <div className="bg-white rounded-xl border border-gray-100 shadow-sm overflow-hidden">
          {tradesLoading ? (
            <div className="flex justify-center py-12">
              <div className="w-5 h-5 border-2 border-gray-200 border-t-gray-700 rounded-full animate-spin" />
            </div>
          ) : trades.length === 0 ? (
            <div className="flex flex-col items-center justify-center py-16 text-center">
              <p className="text-sm text-gray-400">Aucun trade</p>
              <p className="text-xs text-gray-300 mt-1">Commencez par enregistrer un achat</p>
            </div>
          ) : (
            <table className="w-full text-xs">
              <thead>
                <tr className="border-b border-gray-50">
                  {([
                    ['date', 'Date'],
                    ['side', 'Sens'],
                    ['instrument_symbol', 'Instrument'],
                    ['quantity', 'Quantité'],
                    ['price', 'Prix unit.'],
                    ['fees', 'Frais'],
                  ] as [SortField, string][]).map(([col, label]) => (
                    <th
                      key={col}
                      onClick={() => handleSort(col)}
                      className="px-4 py-3 text-left font-medium text-gray-400 cursor-pointer hover:text-gray-700 transition-colors select-none"
                    >
                      {label}{sortIcon(col)}
                    </th>
                  ))}
                  <th className="px-4 py-3 text-right font-medium text-gray-400">Total</th>
                  <th className="px-4 py-3 text-left font-medium text-gray-400">Libellé</th>
                  <th className="px-4 py-3" />
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-50">
                {trades.map((t) => {
                  const total = tradeTotal(t)
                  return (
                    <tr key={t.id} className="hover:bg-gray-50 group transition-colors">
                      <td className="px-4 py-3 text-gray-600 tabular-nums">
                        {new Date(t.date + 'T00:00:00').toLocaleDateString('fr-FR')}
                      </td>
                      <td className="px-4 py-3">
                        <TradeSideBadge trade={t} />
                      </td>
                      <td className="px-4 py-3">
                        <div className="font-semibold text-gray-900 leading-tight">{instLabel(instruments, t.instrument_symbol)}</div>
                        <div className="text-[10px] text-gray-400 font-mono">{t.instrument_symbol}</div>
                      </td>
                      <td className="px-4 py-3 text-gray-700 tabular-nums">{formatNum(t.quantity, 8)}</td>
                      <td className="px-4 py-3 text-gray-700 tabular-nums">{format(t.price, t.currency)}</td>
                      <td className="px-4 py-3 text-gray-500 tabular-nums">{format(t.fees, t.currency)}</td>
                      <td className={`px-4 py-3 text-right tabular-nums font-medium ${total < 0 ? 'text-red-600' : 'text-emerald-600'}`}>
                        {format(total.toString(), t.currency)}
                      </td>
                      <td className="px-4 py-3 text-gray-400 max-w-[160px] truncate">{t.label}</td>
                      <td className="px-4 py-3">
                        <div className="flex items-center gap-2 opacity-0 group-hover:opacity-100 transition-opacity justify-end">
                          <button onClick={() => openEdit(t)} className="text-gray-400 hover:text-gray-700 transition-colors text-xs">Modifier</button>
                          <button onClick={() => setConfirmDeleteId(t.id)} className="text-gray-300 hover:text-red-500 transition-colors text-xs">Suppr.</button>
                        </div>
                      </td>
                    </tr>
                  )
                })}
              </tbody>
            </table>
          )}
        </div>
      </div>

      {/* Modal trade */}
      {modal && (
        <div className="fixed inset-0 bg-black/20 backdrop-blur-sm z-50 flex items-center justify-center p-4">
          <div className="bg-white rounded-2xl shadow-2xl w-full max-w-lg max-h-[90vh] overflow-y-auto">
            <div className="px-6 py-5 border-b border-gray-100 flex items-center justify-between sticky top-0 bg-white">
              <h2 className="text-base font-semibold text-gray-900">
                {modal.type === 'create' ? 'Nouveau trade' : 'Modifier le trade'}
              </h2>
              <button onClick={() => setModal(null)} className="text-gray-400 hover:text-gray-600 text-lg leading-none">×</button>
            </div>

            <form onSubmit={handleSubmitTrade} className="px-6 py-5 space-y-4">
              {/* Sens */}
              <div>
                <label className="block text-xs font-medium text-gray-700 mb-1.5">Sens</label>
                <div className="flex gap-2">
                  {(['BUY', 'SELL'] as TradeSide[]).map((s) => (
                    <button
                      key={s}
                      type="button"
                      onClick={() => setTradeSide(s)}
                      className={`flex-1 py-2 rounded-lg text-xs font-semibold transition-colors ${
                        tradeSide === s
                          ? s === 'BUY' ? 'bg-emerald-600 text-white' : 'bg-red-600 text-white'
                          : 'bg-gray-100 text-gray-600 hover:bg-gray-200'
                      }`}
                    >
                      {s === 'BUY' ? 'Achat' : 'Vente'}
                    </button>
                  ))}
                </div>
              </div>

              {/* Instrument */}
              <div>
                <div className="flex items-center justify-between mb-1.5">
                  <label className="text-xs font-medium text-gray-700">Instrument</label>
                  {modal.type === 'create' && (
                    <button type="button" onClick={() => setShowNewInstrument((v) => !v)} className="text-[11px] text-gray-400 hover:text-gray-700 transition-colors">
                      {showNewInstrument ? '← Retour' : '+ Nouvel instrument'}
                    </button>
                  )}
                </div>

                {showNewInstrument ? (
                  <div className="bg-gray-50 rounded-xl p-4 space-y-3">
                    <p className="text-xs font-medium text-gray-600">Créer un instrument</p>
                    <div className="grid grid-cols-3 gap-2">
                      <div>
                        <label className="text-[10px] text-gray-500 mb-1 block">Symbole</label>
                        <input
                          value={newInstSymbol}
                          onChange={(e) => setNewInstSymbol(e.target.value.toUpperCase())}
                          placeholder="BTC, AAPL…"
                          className="w-full border border-gray-200 rounded-lg px-2 py-1.5 text-xs focus:outline-none focus:ring-1 focus:ring-gray-900"
                        />
                      </div>
                      <div>
                        <label className="text-[10px] text-gray-500 mb-1 block">Type</label>
                        <select value={newInstKind} onChange={(e) => setNewInstKind(e.target.value)} className="w-full border border-gray-200 rounded-lg px-2 py-1.5 text-xs focus:outline-none">
                          {KIND_LABELS.map((k) => <option key={k} value={k}>{k}</option>)}
                        </select>
                      </div>
                      <div>
                        <label className="text-[10px] text-gray-500 mb-1 block">Devise</label>
                        <select value={newInstCurrency} onChange={(e) => setNewInstCurrency(e.target.value)} className="w-full border border-gray-200 rounded-lg px-2 py-1.5 text-xs focus:outline-none">
                          {CURRENCIES.map((c) => <option key={c} value={c}>{c}</option>)}
                        </select>
                      </div>
                    </div>
                    <button
                      type="button"
                      onClick={handleCreateInstrument}
                      disabled={createInstrument.isPending}
                      className="w-full py-1.5 bg-gray-900 text-white text-xs font-medium rounded-lg hover:bg-gray-800 disabled:opacity-60 transition-colors"
                    >
                      {createInstrument.isPending ? 'Création…' : 'Créer et sélectionner'}
                    </button>
                  </div>
                ) : (
                  <div className="flex gap-2">
                    <select
                      value={tradeSymbol}
                      onChange={(e) => setTradeSymbol(e.target.value)}
                      disabled={modal.type === 'edit'}
                      className="flex-1 border border-gray-200 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-gray-900 disabled:bg-gray-50"
                    >
                      <option value="">— Sélectionner —</option>
                      {instruments.map((i) => (
                        <option key={i.symbol} value={i.symbol}>
                          {i.name || i.symbol} — {i.symbol} ({i.kind})
                        </option>
                      ))}
                    </select>
                  </div>
                )}
              </div>

              {/* Date */}
              <div>
                <label className="block text-xs font-medium text-gray-700 mb-1.5">Date</label>
                <input
                  type="date"
                  value={tradeDate}
                  onChange={(e) => setTradeDate(e.target.value)}
                  className="w-full border border-gray-200 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-gray-900"
                />
              </div>

              {/* Quantité + Prix + Frais */}
              <div className="grid grid-cols-3 gap-3">
                <div>
                  <label className="block text-xs font-medium text-gray-700 mb-1.5">Quantité</label>
                  <input
                    type="number"
                    step="any"
                    min="0"
                    value={tradeQty}
                    onChange={(e) => setTradeQty(e.target.value)}
                    placeholder="0"
                    className="w-full border border-gray-200 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-gray-900"
                  />
                </div>
                <div>
                  <label className="block text-xs font-medium text-gray-700 mb-1.5">Prix unit.</label>
                  <input
                    type="number"
                    step="any"
                    min="0"
                    value={tradePrice}
                    onChange={(e) => setTradePrice(e.target.value)}
                    placeholder="0.00"
                    className="w-full border border-gray-200 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-gray-900"
                  />
                </div>
                <div>
                  <label className="block text-xs font-medium text-gray-700 mb-1.5">Frais</label>
                  <input
                    type="number"
                    step="any"
                    min="0"
                    value={tradeFees}
                    onChange={(e) => setTradeFees(e.target.value)}
                    placeholder="0"
                    className="w-full border border-gray-200 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-gray-900"
                  />
                </div>
              </div>

              {/* Total calculé */}
              {tradeQty && tradePrice && (
                <div className="bg-gray-50 rounded-lg px-4 py-2.5 flex items-center justify-between">
                  <span className="text-xs text-gray-500">Total</span>
                  <span className={`text-sm font-semibold tabular-nums ${tradeSide === 'BUY' ? 'text-red-600' : 'text-emerald-600'}`}>
                    {(() => {
                      const gross = parseFloat(tradeQty) * parseFloat(tradePrice)
                      const fees = parseFloat(tradeFees || '0')
                      const total = tradeSide === 'BUY' ? -(gross + fees) : gross - fees
                      return format(total.toString(), portfolio?.currency ?? 'EUR')
                    })()}
                  </span>
                </div>
              )}

              {/* Libellé */}
              <div>
                <label className="block text-xs font-medium text-gray-700 mb-1.5">Libellé (optionnel)</label>
                <input
                  value={tradeLabel}
                  onChange={(e) => setTradeLabel(e.target.value)}
                  placeholder="Note libre…"
                  className="w-full border border-gray-200 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-gray-900"
                />
              </div>

              {tradeError && <p className="text-xs text-red-600">{tradeError}</p>}

              <div className="flex justify-end gap-2 pt-1">
                <button type="button" onClick={() => setModal(null)} className="px-4 py-2 text-sm text-gray-600 hover:text-gray-900 transition-colors">
                  Annuler
                </button>
                <button
                  type="submit"
                  disabled={createTrade.isPending || patchTrade.isPending}
                  className="px-4 py-2 bg-gray-900 text-white text-sm font-medium rounded-lg hover:bg-gray-800 disabled:opacity-60 transition-colors"
                >
                  {createTrade.isPending || patchTrade.isPending ? 'Enregistrement…' : modal.type === 'create' ? 'Enregistrer' : 'Mettre à jour'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Modal import CSV */}
      {showImport && (
        <div className="fixed inset-0 bg-black/20 backdrop-blur-sm z-50 flex items-center justify-center p-4">
          <div className="bg-white rounded-2xl shadow-2xl w-full max-w-md">
            <div className="px-6 py-5 border-b border-gray-100 flex items-center justify-between">
              <div>
                <h2 className="text-base font-semibold text-gray-900">Importer des trades</h2>
                <p className="text-xs text-gray-400 mt-0.5">Sélectionnez la source de votre export CSV</p>
              </div>
              <button onClick={closeImport} className="text-gray-400 hover:text-gray-600 text-lg leading-none">×</button>
            </div>

            <div className="px-6 py-5 space-y-4">
              {importResult ? (
                /* Résultats */
                <div className="space-y-3">
                  <div className="grid grid-cols-2 gap-3">
                    <div className="bg-emerald-50 rounded-xl px-4 py-3 text-center">
                      <p className="text-2xl font-bold text-emerald-700">{importResult.imported}</p>
                      <p className="text-xs text-emerald-600 mt-0.5">trade{importResult.imported !== 1 ? 's' : ''} importé{importResult.imported !== 1 ? 's' : ''}</p>
                    </div>
                    <div className="bg-gray-50 rounded-xl px-4 py-3 text-center">
                      <p className="text-2xl font-bold text-gray-600">{importResult.skipped_duplicates + importResult.skipped_csv_duplicates}</p>
                      <p className="text-xs text-gray-500 mt-0.5">doublon{(importResult.skipped_duplicates + importResult.skipped_csv_duplicates) !== 1 ? 's' : ''} ignoré{(importResult.skipped_duplicates + importResult.skipped_csv_duplicates) !== 1 ? 's' : ''}</p>
                    </div>
                  </div>

                  {importResult.created_instruments.length > 0 && (
                    <div className="bg-blue-50 rounded-xl px-4 py-3">
                      <p className="text-xs font-medium text-blue-700 mb-1.5">Instruments créés automatiquement</p>
                      <div className="flex flex-wrap gap-1.5">
                        {importResult.created_instruments.map((s) => (
                          <span key={s} className="text-[11px] font-mono bg-blue-100 text-blue-800 px-2 py-0.5 rounded">{s}</span>
                        ))}
                      </div>
                      <p className="text-[10px] text-blue-500 mt-1.5">Type détecté automatiquement — vérifiez dans la page Actifs</p>
                    </div>
                  )}

                  {importResult.note && (
                    <div className="bg-amber-50 rounded-xl px-4 py-3">
                      <p className="text-xs text-amber-700">⚠ {importResult.note}</p>
                    </div>
                  )}

                  {importResult.errors_count > 0 && (
                    <div className="bg-red-50 rounded-xl px-4 py-3">
                      <p className="text-xs font-medium text-red-700 mb-1.5">{importResult.errors_count} erreur{importResult.errors_count !== 1 ? 's' : ''}</p>
                      <ul className="space-y-0.5">
                        {importResult.errors_preview.map((e, i) => (
                          <li key={i} className="text-[10px] text-red-600 font-mono">{e}</li>
                        ))}
                      </ul>
                    </div>
                  )}

                  <button onClick={closeImport} className="w-full py-2.5 bg-gray-900 text-white text-sm font-medium rounded-lg hover:bg-gray-800 transition-colors">
                    Fermer
                  </button>
                </div>
              ) : (
                /* Zone de dépôt */
                <>
                  {/* Sélecteur de source */}
                  <div className="flex gap-2">
                    {([
                      { key: 'boursorama', label: 'Boursorama', desc: 'Avis d\'opérés PEA/CTO' },
                      { key: 'binance', label: 'Binance', desc: 'Trade history CSV' },
                    ] as const).map(({ key, label, desc }) => (
                      <button
                        key={key}
                        onClick={() => { setImportSource(key); setImportFile(null); setImportError('') }}
                        className={`flex-1 px-3 py-2.5 rounded-xl border text-left transition-colors ${
                          importSource === key
                            ? 'border-gray-900 bg-gray-900 text-white'
                            : 'border-gray-200 text-gray-700 hover:border-gray-300'
                        }`}
                      >
                        <div className="text-xs font-semibold">{label}</div>
                        <div className={`text-[10px] mt-0.5 ${importSource === key ? 'text-gray-300' : 'text-gray-400'}`}>{desc}</div>
                      </button>
                    ))}
                  </div>

                  <div
                    onDragOver={(e) => { e.preventDefault(); setIsDragOver(true) }}
                    onDragLeave={() => setIsDragOver(false)}
                    onDrop={handleImportDrop}
                    onClick={() => fileInputRef.current?.click()}
                    className={`border-2 border-dashed rounded-xl px-6 py-10 text-center cursor-pointer transition-colors ${
                      isDragOver ? 'border-gray-400 bg-gray-50' : importFile ? 'border-emerald-400 bg-emerald-50' : 'border-gray-200 hover:border-gray-300'
                    }`}
                  >
                    <input
                      ref={fileInputRef}
                      type="file"
                      accept=".csv,.txt"
                      className="hidden"
                      onChange={(e) => {
                        const f = e.target.files?.[0]
                        if (f) { setImportFile(f); setImportResult(null); setImportError('') }
                      }}
                    />
                    {importFile ? (
                      <>
                        <p className="text-sm font-medium text-emerald-700">{importFile.name}</p>
                        <p className="text-xs text-emerald-500 mt-1">{(importFile.size / 1024).toFixed(1)} Ko — cliquez pour changer</p>
                      </>
                    ) : (
                      <>
                        <p className="text-sm text-gray-500">Glissez le CSV ici ou cliquez pour parcourir</p>
                        <p className="text-xs text-gray-400 mt-1">
                          {importSource === 'binance'
                            ? 'Export « Trade History » depuis Binance → Orders'
                            : 'Fichier « Avis d\'opérés » exporté depuis Boursorama'}
                        </p>
                      </>
                    )}
                  </div>

                  {importError && <p className="text-xs text-red-600">{importError}</p>}

                  <div className="flex justify-end gap-2">
                    <button type="button" onClick={closeImport} className="px-4 py-2 text-sm text-gray-600 hover:text-gray-900 transition-colors">
                      Annuler
                    </button>
                    <button
                      onClick={handleImportSubmit}
                      disabled={!importFile || importBoursorama.isPending}
                      className="px-4 py-2 bg-gray-900 text-white text-sm font-medium rounded-lg hover:bg-gray-800 disabled:opacity-50 transition-colors"
                    >
                      {importBoursorama.isPending ? 'Import en cours…' : 'Importer'}
                    </button>
                  </div>
                </>
              )}
            </div>
          </div>
        </div>
      )}

      {/* Confirm delete trade */}
      {confirmDeleteId && (
        <div className="fixed inset-0 bg-black/20 backdrop-blur-sm z-50 flex items-center justify-center p-4">
          <div className="bg-white rounded-2xl shadow-2xl w-full max-w-sm p-6">
            <p className="text-sm font-medium text-gray-900 mb-2">Supprimer ce trade ?</p>
            <p className="text-xs text-gray-500 mb-5">La transaction de trésorerie associée sera également supprimée.</p>
            <div className="flex justify-end gap-2">
              <button onClick={() => setConfirmDeleteId(null)} className="px-4 py-2 text-sm text-gray-600 hover:text-gray-900 transition-colors">Annuler</button>
              <button
                onClick={async () => { await deleteTrade.mutateAsync(confirmDeleteId); setConfirmDeleteId(null) }}
                disabled={deleteTrade.isPending}
                className="px-4 py-2 bg-red-600 text-white text-sm font-medium rounded-lg hover:bg-red-700 disabled:opacity-60 transition-colors"
              >
                {deleteTrade.isPending ? 'Suppression…' : 'Supprimer'}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
