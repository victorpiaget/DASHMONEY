import { useState, useMemo, type FormEvent } from 'react'
import { Link, useParams } from 'react-router-dom'
import { useQueryClient } from '@tanstack/react-query'
import { usePortfolios, useTrades, usePositions, useSnapshots, useAddSnapshot, useInstruments, useLatestPrices, usePriceHistory } from '../hooks/usePortfolios'
import { pricesApi } from '../lib/portfoliosApi'
import { useCurrency } from '../context/CurrencyContext'
import { useTheme } from '../context/ThemeContext'
import PeriodPicker from '../components/PeriodPicker'
import { type PeriodSelection, resolveDates } from '../lib/period'
import type { PortfolioSnapshot, Instrument } from '../lib/portfoliosApi'

function instLabel(instruments: Instrument[], symbol: string): string {
  const inst = instruments.find((i) => i.symbol === symbol)
  return inst?.name || symbol
}

const TYPE_LABELS: Record<string, string> = {
  PEA: 'PEA', CTO: 'CTO', CRYPTO_EXCHANGE: 'Crypto Exchange', WALLET: 'Wallet', OTHER: 'Autre',
}
const TYPE_COLORS: Record<string, string> = {
  PEA: 'bg-blue-50 text-blue-700', CTO: 'bg-violet-50 text-violet-700',
  CRYPTO_EXCHANGE: 'bg-orange-50 text-orange-700', WALLET: 'bg-yellow-50 text-yellow-700',
  OTHER: 'bg-gray-100 text-gray-600',
}

// ── Snapshot Chart ─────────────────────────────────────────────────────────────

function SnapshotChart({ snapshots }: { snapshots: PortfolioSnapshot[] }) {
  const { format } = useCurrency()
  const { theme } = useTheme()
  const isDark = theme === 'dark'
  const lineColor = isDark ? '#e2e8f0' : '#111827'
  const gridColor = isDark ? '#334155' : '#f3f4f6'
  const [hovered, setHovered] = useState<number | null>(null)

  const sorted = useMemo(() => [...snapshots].sort((a, b) => a.date.localeCompare(b.date)), [snapshots])

  const W = 600, H = 320
  const pad = { top: 16, right: 12, bottom: 32, left: 68 }
  const innerW = W - pad.left - pad.right
  const innerH = H - pad.top - pad.bottom

  const values = sorted.map((s) => parseFloat(s.value))
  const minV = Math.min(...values)
  const maxV = Math.max(...values)
  const range = maxV - minV || 1

  const toX = (i: number) => pad.left + (sorted.length === 1 ? innerW / 2 : (i / (sorted.length - 1)) * innerW)
  const toY = (v: number) => pad.top + (1 - (v - minV) / range) * innerH

  const pathPts = sorted.map((s, i) => `${toX(i)},${toY(parseFloat(s.value))}`)
  const linePath = 'M ' + pathPts.join(' L ')
  const areaPath = `${linePath} L ${toX(sorted.length - 1)} ${H - pad.bottom} L ${toX(0)} ${H - pad.bottom} Z`
  const yTicks = [0, 0.5, 1].map((t) => ({ y: pad.top + (1 - t) * innerH, val: minV + t * range }))
  const step = Math.max(1, Math.ceil((sorted.length - 1) / 5))
  const xTickIndices = [...new Set([
    ...Array.from({ length: sorted.length }, (_, i) => i).filter((i) => i % step === 0),
    sorted.length - 1,
  ])]

  const fmtDate = (d: string) => new Date(d + 'T00:00:00').toLocaleDateString('fr-FR', { day: '2-digit', month: 'short', year: '2-digit' })
  const hov = hovered !== null ? sorted[hovered] : null

  return (
    <div className="relative flex flex-col h-full">
      <svg
        viewBox={`0 0 ${W} ${H}`}
        preserveAspectRatio="xMidYMid meet"
        style={{ width: '100%', flex: 1, minHeight: 0 }}
        onMouseLeave={() => setHovered(null)}
      >
        <defs>
          <linearGradient id="snapGrad" x1="0" y1="0" x2="0" y2="1">
            <stop offset="0%" stopColor={lineColor} stopOpacity={0.12} />
            <stop offset="100%" stopColor={lineColor} stopOpacity={0} />
          </linearGradient>
        </defs>
        {yTicks.map((t, i) => (
          <g key={i}>
            <line x1={pad.left} y1={t.y} x2={W - pad.right} y2={t.y} stroke={gridColor} strokeWidth={1} />
            <text x={pad.left - 5} y={t.y} textAnchor="end" dominantBaseline="middle" fontSize={8.5} fill="#9ca3af">
              {new Intl.NumberFormat('fr-FR', { notation: 'compact', maximumFractionDigits: 1 }).format(t.val)}
            </text>
          </g>
        ))}
        <path d={areaPath} fill="url(#snapGrad)" />
        <path d={linePath} fill="none" stroke={lineColor} strokeWidth={1.5} strokeLinejoin="round" />
        {xTickIndices.map((idx) => (
          <text key={idx} x={toX(idx)} y={H - pad.bottom + 13} textAnchor="middle" fontSize={8.5} fill="#9ca3af">
            {new Date(sorted[idx].date + 'T00:00:00').toLocaleDateString('fr-FR', { month: 'short', year: '2-digit' })}
          </text>
        ))}
        {sorted.map((_, i) => (
          <rect key={i} x={toX(i) - 8} y={pad.top} width={16} height={innerH} fill="transparent" onMouseEnter={() => setHovered(i)} />
        ))}
        {hovered !== null && (
          <>
            <line x1={toX(hovered)} y1={pad.top} x2={toX(hovered)} y2={H - pad.bottom} stroke="#d1d5db" strokeWidth={1} strokeDasharray="3,2" />
            <circle cx={toX(hovered)} cy={toY(parseFloat(sorted[hovered].value))} r={3} fill={lineColor} />
          </>
        )}
      </svg>
      {hov && (
        <div className="absolute top-1 left-1/2 -translate-x-1/2 bg-gray-900 text-white text-xs px-2.5 py-1.5 rounded-lg pointer-events-none whitespace-nowrap shadow-lg z-10">
          <span className="text-gray-400 mr-2">{fmtDate(hov.date)}</span>
          {format(hov.value, hov.currency)}
        </div>
      )}
    </div>
  )
}

// ── Benchmark Chart ────────────────────────────────────────────────────────────

interface PerfPoint { date: string; portfolioPct: number; benchmarkPct: number | null }

function PnlBenchmarkChart({ points, benchmarkLabel }: { points: PerfPoint[]; benchmarkLabel: string }) {
  const { theme } = useTheme()
  const isDark = theme === 'dark'
  const gridColor = isDark ? '#334155' : '#f3f4f6'
  const [hovered, setHovered] = useState<number | null>(null)

  const W = 600, H = 320
  const pad = { top: 16, right: 52, bottom: 32, left: 14 }
  const innerW = W - pad.left - pad.right
  const innerH = H - pad.top - pad.bottom

  const allPcts = points.flatMap((p) => [p.portfolioPct, p.benchmarkPct ?? p.portfolioPct])
  const minV = Math.min(...allPcts, 0)
  const maxV = Math.max(...allPcts, 0)
  const range = maxV - minV || 1

  const toX = (i: number) => pad.left + (points.length === 1 ? innerW / 2 : (i / (points.length - 1)) * innerW)
  const toY = (v: number) => pad.top + (1 - (v - minV) / range) * innerH
  const zeroY = toY(0)

  const portPts = points.map((p, i) => `${toX(i)},${toY(p.portfolioPct)}`).join(' L ')
  const portPath = `M ${portPts}`
  const areaPath = `M ${portPts} L ${toX(points.length - 1)},${zeroY} L ${toX(0)},${zeroY} Z`

  const benchPoints = points.filter((p) => p.benchmarkPct !== null)
  const benchPath = benchPoints.length > 1
    ? 'M ' + benchPoints.map((p) => `${toX(points.indexOf(p))},${toY(p.benchmarkPct!)}`).join(' L ')
    : null

  const lastPct = points[points.length - 1]?.portfolioPct ?? 0
  const isPositive = lastPct >= 0

  const yTickCount = 4
  const yTicks = Array.from({ length: yTickCount }, (_, i) => {
    const v = minV + (i / (yTickCount - 1)) * range
    return { y: toY(v), val: v }
  })

  const step = Math.max(1, Math.ceil((points.length - 1) / 5))
  const xTickIndices = [...new Set([
    ...Array.from({ length: points.length }, (_, i) => i).filter((i) => i % step === 0),
    points.length - 1,
  ])]

  const fmtDate = (d: string) => new Date(d + 'T00:00:00').toLocaleDateString('fr-FR', { day: '2-digit', month: 'short', year: '2-digit' })
  const hov = hovered !== null ? points[hovered] : null

  return (
    <div className="relative flex flex-col h-full">
      <div className="flex items-center gap-4 mb-2 flex-none">
        <div className="flex items-center gap-1.5">
          <div className="w-3 h-0.5 bg-blue-600 rounded" />
          <span className="text-[10px] text-gray-500">P&L portef.</span>
        </div>
        <div className="flex items-center gap-1.5">
          <div className="w-3 h-0.5 bg-orange-400 rounded" />
          <span className="text-[10px] text-gray-500">{benchmarkLabel}</span>
        </div>
      </div>
      <svg
        viewBox={`0 0 ${W} ${H}`}
        preserveAspectRatio="xMidYMid meet"
        style={{ width: '100%', flex: 1, minHeight: 0 }}
        onMouseLeave={() => setHovered(null)}
      >
        <defs>
          <linearGradient id="perfGradPos" x1="0" y1="0" x2="0" y2="1">
            <stop offset="0%" stopColor="#3b82f6" stopOpacity={0.12} />
            <stop offset="100%" stopColor="#3b82f6" stopOpacity={0.01} />
          </linearGradient>
          <linearGradient id="perfGradNeg" x1="0" y1="0" x2="0" y2="1">
            <stop offset="0%" stopColor="#ef4444" stopOpacity={0.01} />
            <stop offset="100%" stopColor="#ef4444" stopOpacity={0.12} />
          </linearGradient>
        </defs>
        {yTicks.map((t, i) => (
          <g key={i}>
            <line x1={pad.left} y1={t.y} x2={W - pad.right} y2={t.y}
              stroke={Math.abs(t.val) < 0.01 ? (isDark ? '#64748b' : '#d1d5db') : gridColor}
              strokeWidth={Math.abs(t.val) < 0.01 ? 1.5 : 1} />
            <text x={W - pad.right + 3} y={t.y} dominantBaseline="middle" fontSize={8.5} fill="#9ca3af">
              {t.val >= 0 ? '+' : ''}{t.val.toFixed(1)}%
            </text>
          </g>
        ))}
        <path d={areaPath} fill={isPositive ? 'url(#perfGradPos)' : 'url(#perfGradNeg)'} />
        {benchPath && <path d={benchPath} fill="none" stroke="#f97316" strokeWidth={1.5} strokeLinejoin="round" opacity={0.8} />}
        <path d={portPath} fill="none" stroke="#2563eb" strokeWidth={2} strokeLinejoin="round" />
        {xTickIndices.map((idx) => (
          <text key={idx} x={toX(idx)} y={H - pad.bottom + 13} textAnchor="middle" fontSize={8.5} fill="#9ca3af">
            {new Date(points[idx].date + 'T00:00:00').toLocaleDateString('fr-FR', { month: 'short', year: '2-digit' })}
          </text>
        ))}
        {points.map((_, i) => (
          <rect key={i} x={toX(i) - 10} y={pad.top} width={20} height={innerH} fill="transparent" onMouseEnter={() => setHovered(i)} />
        ))}
        {hovered !== null && (
          <>
            <line x1={toX(hovered)} y1={pad.top} x2={toX(hovered)} y2={H - pad.bottom} stroke="#d1d5db" strokeWidth={1} strokeDasharray="3,2" />
            <circle cx={toX(hovered)} cy={toY(points[hovered].portfolioPct)} r={3.5} fill="#2563eb" />
            {points[hovered].benchmarkPct !== null && (
              <circle cx={toX(hovered)} cy={toY(points[hovered].benchmarkPct!)} r={3} fill="#f97316" />
            )}
          </>
        )}
      </svg>
      {hov && (
        <div className="absolute top-1 left-1/2 -translate-x-1/2 bg-gray-900 text-white text-xs px-3 py-2 rounded-xl pointer-events-none whitespace-nowrap shadow-xl z-10">
          <div className="text-gray-400 text-center mb-1 text-[10px]">{fmtDate(hov.date)}</div>
          <div className="flex gap-4">
            <div>
              <div className="text-[10px] text-blue-300">P&L</div>
              <div className={`font-semibold ${hov.portfolioPct >= 0 ? 'text-blue-300' : 'text-red-400'}`}>
                {hov.portfolioPct >= 0 ? '+' : ''}{hov.portfolioPct.toFixed(2)}%
              </div>
            </div>
            {hov.benchmarkPct !== null && (
              <div>
                <div className="text-[10px] text-orange-300">{benchmarkLabel}</div>
                <div className={`font-semibold ${hov.benchmarkPct >= 0 ? 'text-orange-300' : 'text-red-400'}`}>
                  {hov.benchmarkPct >= 0 ? '+' : ''}{hov.benchmarkPct.toFixed(2)}%
                </div>
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  )
}

// ── PnL Badge ──────────────────────────────────────────────────────────────────

function PnlBadge({ value, currency }: { value: number; currency: string }) {
  const { format } = useCurrency()
  if (value === 0) return <span className="text-gray-400 tabular-nums">—</span>
  const positive = value >= 0
  return (
    <span className={`tabular-nums font-medium ${positive ? 'text-emerald-600' : 'text-red-500'}`}>
      {positive ? '+' : ''}{format(value.toFixed(2), currency)}
    </span>
  )
}

// ── Add Snapshot Modal ─────────────────────────────────────────────────────────

const today = () => new Date().toISOString().slice(0, 10)

function AddSnapshotModal({ portfolioId, currency, onClose }: {
  portfolioId: string; currency: string; onClose: () => void
}) {
  const addSnapshot = useAddSnapshot(portfolioId)
  const [date, setDate] = useState(today())
  const [value, setValue] = useState('')
  const [note, setNote] = useState('')
  const [error, setError] = useState('')

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault()
    if (!value.trim() || isNaN(parseFloat(value))) { setError('Valeur invalide'); return }
    try {
      await addSnapshot.mutateAsync({ date, value: parseFloat(value).toString(), currency, note: note || undefined })
      onClose()
    } catch { setError('Erreur lors de l\'enregistrement') }
  }

  return (
    <div className="fixed inset-0 bg-black/20 backdrop-blur-sm z-50 flex items-center justify-center p-4">
      <div className="bg-white dark:bg-gray-900 rounded-2xl shadow-2xl w-full max-w-sm">
        <div className="px-6 py-5 border-b border-gray-100 dark:border-gray-800 flex items-center justify-between">
          <h2 className="text-base font-semibold text-gray-900 dark:text-white">Ajouter un snapshot</h2>
          <button onClick={onClose} className="text-gray-400 hover:text-gray-600 dark:hover:text-gray-300 text-lg leading-none">×</button>
        </div>
        <form onSubmit={handleSubmit} className="px-6 py-5 space-y-4">
          <div>
            <label className="block text-xs font-medium text-gray-700 dark:text-gray-300 mb-1.5">Date</label>
            <input type="date" value={date} onChange={(e) => setDate(e.target.value)}
              className="w-full border border-gray-200 dark:border-gray-700 dark:bg-gray-800 dark:text-white rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-gray-900 dark:focus:ring-gray-300" />
          </div>
          <div>
            <label className="block text-xs font-medium text-gray-700 dark:text-gray-300 mb-1.5">Valeur ({currency})</label>
            <input value={value} onChange={(e) => setValue(e.target.value)} placeholder="12500.00" autoFocus
              className="w-full border border-gray-200 dark:border-gray-700 dark:bg-gray-800 dark:text-white rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-gray-900 dark:focus:ring-gray-300" />
          </div>
          <div>
            <label className="block text-xs font-medium text-gray-700 dark:text-gray-300 mb-1.5">Note (optionnel)</label>
            <input value={note} onChange={(e) => setNote(e.target.value)} placeholder="Valorisation…"
              className="w-full border border-gray-200 dark:border-gray-700 dark:bg-gray-800 dark:text-white rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-gray-900 dark:focus:ring-gray-300" />
          </div>
          {error && <p className="text-xs text-red-600 dark:text-red-400">{error}</p>}
          <div className="flex justify-end gap-2 pt-1">
            <button type="button" onClick={onClose} className="px-4 py-2 text-sm text-gray-600 dark:text-gray-400 hover:text-gray-900 dark:hover:text-white">Annuler</button>
            <button type="submit" disabled={addSnapshot.isPending}
              className="px-4 py-2 bg-gray-900 dark:bg-white text-white dark:text-gray-900 text-sm font-medium rounded-lg hover:bg-gray-800 dark:hover:bg-gray-100 disabled:opacity-60">
              {addSnapshot.isPending ? 'Enregistrement…' : 'Enregistrer'}
            </button>
          </div>
        </form>
      </div>
    </div>
  )
}

// ── Page ──────────────────────────────────────────────────────────────────────

type TableTab = 'positions' | 'instruments'

export default function PortfolioAnalysisPage() {
  const { format } = useCurrency()
  const { id } = useParams<{ id: string }>()
  const portfolioId = id ?? ''

  const { data: portfolios = [] } = usePortfolios()
  const portfolio = portfolios.find((p) => p.id === portfolioId)

  const queryClient = useQueryClient()
  const [selection, setSelection] = useState<PeriodSelection>({ type: 'preset', preset: '1A' })
  const [showSnapshotModal, setShowSnapshotModal] = useState(false)
  const [tableTab, setTableTab] = useState<TableTab>('positions')
  const [refreshing, setRefreshing] = useState(false)

  const handleRefreshPrices = async () => {
    setRefreshing(true)
    try {
      await pricesApi.updateDaily()
      await queryClient.invalidateQueries({ queryKey: ['prices'] })
    } finally {
      setRefreshing(false)
    }
  }

  const minMonth = `${new Date().getFullYear() - 10}-01`
  const dates = useMemo(() => resolveDates(selection, `${minMonth}-01`), [selection, minMonth])

  const { data: allTrades = [], isLoading: tradesLoading } = useTrades(portfolioId)
  const { data: positions = [], isLoading: positionsLoading } = usePositions(portfolioId)
  const { data: snapshots = [], isLoading: snapshotsLoading } = useSnapshots(portfolioId)
  const { data: instruments = [] } = useInstruments()
  const { data: latestPricesArr = [] } = useLatestPrices()

  const currency = portfolio?.currency ?? 'EUR'

  const latestPrices = useMemo(() => new Map(latestPricesArr.map((p) => [p.symbol, p])), [latestPricesArr])

  const benchmarkSymbol = useMemo(() => {
    if (latestPricesArr.length === 0 || positions.length === 0) return null
    const priceMap = new Map(latestPricesArr.map((p) => [p.symbol, parseFloat(p.price)]))
    let best: { symbol: string; value: number } | null = null
    for (const pos of positions) {
      const qty = parseFloat(pos.quantity)
      if (qty <= 0) continue
      const price = priceMap.get(pos.instrument_symbol.toUpperCase()) ?? 0
      const value = qty * price
      if (!best || value > best.value) best = { symbol: pos.instrument_symbol.toUpperCase(), value }
    }
    return best?.symbol ?? null
  }, [positions, latestPricesArr])

  const benchmarkInstrument = useMemo(
    () => instruments.find((i) => i.symbol === benchmarkSymbol) ?? null,
    [instruments, benchmarkSymbol],
  )

  const { data: benchPrices = [] } = usePriceHistory(benchmarkSymbol, dates.from, dates.to)

  const periodTrades = useMemo(
    () => allTrades.filter((t) => t.date >= dates.from && t.date <= dates.to && t.trade_type !== 'TRANSFER'),
    [allTrades, dates],
  )

  const periodSnapshots = useMemo(
    () => snapshots.filter((s) => s.date >= dates.from && s.date <= dates.to),
    [snapshots, dates],
  )

  const kpis = useMemo(() => {
    let invested = 0, proceeds = 0, totalFees = 0
    for (const t of periodTrades) {
      const qty = parseFloat(t.quantity), price = parseFloat(t.price), fees = parseFloat(t.fees ?? '0')
      totalFees += fees
      if (t.side === 'BUY') invested += qty * price
      else proceeds += qty * price
    }
    return { invested: invested.toFixed(2), proceeds: proceeds.toFixed(2), fees: totalFees.toFixed(2) }
  }, [periodTrades])

  const currentValuation = useMemo(() => {
    let total = 0
    for (const pos of positions) {
      const qty = parseFloat(pos.quantity)
      if (qty === 0) continue
      const pp = latestPrices.get(pos.instrument_symbol.toUpperCase())
      if (pp) total += qty * parseFloat(pp.price)
    }
    return total
  }, [positions, latestPrices])

  const portfolioPnl = useMemo(() => {
    const netInvested = allTrades
      .filter((t) => t.trade_type !== 'TRANSFER')
      .reduce((sum, t) => {
        const amt = parseFloat(t.quantity) * parseFloat(t.price)
        return t.side === 'BUY' ? sum + amt : sum - amt
      }, 0)
    if (netInvested <= 0) return null
    const pnl = currentValuation - netInvested
    return { pnl, netInvested, pnlPct: (pnl / netInvested) * 100 }
  }, [allTrades, currentValuation])

  const avgCostBySymbol = useMemo(() => {
    const map: Record<string, { buyQty: number; buyAmount: number }> = {}
    for (const t of allTrades) {
      if (t.side !== 'BUY' || t.trade_type === 'TRANSFER') continue
      if (!map[t.instrument_symbol]) map[t.instrument_symbol] = { buyQty: 0, buyAmount: 0 }
      map[t.instrument_symbol].buyQty += parseFloat(t.quantity)
      map[t.instrument_symbol].buyAmount += parseFloat(t.quantity) * parseFloat(t.price)
    }
    const result: Record<string, number> = {}
    for (const [sym, { buyQty, buyAmount }] of Object.entries(map))
      result[sym] = buyQty > 0 ? buyAmount / buyQty : 0
    return result
  }, [allTrades])

  interface InstrumentStats {
    symbol: string; buyQty: number; buyAmount: number; sellQty: number; sellAmount: number; fees: number
  }

  const instrumentStats = useMemo((): InstrumentStats[] => {
    const map: Record<string, InstrumentStats> = {}
    for (const t of periodTrades) {
      if (!map[t.instrument_symbol])
        map[t.instrument_symbol] = { symbol: t.instrument_symbol, buyQty: 0, buyAmount: 0, sellQty: 0, sellAmount: 0, fees: 0 }
      const qty = parseFloat(t.quantity), price = parseFloat(t.price), fees = parseFloat(t.fees ?? '0')
      map[t.instrument_symbol].fees += fees
      if (t.side === 'BUY') { map[t.instrument_symbol].buyQty += qty; map[t.instrument_symbol].buyAmount += qty * price }
      else { map[t.instrument_symbol].sellQty += qty; map[t.instrument_symbol].sellAmount += qty * price }
    }
    return Object.values(map).sort((a, b) => b.buyAmount - a.buyAmount)
  }, [periodTrades])

  const perfPoints = useMemo((): PerfPoint[] => {
    const sorted = [...periodSnapshots].sort((a, b) => a.date.localeCompare(b.date))
    if (sorted.length < 2) return []
    const netInvestedAt = (date: string): number =>
      allTrades.filter((t) => t.trade_type !== 'TRANSFER' && t.date <= date)
        .reduce((sum, t) => { const amt = parseFloat(t.quantity) * parseFloat(t.price); return t.side === 'BUY' ? sum + amt : sum - amt }, 0)
    const benchMap = new Map(benchPrices.map((p) => [p.day, parseFloat(p.price)]))
    let firstBenchPrice: number | null = null
    for (const snap of sorted) {
      const bp = benchMap.get(snap.date)
      if (bp !== undefined) { firstBenchPrice = bp; break }
    }
    return sorted.map((snap) => {
      const value = parseFloat(snap.value)
      const invested = netInvestedAt(snap.date)
      const portfolioPct = invested > 0 ? ((value - invested) / invested) * 100 : 0
      const benchPrice = benchMap.get(snap.date) ?? null
      const benchmarkPct = benchPrice !== null && firstBenchPrice !== null && firstBenchPrice > 0
        ? ((benchPrice - firstBenchPrice) / firstBenchPrice) * 100 : null
      return { date: snap.date, portfolioPct, benchmarkPct }
    })
  }, [periodSnapshots, allTrades, benchPrices])

  const enrichedPositions = useMemo(() => {
    return positions
      .filter((p) => parseFloat(p.quantity) !== 0)
      .map((p) => {
        const qty = parseFloat(p.quantity)
        const pp = latestPrices.get(p.instrument_symbol.toUpperCase())
        const latestPrice = pp ? parseFloat(pp.price) : null
        const currentValue = latestPrice !== null ? qty * latestPrice : null
        const avgCost = avgCostBySymbol[p.instrument_symbol] ?? null
        const pnl = currentValue !== null && avgCost !== null ? currentValue - avgCost * qty : null
        return { ...p, qty, latestPrice, currentValue, pnl, priceDate: pp?.day ?? null }
      })
      .sort((a, b) => (b.currentValue ?? b.qty) - (a.currentValue ?? a.qty))
  }, [positions, latestPrices, avgCostBySymbol])

  const positionsMaxValue = useMemo(
    () => Math.max(...enrichedPositions.map((p) => p.currentValue ?? p.qty), 1),
    [enrichedPositions],
  )

  const fmtQty = (q: number) =>
    q % 1 === 0 ? q.toLocaleString('fr-FR') : q.toLocaleString('fr-FR', { maximumFractionDigits: 8 })
  const fmtPrice = (price: number, cur: string) =>
    format(price.toFixed(price < 1 ? 6 : 2), cur)

  const hasBenchmark = perfPoints.length >= 2
  const hasSnapshot = periodSnapshots.length >= 2
  const [chartView, setChartView] = useState<'value' | 'perf'>('value')

  return (
    <div className="h-full flex flex-col p-6 gap-4 overflow-hidden">

      {/* Header */}
      <div className="flex-none flex items-center justify-between gap-4 flex-wrap">
        <div className="flex items-center gap-3">
          <Link to={`/portfolios/${portfolioId}`} className="text-xs text-gray-400 hover:text-gray-600 dark:hover:text-gray-300 transition-colors">←</Link>
          <div className="flex items-center gap-2">
            <div>
              <div className="flex items-center gap-2">
                <h1 className="text-xl font-semibold text-gray-900 dark:text-white">{portfolio?.name ?? '…'}</h1>
                {portfolio && (
                  <span className={`text-[10px] font-semibold px-1.5 py-0.5 rounded-md ${TYPE_COLORS[portfolio.portfolio_type] ?? TYPE_COLORS.OTHER}`}>
                    {TYPE_LABELS[portfolio.portfolio_type] ?? portfolio.portfolio_type}
                  </span>
                )}
              </div>
              <p className="text-xs text-gray-400 dark:text-gray-500">Analyse · {currency}</p>
            </div>
          </div>
        </div>
        <div className="flex items-center gap-3">
          <button
            onClick={handleRefreshPrices}
            disabled={refreshing}
            className="text-xs font-medium text-gray-500 dark:text-gray-400 hover:text-gray-900 dark:hover:text-white transition-colors px-2.5 py-1.5 rounded-lg border border-gray-200 dark:border-gray-700 hover:border-gray-300 dark:hover:border-gray-600 disabled:opacity-50 flex items-center gap-1.5"
          >
            <span className={refreshing ? 'animate-spin inline-block' : ''}>↻</span>
            {refreshing ? 'Actualisation…' : 'Actualiser les prix'}
          </button>
          <PeriodPicker selection={selection} onChange={setSelection} minMonth={minMonth} />
        </div>
      </div>

      {/* KPI row */}
      <div className="flex-none grid grid-cols-5 gap-3">
        {[
          {
            label: 'Valorisation',
            value: positionsLoading ? null : format(currentValuation.toFixed(2), currency),
            color: 'text-blue-700',
            sub: latestPricesArr.length === 0 ? 'Prix non disponibles' : undefined,
          },
          {
            label: 'P&L all-time',
            value: tradesLoading || positionsLoading ? null : format((portfolioPnl?.pnl ?? 0).toFixed(2), currency),
            color: portfolioPnl && portfolioPnl.pnl >= 0 ? 'text-emerald-600' : 'text-red-600',
            sub: portfolioPnl ? `${portfolioPnl.pnlPct >= 0 ? '+' : ''}${portfolioPnl.pnlPct.toFixed(2)}%` : undefined,
          },
          {
            label: 'Investi (période)',
            value: tradesLoading ? null : format(kpis.invested, currency),
            color: 'text-gray-900 dark:text-white',
          },
          {
            label: 'Cédé (période)',
            value: tradesLoading ? null : format(kpis.proceeds, currency),
            color: 'text-emerald-600',
          },
          {
            label: 'Frais (période)',
            value: tradesLoading ? null : format(kpis.fees, currency),
            color: 'text-red-600',
          },
        ].map(({ label, value, color, sub }) => (
          <div key={label} className="rounded-xl border border-gray-100 dark:border-gray-800 bg-white dark:bg-gray-900 px-5 py-4 hover:shadow-sm dark:hover:shadow-none transition-shadow">
            <p className="text-[10px] font-medium text-gray-400 dark:text-gray-500 uppercase tracking-wider">{label}</p>
            {value !== null
              ? <p className={`text-base font-semibold tabular-nums tracking-tight mt-1 ${color}`}>{value}</p>
              : <div className="h-6 w-24 bg-gray-100 dark:bg-gray-800 rounded animate-pulse mt-1" />
            }
            {sub && value !== null && <p className="text-[10px] text-gray-400 dark:text-gray-500 mt-0.5">{sub}</p>}
          </div>
        ))}
      </div>

      {/* Main grid */}
      <div className="flex-1 min-h-0 grid grid-cols-5 gap-4">

        {/* Left — chart */}
        <div className="col-span-3 rounded-xl border border-gray-100 dark:border-gray-800 bg-white dark:bg-gray-900 p-4 flex flex-col min-h-0">
          <div className="flex-none flex items-center justify-between mb-3">
            <p className="text-[10px] font-medium text-gray-400 dark:text-gray-500 uppercase tracking-wider">
              {chartView === 'value'
                ? 'Évolution de la valeur'
                : `Performance · vs ${benchmarkInstrument?.name || benchmarkSymbol || 'benchmark'}`}
            </p>
            <div className="flex items-center gap-0.5 bg-gray-100 dark:bg-gray-800 rounded-lg p-0.5">
              <button
                onClick={() => setChartView('value')}
                className={`px-2.5 py-1 text-xs font-medium rounded-lg transition-colors ${chartView === 'value' ? 'bg-white dark:bg-gray-700 text-gray-900 dark:text-white shadow-sm' : 'text-gray-500 dark:text-gray-400 hover:text-gray-700 dark:hover:text-gray-200'}`}
              >
                Valeur
              </button>
              <button
                onClick={() => setChartView('perf')}
                disabled={!hasBenchmark}
                className={`px-2.5 py-1 text-xs font-medium rounded-lg transition-colors ${chartView === 'perf' ? 'bg-white dark:bg-gray-700 text-gray-900 dark:text-white shadow-sm' : 'text-gray-500 dark:text-gray-400 hover:text-gray-700 dark:hover:text-gray-200'} disabled:opacity-40 disabled:cursor-not-allowed`}
              >
                Performance
              </button>
            </div>
          </div>
          <div className="flex-1 min-h-0">
            {snapshotsLoading ? (
              <div className="h-full bg-gray-50 dark:bg-gray-800 rounded-xl animate-pulse" />
            ) : chartView === 'perf' && hasBenchmark ? (
              <PnlBenchmarkChart
                points={perfPoints}
                benchmarkLabel={benchmarkInstrument?.name || benchmarkSymbol || ''}
              />
            ) : hasSnapshot ? (
              <SnapshotChart snapshots={periodSnapshots} />
            ) : (
              <div className="flex flex-col items-center justify-center h-full gap-3 text-gray-400 dark:text-gray-500">
                <span className="text-4xl opacity-20">◎</span>
                <p className="text-sm">{snapshots.length === 0 ? 'Aucun snapshot enregistré' : 'Pas assez de snapshots sur la période'}</p>
                <button
                  onClick={() => setShowSnapshotModal(true)}
                  className="text-xs text-gray-500 dark:text-gray-400 hover:text-gray-900 dark:hover:text-white border border-gray-200 dark:border-gray-700 rounded-lg px-3 py-1.5 transition-colors"
                >
                  Ajouter un snapshot
                </button>
              </div>
            )}
          </div>
        </div>

        {/* Right — table avec tabs */}
        <div className="col-span-2 rounded-xl border border-gray-100 dark:border-gray-800 bg-white dark:bg-gray-900 flex flex-col min-h-0">
          <div className="flex-none px-4 py-3 border-b border-gray-50 dark:border-gray-800 flex items-center justify-between">
            <div className="flex items-center gap-0.5 bg-gray-100 dark:bg-gray-800 rounded-lg p-0.5">
              {([
                { key: 'positions' as TableTab, label: 'Positions actuelles' },
                { key: 'instruments' as TableTab, label: 'Analyse (période)' },
              ]).map((o) => (
                <button
                  key={o.key}
                  onClick={() => setTableTab(o.key)}
                  className={`px-2.5 py-1 text-xs font-medium rounded-lg transition-colors ${tableTab === o.key ? 'bg-white dark:bg-gray-700 text-gray-900 dark:text-white shadow-sm' : 'text-gray-500 dark:text-gray-400 hover:text-gray-700 dark:hover:text-gray-200'}`}
                >
                  {o.label}
                </button>
              ))}
            </div>
          </div>

          <div className="flex-1 min-h-0 overflow-y-auto">
            {tableTab === 'positions' ? (
              positionsLoading ? (
                <div className="flex items-center justify-center h-full">
                  <div className="w-5 h-5 border-2 border-gray-200 dark:border-gray-700 border-t-gray-700 dark:border-t-gray-300 rounded-full animate-spin" />
                </div>
              ) : enrichedPositions.length === 0 ? (
                <div className="flex items-center justify-center h-full text-sm text-gray-400 dark:text-gray-500">Aucune position ouverte</div>
              ) : (
                <table className="w-full text-xs">
                  <thead className="sticky top-0 bg-white dark:bg-gray-900 z-10">
                    <tr className="border-b border-gray-100 dark:border-gray-800">
                      <th className="text-left text-gray-400 dark:text-gray-500 font-medium py-2.5 px-4 uppercase tracking-wider text-[10px]">Actif</th>
                      <th className="text-right text-gray-400 dark:text-gray-500 font-medium py-2.5 px-3 uppercase tracking-wider text-[10px]">Qté</th>
                      <th className="text-right text-gray-400 dark:text-gray-500 font-medium py-2.5 px-3 uppercase tracking-wider text-[10px]">Cours</th>
                      <th className="text-right text-gray-400 dark:text-gray-500 font-medium py-2.5 px-3 uppercase tracking-wider text-[10px]">Valeur</th>
                      <th className="text-right text-gray-400 dark:text-gray-500 font-medium py-2.5 px-4 uppercase tracking-wider text-[10px]">P&L latent</th>
                    </tr>
                  </thead>
                  <tbody>
                    {enrichedPositions.map((p) => {
                      const barPct = ((p.currentValue ?? p.qty) / positionsMaxValue) * 100
                      return (
                        <tr key={p.instrument_symbol} className="border-b border-gray-50 dark:border-gray-800 hover:bg-gray-50 dark:hover:bg-gray-800/50">
                          <td className="py-2.5 px-4">
                            <div className="font-medium text-gray-900 dark:text-white">{instLabel(instruments, p.instrument_symbol)}</div>
                            <div className="text-[10px] text-gray-400 dark:text-gray-500 font-mono">{p.instrument_symbol}</div>
                            <div className="mt-1 h-0.5 w-20 bg-gray-100 dark:bg-gray-800 rounded-full overflow-hidden">
                              <div className="h-full bg-gray-400 dark:bg-gray-500 rounded-full" style={{ width: `${barPct}%` }} />
                            </div>
                          </td>
                          <td className="py-2.5 px-3 text-right text-gray-600 dark:text-gray-400 tabular-nums">{fmtQty(p.qty)}</td>
                          <td className="py-2.5 px-3 text-right tabular-nums">
                            {p.latestPrice !== null ? (
                              <div>
                                <div className="text-gray-700 dark:text-gray-300">{fmtPrice(p.latestPrice, currency)}</div>
                                {p.priceDate && <div className="text-[10px] text-gray-400 dark:text-gray-500">{p.priceDate}</div>}
                              </div>
                            ) : <span className="text-gray-400 dark:text-gray-500">—</span>}
                          </td>
                          <td className="py-2.5 px-3 text-right text-gray-900 dark:text-white font-semibold tabular-nums">
                            {p.currentValue !== null ? format(p.currentValue.toFixed(2), currency) : '—'}
                          </td>
                          <td className="py-2.5 px-4 text-right tabular-nums">
                            {p.pnl !== null ? <PnlBadge value={p.pnl} currency={currency} /> : <span className="text-gray-400 dark:text-gray-500">—</span>}
                          </td>
                        </tr>
                      )
                    })}
                  </tbody>
                  <tfoot className="sticky bottom-0 bg-white dark:bg-gray-900 border-t border-gray-200 dark:border-gray-700">
                    <tr>
                      <td colSpan={3} className="pt-2.5 px-4 text-gray-500 dark:text-gray-400 font-medium">Total</td>
                      <td className="pt-2.5 px-3 text-right text-gray-900 dark:text-white font-semibold tabular-nums">
                        {format(currentValuation.toFixed(2), currency)}
                      </td>
                      <td className="pt-2.5 px-4 text-right">
                        <PnlBadge value={enrichedPositions.reduce((s, p) => s + (p.pnl ?? 0), 0)} currency={currency} />
                      </td>
                    </tr>
                  </tfoot>
                </table>
              )
            ) : (
              tradesLoading ? (
                <div className="flex items-center justify-center h-full">
                  <div className="w-5 h-5 border-2 border-gray-200 dark:border-gray-700 border-t-gray-700 dark:border-t-gray-300 rounded-full animate-spin" />
                </div>
              ) : instrumentStats.length === 0 ? (
                <div className="flex items-center justify-center h-full text-sm text-gray-400 dark:text-gray-500">Aucun trade sur cette période</div>
              ) : (
                <table className="w-full text-xs">
                  <thead className="sticky top-0 bg-white dark:bg-gray-900 z-10">
                    <tr className="border-b border-gray-100 dark:border-gray-800">
                      <th className="text-left text-gray-400 dark:text-gray-500 font-medium py-2.5 px-4 uppercase tracking-wider text-[10px]">Symbole</th>
                      <th className="text-right text-gray-400 dark:text-gray-500 font-medium py-2.5 px-3 uppercase tracking-wider text-[10px]">Qté achetée</th>
                      <th className="text-right text-gray-400 dark:text-gray-500 font-medium py-2.5 px-3 uppercase tracking-wider text-[10px]">Montant investi</th>
                      <th className="text-right text-gray-400 dark:text-gray-500 font-medium py-2.5 px-3 uppercase tracking-wider text-[10px]">Prix moy.</th>
                      <th className="text-right text-gray-400 dark:text-gray-500 font-medium py-2.5 px-3 uppercase tracking-wider text-[10px]">Frais</th>
                      <th className="text-right text-gray-400 dark:text-gray-500 font-medium py-2.5 px-4 uppercase tracking-wider text-[10px]">Valeur actuelle</th>
                    </tr>
                  </thead>
                  <tbody>
                    {instrumentStats.map((s) => {
                      const pos = positions.find((p) => p.instrument_symbol === s.symbol)
                      const posQty = pos ? parseFloat(pos.quantity) : 0
                      const pp = latestPrices.get(s.symbol.toUpperCase())
                      const currentVal = pp && posQty !== 0 ? posQty * parseFloat(pp.price) : null
                      return (
                        <tr key={s.symbol} className="border-b border-gray-50 dark:border-gray-800 hover:bg-gray-50 dark:hover:bg-gray-800/50">
                          <td className="py-2 px-4">
                            <div className="font-medium text-gray-900 dark:text-white">{instLabel(instruments, s.symbol)}</div>
                            <div className="text-[10px] text-gray-400 dark:text-gray-500 font-mono">{s.symbol}</div>
                          </td>
                          <td className="py-2 px-3 text-right text-gray-600 dark:text-gray-400 tabular-nums">{fmtQty(s.buyQty)}</td>
                          <td className="py-2 px-3 text-right text-gray-700 dark:text-gray-300 font-medium tabular-nums">{format(s.buyAmount.toFixed(2), currency)}</td>
                          <td className="py-2 px-3 text-right text-gray-600 dark:text-gray-400 tabular-nums">
                            {s.buyQty > 0 ? format((s.buyAmount / s.buyQty).toFixed(4), currency) : '—'}
                          </td>
                          <td className="py-2 px-3 text-right text-red-500 dark:text-red-400 tabular-nums">
                            {s.fees > 0 ? format(s.fees.toFixed(2), currency) : '—'}
                          </td>
                          <td className="py-2 px-4 text-right tabular-nums">
                            {currentVal !== null
                              ? <span className="font-medium text-blue-700 dark:text-blue-400">{format(currentVal.toFixed(2), currency)}</span>
                              : <span className="text-gray-400 dark:text-gray-500">—</span>}
                          </td>
                        </tr>
                      )
                    })}
                  </tbody>
                  <tfoot className="sticky bottom-0 bg-white dark:bg-gray-900 border-t border-gray-200 dark:border-gray-700">
                    <tr>
                      <td className="pt-2 px-4 text-gray-500 dark:text-gray-400 font-medium">Total</td>
                      <td className="pt-2 px-3" />
                      <td className="pt-2 px-3 text-right text-gray-900 dark:text-white font-semibold tabular-nums">{format(kpis.invested, currency)}</td>
                      <td className="pt-2 px-3" />
                      <td className="pt-2 px-3 text-right text-red-600 dark:text-red-400 font-semibold tabular-nums">{format(kpis.fees, currency)}</td>
                      <td className="pt-2 px-4 text-right text-blue-700 dark:text-blue-400 font-semibold tabular-nums">{format(currentValuation.toFixed(2), currency)}</td>
                    </tr>
                  </tfoot>
                </table>
              )
            )}
          </div>
        </div>

      </div>

      {showSnapshotModal && (
        <AddSnapshotModal portfolioId={portfolioId} currency={currency} onClose={() => setShowSnapshotModal(false)} />
      )}
    </div>
  )
}
