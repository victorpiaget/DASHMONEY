import { useState, useMemo, type FormEvent, type ReactNode } from 'react'
import { Link, useParams } from 'react-router-dom'
import { usePortfolios, useTrades, usePositions, useSnapshots, useAddSnapshot, useInstruments, useLatestPrices, usePriceHistory } from '../hooks/usePortfolios'
import { useCurrency } from '../context/CurrencyContext'
import PeriodPicker, { type PeriodSelection, resolveDates } from '../components/PeriodPicker'
import type { PortfolioSnapshot, Instrument } from '../lib/portfoliosApi'

function instLabel(instruments: Instrument[], symbol: string): string {
  const inst = instruments.find((i) => i.symbol === symbol)
  return inst?.name || symbol
}

// ── TYPE_LABELS (mirrors PortfoliosPage) ─────────────────────────────────────

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

// ── Snapshot SVG line chart ───────────────────────────────────────────────────

function SnapshotChart({ snapshots }: { snapshots: PortfolioSnapshot[]; currency: string }) {
  const { format } = useCurrency()
  const [hovered, setHovered] = useState<number | null>(null)

  const sorted = useMemo(
    () => [...snapshots].sort((a, b) => a.date.localeCompare(b.date)),
    [snapshots],
  )

  const W = 600, H = 160
  const pad = { top: 16, right: 16, bottom: 30, left: 72 }
  const innerW = W - pad.left - pad.right
  const innerH = H - pad.top - pad.bottom

  const values = sorted.map((s) => parseFloat(s.value))
  const minV = Math.min(...values)
  const maxV = Math.max(...values)
  const range = maxV - minV || 1

  const toX = (i: number) =>
    pad.left + (sorted.length === 1 ? innerW / 2 : (i / (sorted.length - 1)) * innerW)
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

  const fmtDate = (d: string) =>
    new Date(d + 'T00:00:00').toLocaleDateString('fr-FR', { day: '2-digit', month: 'short', year: '2-digit' })

  const hov = hovered !== null ? sorted[hovered] : null

  return (
    <div className="relative">
      <svg viewBox={`0 0 ${W} ${H}`} className="w-full" style={{ height: 180 }} onMouseLeave={() => setHovered(null)}>
        <defs>
          <linearGradient id="snapGrad" x1="0" y1="0" x2="0" y2="1">
            <stop offset="0%" stopColor="#111827" stopOpacity={0.1} />
            <stop offset="100%" stopColor="#111827" stopOpacity={0} />
          </linearGradient>
        </defs>

        {yTicks.map((t, i) => (
          <g key={i}>
            <line x1={pad.left} y1={t.y} x2={W - pad.right} y2={t.y} stroke="#f3f4f6" strokeWidth={1} />
            <text x={pad.left - 6} y={t.y} textAnchor="end" dominantBaseline="middle" fontSize={9} fill="#9ca3af">
              {new Intl.NumberFormat('fr-FR', { notation: 'compact', maximumFractionDigits: 1 }).format(t.val)}
            </text>
          </g>
        ))}

        <path d={areaPath} fill="url(#snapGrad)" />
        <path d={linePath} fill="none" stroke="#111827" strokeWidth={1.5} strokeLinejoin="round" />

        {xTickIndices.map((idx) => (
          <text key={idx} x={toX(idx)} y={H - pad.bottom + 14} textAnchor="middle" fontSize={9} fill="#9ca3af">
            {new Date(sorted[idx].date + 'T00:00:00').toLocaleDateString('fr-FR', { month: 'short', year: '2-digit' })}
          </text>
        ))}

        {sorted.map((_, i) => (
          <rect key={i} x={toX(i) - 8} y={pad.top} width={16} height={innerH} fill="transparent" onMouseEnter={() => setHovered(i)} />
        ))}

        {hovered !== null && (
          <>
            <line x1={toX(hovered)} y1={pad.top} x2={toX(hovered)} y2={H - pad.bottom} stroke="#d1d5db" strokeWidth={1} strokeDasharray="3,2" />
            <circle cx={toX(hovered)} cy={toY(parseFloat(sorted[hovered].value))} r={3.5} fill="#111827" />
          </>
        )}
      </svg>

      {hov && (
        <div className="absolute top-2 left-1/2 -translate-x-1/2 bg-gray-900 text-white text-xs px-2.5 py-1.5 rounded-lg pointer-events-none whitespace-nowrap shadow-lg">
          <span className="text-gray-400 mr-2">{fmtDate(hov.date)}</span>
          {format(hov.value, hov.currency)}
        </div>
      )}
    </div>
  )
}

// ── Helpers UI ────────────────────────────────────────────────────────────────

function KpiCard({ label, value, currency, color = 'default', note }: {
  label: string; value: string | null; currency: string; color?: 'emerald' | 'red' | 'blue' | 'default'; note?: string
}) {
  const { format } = useCurrency()
  const colorClass =
    color === 'emerald' ? 'text-emerald-600' :
    color === 'red' ? 'text-red-600' :
    color === 'blue' ? 'text-blue-700' :
    'text-gray-900'
  return (
    <div className="bg-white rounded-xl border border-gray-100 shadow-sm px-5 py-4">
      <p className="text-xs text-gray-400 uppercase tracking-wider mb-1.5">{label}</p>
      {value !== null
        ? <p className={`text-xl font-semibold tabular-nums ${colorClass}`}>{format(value, currency)}</p>
        : <div className="h-7 w-28 bg-gray-100 rounded animate-pulse" />
      }
      {note && <p className="text-[10px] text-gray-400 mt-1">{note}</p>}
    </div>
  )
}

function Section({ title, loading, children, right }: {
  title: string; loading: boolean; children: ReactNode; right?: ReactNode
}) {
  return (
    <div className="bg-white rounded-xl border border-gray-100 shadow-sm mb-6">
      <div className="px-5 py-4 border-b border-gray-50 flex items-center justify-between">
        <h2 className="text-sm font-medium text-gray-900">{title}</h2>
        {right}
      </div>
      <div className="px-5 py-5">
        {loading
          ? <div className="flex justify-center py-8"><div className="w-5 h-5 border-2 border-gray-200 border-t-gray-700 rounded-full animate-spin" /></div>
          : children
        }
      </div>
    </div>
  )
}

function EmptyState({ label }: { label: string }) {
  return <div className="flex items-center justify-center py-8"><p className="text-sm text-gray-400">{label}</p></div>
}

// ── PnL badge ─────────────────────────────────────────────────────────────────

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

// ── Performance chart (P&L % vs benchmark %) ─────────────────────────────────

interface PerfPoint { date: string; portfolioPct: number; benchmarkPct: number | null }

function PnlBenchmarkChart({
  points,
  benchmarkLabel,
}: {
  points: PerfPoint[]
  benchmarkLabel: string
}) {
  const [hovered, setHovered] = useState<number | null>(null)

  const W = 600, H = 200
  const pad = { top: 20, right: 56, bottom: 32, left: 16 }
  const innerW = W - pad.left - pad.right
  const innerH = H - pad.top - pad.bottom

  const allPcts = points.flatMap((p) => [p.portfolioPct, p.benchmarkPct ?? p.portfolioPct])
  const minV = Math.min(...allPcts, 0)
  const maxV = Math.max(...allPcts, 0)
  const range = maxV - minV || 1

  const toX = (i: number) =>
    pad.left + (points.length === 1 ? innerW / 2 : (i / (points.length - 1)) * innerW)
  const toY = (v: number) => pad.top + (1 - (v - minV) / range) * innerH
  const zeroY = toY(0)

  // Portfolio line + area
  const portPts = points.map((p, i) => `${toX(i)},${toY(p.portfolioPct)}`).join(' L ')
  const portPath = `M ${portPts}`
  const areaPath = `M ${portPts} L ${toX(points.length - 1)},${zeroY} L ${toX(0)},${zeroY} Z`

  // Benchmark line
  const benchPoints = points.filter((p) => p.benchmarkPct !== null)
  const benchPath = benchPoints.length > 1
    ? 'M ' + benchPoints.map((p) => {
        const i = points.indexOf(p)
        return `${toX(i)},${toY(p.benchmarkPct!)}`
      }).join(' L ')
    : null

  const lastPct = points[points.length - 1]?.portfolioPct ?? 0
  const isPositive = lastPct >= 0

  // Y axis ticks (%)
  const yTickCount = 5
  const yTicks = Array.from({ length: yTickCount }, (_, i) => {
    const v = minV + (i / (yTickCount - 1)) * range
    return { y: toY(v), val: v }
  })

  // X axis ticks
  const step = Math.max(1, Math.ceil((points.length - 1) / 6))
  const xTickIndices = [...new Set([
    ...Array.from({ length: points.length }, (_, i) => i).filter((i) => i % step === 0),
    points.length - 1,
  ])]

  const fmtDate = (d: string) =>
    new Date(d + 'T00:00:00').toLocaleDateString('fr-FR', { day: '2-digit', month: 'short', year: '2-digit' })

  const hov = hovered !== null ? points[hovered] : null

  return (
    <div>
      {/* Legend */}
      <div className="flex items-center gap-5 mb-3">
        <div className="flex items-center gap-1.5">
          <div className="w-4 h-0.5 bg-blue-600 rounded" />
          <span className="text-[11px] text-gray-500 font-medium">P&L portefeuille</span>
        </div>
        <div className="flex items-center gap-1.5">
          <div className="w-4 h-0.5 bg-orange-400 rounded" />
          <span className="text-[11px] text-gray-500">{benchmarkLabel}</span>
        </div>
      </div>

      <div className="relative">
        <svg viewBox={`0 0 ${W} ${H}`} className="w-full" style={{ height: 220 }} onMouseLeave={() => setHovered(null)}>
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

          {/* Grid lines + Y labels */}
          {yTicks.map((t, i) => (
            <g key={i}>
              <line x1={pad.left} y1={t.y} x2={W - pad.right} y2={t.y}
                stroke={Math.abs(t.val) < 0.01 ? '#d1d5db' : '#f3f4f6'}
                strokeWidth={Math.abs(t.val) < 0.01 ? 1.5 : 1} />
              <text x={W - pad.right + 4} y={t.y} dominantBaseline="middle" fontSize={9} fill="#9ca3af">
                {t.val >= 0 ? '+' : ''}{t.val.toFixed(1)}%
              </text>
            </g>
          ))}

          {/* Shaded P&L area */}
          <path d={areaPath} fill={isPositive ? 'url(#perfGradPos)' : 'url(#perfGradNeg)'} />

          {/* Benchmark line */}
          {benchPath && (
            <path d={benchPath} fill="none" stroke="#f97316" strokeWidth={1.5} strokeLinejoin="round" opacity={0.8} />
          )}

          {/* Portfolio line */}
          <path d={portPath} fill="none" stroke="#2563eb" strokeWidth={2} strokeLinejoin="round" />

          {/* X axis ticks */}
          {xTickIndices.map((idx) => (
            <text key={idx} x={toX(idx)} y={H - pad.bottom + 14} textAnchor="middle" fontSize={9} fill="#9ca3af">
              {new Date(points[idx].date + 'T00:00:00').toLocaleDateString('fr-FR', { month: 'short', year: '2-digit' })}
            </text>
          ))}

          {/* Hover zones */}
          {points.map((_, i) => (
            <rect key={i} x={toX(i) - 10} y={pad.top} width={20} height={innerH} fill="transparent" onMouseEnter={() => setHovered(i)} />
          ))}

          {/* Hover indicator */}
          {hovered !== null && (
            <>
              <line x1={toX(hovered)} y1={pad.top} x2={toX(hovered)} y2={H - pad.bottom}
                stroke="#d1d5db" strokeWidth={1} strokeDasharray="3,2" />
              <circle cx={toX(hovered)} cy={toY(points[hovered].portfolioPct)} r={4} fill="#2563eb" />
              {points[hovered].benchmarkPct !== null && (
                <circle cx={toX(hovered)} cy={toY(points[hovered].benchmarkPct!)} r={3.5} fill="#f97316" />
              )}
            </>
          )}
        </svg>

        {/* Tooltip */}
        {hov && (
          <div className="absolute top-1 left-1/2 -translate-x-1/2 bg-gray-900 text-white text-xs px-3 py-2 rounded-xl pointer-events-none whitespace-nowrap shadow-xl z-10">
            <div className="text-gray-400 text-center mb-1.5 text-[10px]">{fmtDate(hov.date)}</div>
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
    </div>
  )
}

// ── Modal ajout snapshot ──────────────────────────────────────────────────────

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
    } catch {
      setError('Erreur lors de l\'enregistrement')
    }
  }

  return (
    <div className="fixed inset-0 bg-black/20 backdrop-blur-sm z-50 flex items-center justify-center p-4">
      <div className="bg-white rounded-2xl shadow-2xl w-full max-w-sm">
        <div className="px-6 py-5 border-b border-gray-100 flex items-center justify-between">
          <h2 className="text-base font-semibold text-gray-900">Ajouter un snapshot</h2>
          <button onClick={onClose} className="text-gray-400 hover:text-gray-600 text-lg leading-none">×</button>
        </div>
        <form onSubmit={handleSubmit} className="px-6 py-5 space-y-4">
          <div>
            <label className="block text-xs font-medium text-gray-700 mb-1.5">Date</label>
            <input type="date" value={date} onChange={(e) => setDate(e.target.value)}
              className="w-full border border-gray-200 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-gray-900" />
          </div>
          <div>
            <label className="block text-xs font-medium text-gray-700 mb-1.5">Valeur ({currency})</label>
            <input value={value} onChange={(e) => setValue(e.target.value)} placeholder="12500.00"
              className="w-full border border-gray-200 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-gray-900"
              autoFocus />
          </div>
          <div>
            <label className="block text-xs font-medium text-gray-700 mb-1.5">Note (optionnel)</label>
            <input value={note} onChange={(e) => setNote(e.target.value)} placeholder="Valorisation…"
              className="w-full border border-gray-200 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-gray-900" />
          </div>
          {error && <p className="text-xs text-red-600">{error}</p>}
          <div className="flex justify-end gap-2 pt-1">
            <button type="button" onClick={onClose} className="px-4 py-2 text-sm text-gray-600 hover:text-gray-900 transition-colors">
              Annuler
            </button>
            <button type="submit" disabled={addSnapshot.isPending}
              className="px-4 py-2 bg-gray-900 text-white text-sm font-medium rounded-lg hover:bg-gray-800 disabled:opacity-60 transition-colors">
              {addSnapshot.isPending ? 'Enregistrement…' : 'Enregistrer'}
            </button>
          </div>
        </form>
      </div>
    </div>
  )
}

// ── Page principale ───────────────────────────────────────────────────────────

export default function PortfolioAnalysisPage() {
  const { format } = useCurrency()
  const { id } = useParams<{ id: string }>()
  const portfolioId = id ?? ''

  const { data: portfolios = [] } = usePortfolios()
  const portfolio = portfolios.find((p) => p.id === portfolioId)

  const [selection, setSelection] = useState<PeriodSelection>({ type: 'preset', preset: '1A' })
  const [showSnapshotModal, setShowSnapshotModal] = useState(false)

  const minMonth = `${new Date().getFullYear() - 10}-01`

  const dates = useMemo(() => resolveDates(selection, `${minMonth}-01`), [selection, minMonth])

  const { data: allTrades = [], isLoading: tradesLoading } = useTrades(portfolioId)
  const { data: positions = [], isLoading: positionsLoading } = usePositions(portfolioId)
  const { data: snapshots = [], isLoading: snapshotsLoading } = useSnapshots(portfolioId)
  const { data: instruments = [] } = useInstruments()
  const { data: latestPricesArr = [] } = useLatestPrices()

  // Benchmark : symbole de la position avec la plus grande valeur actuelle
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

  const currency = portfolio?.currency ?? 'EUR'

  // Map symbol → latest price
  const latestPrices = useMemo(
    () => new Map(latestPricesArr.map((p) => [p.symbol, p])),
    [latestPricesArr],
  )

  // ── Filtrage des trades sur la période (hors transferts d'actifs) ───────────

  const periodTrades = useMemo(() =>
    allTrades.filter((t) => t.date >= dates.from && t.date <= dates.to && t.trade_type !== 'TRANSFER'),
    [allTrades, dates],
  )

  // ── Filtrage des snapshots sur la période ───────────────────────────────────

  const periodSnapshots = useMemo(() =>
    snapshots.filter((s) => s.date >= dates.from && s.date <= dates.to),
    [snapshots, dates],
  )

  // ── KPIs calculés sur la période ────────────────────────────────────────────

  const kpis = useMemo(() => {
    let invested = 0, proceeds = 0, totalFees = 0
    for (const t of periodTrades) {
      const qty = parseFloat(t.quantity)
      const price = parseFloat(t.price)
      const fees = parseFloat(t.fees ?? '0')
      totalFees += fees
      if (t.side === 'BUY') invested += qty * price
      else proceeds += qty * price
    }
    return {
      invested: invested.toFixed(2),
      proceeds: proceeds.toFixed(2),
      fees: totalFees.toFixed(2),
    }
  }, [periodTrades])

  // ── Valorisation actuelle (positions × latest prices) ─────────────────────

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

  // ── P&L du portefeuille courant (all-time) ────────────────────────────────

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

  // ── Coût d'acquisition moyen (all-time) par symbol ────────────────────────

  const avgCostBySymbol = useMemo(() => {
    const map: Record<string, { buyQty: number; buyAmount: number }> = {}
    for (const t of allTrades) {
      if (t.side !== 'BUY' || t.trade_type === 'TRANSFER') continue
      if (!map[t.instrument_symbol]) map[t.instrument_symbol] = { buyQty: 0, buyAmount: 0 }
      const qty = parseFloat(t.quantity)
      const price = parseFloat(t.price)
      map[t.instrument_symbol].buyQty += qty
      map[t.instrument_symbol].buyAmount += qty * price
    }
    const result: Record<string, number> = {}
    for (const [sym, { buyQty, buyAmount }] of Object.entries(map)) {
      result[sym] = buyQty > 0 ? buyAmount / buyQty : 0
    }
    return result
  }, [allTrades])

  // ── Analyse par instrument ─────────────────────────────────────────────────

  interface InstrumentStats {
    symbol: string
    buyQty: number
    buyAmount: number
    sellQty: number
    sellAmount: number
    fees: number
  }

  const instrumentStats = useMemo((): InstrumentStats[] => {
    const map: Record<string, InstrumentStats> = {}
    for (const t of periodTrades) {
      if (!map[t.instrument_symbol]) {
        map[t.instrument_symbol] = { symbol: t.instrument_symbol, buyQty: 0, buyAmount: 0, sellQty: 0, sellAmount: 0, fees: 0 }
      }
      const qty = parseFloat(t.quantity)
      const price = parseFloat(t.price)
      const fees = parseFloat(t.fees ?? '0')
      map[t.instrument_symbol].fees += fees
      if (t.side === 'BUY') {
        map[t.instrument_symbol].buyQty += qty
        map[t.instrument_symbol].buyAmount += qty * price
      } else {
        map[t.instrument_symbol].sellQty += qty
        map[t.instrument_symbol].sellAmount += qty * price
      }
    }
    return Object.values(map).sort((a, b) => b.buyAmount - a.buyAmount)
  }, [periodTrades])

  // ── Courbe performance P&L % vs benchmark % ───────────────────────────────

  const perfPoints = useMemo((): PerfPoint[] => {
    const sorted = [...periodSnapshots].sort((a, b) => a.date.localeCompare(b.date))
    if (sorted.length < 2) return []

    // Coût net investi cumulé jusqu'à une date donnée (all-time, pas période)
    const netInvestedAt = (date: string): number => {
      return allTrades
        .filter((t) => t.trade_type !== 'TRANSFER' && t.date <= date)
        .reduce((sum, t) => {
          const amt = parseFloat(t.quantity) * parseFloat(t.price)
          return t.side === 'BUY' ? sum + amt : sum - amt
        }, 0)
    }

    // Index benchmark prices by date
    const benchMap = new Map(benchPrices.map((p) => [p.day, parseFloat(p.price)]))

    // Trouver le premier prix benchmark disponible dans la période
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
        ? ((benchPrice - firstBenchPrice) / firstBenchPrice) * 100
        : null

      return { date: snap.date, portfolioPct, benchmarkPct }
    })
  }, [periodSnapshots, allTrades, benchPrices])

  // ── Positions enrichies avec valeur actuelle ──────────────────────────────

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

  return (
    <div className="p-8">
      {/* Header */}
      <div className="mb-8">
        <Link to={`/portfolios/${portfolioId}`} className="text-xs text-gray-400 hover:text-gray-700 transition-colors mb-3 inline-block">
          ← Trades
        </Link>
        <div className="flex items-center justify-between flex-wrap gap-4">
          <div className="flex items-center gap-3">
            <div>
              <div className="flex items-center gap-2 mb-1">
                <h1 className="text-2xl font-semibold text-gray-900">{portfolio?.name ?? '…'}</h1>
                {portfolio && (
                  <span className={`text-[11px] font-semibold px-2 py-0.5 rounded-md ${TYPE_COLORS[portfolio.portfolio_type] ?? TYPE_COLORS.OTHER}`}>
                    {TYPE_LABELS[portfolio.portfolio_type] ?? portfolio.portfolio_type}
                  </span>
                )}
              </div>
              <p className="text-sm text-gray-400">Analyse · {currency}</p>
            </div>
          </div>
          <PeriodPicker selection={selection} onChange={setSelection} minMonth={minMonth} />
        </div>
      </div>

      {/* KPI cards */}
      <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-5 gap-4 mb-6">
        <KpiCard
          label="Valorisation actuelle"
          value={positionsLoading ? null : currentValuation.toFixed(2)}
          currency={currency}
          color="blue"
          note={latestPricesArr.length === 0 ? 'Prix non disponibles' : undefined}
        />
        <KpiCard
          label="P&L (all-time)"
          value={tradesLoading || positionsLoading ? null : (portfolioPnl?.pnl ?? 0).toFixed(2)}
          currency={currency}
          color={portfolioPnl && portfolioPnl.pnl >= 0 ? 'emerald' : 'red'}
          note={portfolioPnl ? `${portfolioPnl.pnlPct >= 0 ? '+' : ''}${portfolioPnl.pnlPct.toFixed(2)}%` : undefined}
        />
        <KpiCard label="Investi (période)" value={tradesLoading ? null : kpis.invested} currency={currency} />
        <KpiCard label="Cédé (période)" value={tradesLoading ? null : kpis.proceeds} currency={currency} color="emerald" />
        <KpiCard label="Frais (période)" value={tradesLoading ? null : kpis.fees} currency={currency} color="red" />
      </div>

      {/* Évolution de la valeur */}
      <Section
        title="Évolution de la valeur"
        loading={snapshotsLoading}
        right={
          <button
            onClick={() => setShowSnapshotModal(true)}
            className="text-xs font-medium text-gray-500 hover:text-gray-900 transition-colors px-2.5 py-1 rounded-lg hover:bg-gray-100"
          >
            + Snapshot
          </button>
        }
      >
        {periodSnapshots.length >= 2
          ? <SnapshotChart snapshots={periodSnapshots} currency={currency} />
          : (
            <div className="flex flex-col items-center justify-center py-8 gap-3">
              <p className="text-sm text-gray-400">
                {snapshots.length === 0 ? 'Aucun snapshot enregistré' : 'Pas assez de snapshots sur cette période'}
              </p>
              <button
                onClick={() => setShowSnapshotModal(true)}
                className="text-xs text-gray-500 hover:text-gray-900 border border-gray-200 rounded-lg px-3 py-1.5 transition-colors"
              >
                Ajouter un snapshot
              </button>
            </div>
          )
        }
      </Section>

      {/* Performance P&L % vs benchmark */}
      {perfPoints.length >= 2 && (
        <Section
          title={`Performance${benchmarkInstrument ? ` · benchmark ${benchmarkInstrument.name || benchmarkSymbol}` : ''}`}
          loading={snapshotsLoading}
        >
          <PnlBenchmarkChart
            points={perfPoints}
            benchmarkLabel={benchmarkInstrument?.name || benchmarkSymbol || ''}
          />
        </Section>
      )}

      {/* Positions actuelles */}
      <Section title="Positions actuelles" loading={positionsLoading}>
        {enrichedPositions.length === 0 ? (
          <EmptyState label="Aucune position ouverte" />
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-xs">
              <thead>
                <tr className="border-b border-gray-100">
                  <th className="text-left text-gray-400 font-medium py-2 pr-4">Actif</th>
                  <th className="text-right text-gray-400 font-medium py-2 px-3">Quantité</th>
                  <th className="text-right text-gray-400 font-medium py-2 px-3">Cours actuel</th>
                  <th className="text-right text-gray-400 font-medium py-2 px-3">Valeur</th>
                  <th className="text-right text-gray-400 font-medium py-2 pl-3">P&L latent</th>
                </tr>
              </thead>
              <tbody>
                {enrichedPositions.map((p) => {
                  const barPct = ((p.currentValue ?? p.qty) / positionsMaxValue) * 100
                  return (
                    <tr key={p.instrument_symbol} className="border-b border-gray-50 hover:bg-gray-50 transition-colors">
                      <td className="py-2.5 pr-4">
                        <div className="font-medium text-gray-900 leading-tight">{instLabel(instruments, p.instrument_symbol)}</div>
                        <div className="text-[10px] text-gray-400 font-mono">{p.instrument_symbol}</div>
                        <div className="mt-1 h-1 w-24 bg-gray-100 rounded-full overflow-hidden">
                          <div className="h-full bg-gray-600 rounded-full" style={{ width: `${barPct}%` }} />
                        </div>
                      </td>
                      <td className="py-2.5 px-3 text-right text-gray-600 tabular-nums">{fmtQty(p.qty)}</td>
                      <td className="py-2.5 px-3 text-right tabular-nums">
                        {p.latestPrice !== null ? (
                          <div>
                            <div className="text-gray-700">{fmtPrice(p.latestPrice, currency)}</div>
                            {p.priceDate && <div className="text-[10px] text-gray-400">{p.priceDate}</div>}
                          </div>
                        ) : (
                          <span className="text-gray-400">—</span>
                        )}
                      </td>
                      <td className="py-2.5 px-3 text-right text-gray-900 font-semibold tabular-nums">
                        {p.currentValue !== null ? format(p.currentValue.toFixed(2), currency) : '—'}
                      </td>
                      <td className="py-2.5 pl-3 text-right tabular-nums">
                        {p.pnl !== null ? <PnlBadge value={p.pnl} currency={currency} /> : <span className="text-gray-400">—</span>}
                      </td>
                    </tr>
                  )
                })}
              </tbody>
              <tfoot>
                <tr className="border-t border-gray-200">
                  <td colSpan={3} className="pt-2.5 pr-4 text-gray-500 font-medium">Total</td>
                  <td className="pt-2.5 px-3 text-right text-gray-900 font-semibold tabular-nums">
                    {format(currentValuation.toFixed(2), currency)}
                  </td>
                  <td className="pt-2.5 pl-3 text-right">
                    <PnlBadge
                      value={enrichedPositions.reduce((s, p) => s + (p.pnl ?? 0), 0)}
                      currency={currency}
                    />
                  </td>
                </tr>
              </tfoot>
            </table>
          </div>
        )}
      </Section>

      {/* Analyse par instrument */}
      <Section title="Analyse par instrument (période)" loading={tradesLoading}>
        {instrumentStats.length === 0 ? (
          <EmptyState label="Aucun trade sur cette période" />
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-xs">
              <thead>
                <tr className="border-b border-gray-100">
                  <th className="text-left text-gray-400 font-medium py-2 pr-4">Symbole</th>
                  <th className="text-right text-gray-400 font-medium py-2 px-3">Qté achetée</th>
                  <th className="text-right text-gray-400 font-medium py-2 px-3">Montant investi</th>
                  <th className="text-right text-gray-400 font-medium py-2 px-3">Prix moy. achat</th>
                  <th className="text-right text-gray-400 font-medium py-2 px-3">Qté vendue</th>
                  <th className="text-right text-gray-400 font-medium py-2 px-3">Frais</th>
                  <th className="text-right text-gray-400 font-medium py-2 pl-3">Valeur actuelle</th>
                </tr>
              </thead>
              <tbody>
                {instrumentStats.map((s) => {
                  const pos = positions.find((p) => p.instrument_symbol === s.symbol)
                  const posQty = pos ? parseFloat(pos.quantity) : 0
                  const pp = latestPrices.get(s.symbol.toUpperCase())
                  const currentVal = pp && posQty !== 0 ? posQty * parseFloat(pp.price) : null
                  return (
                    <tr key={s.symbol} className="border-b border-gray-50 hover:bg-gray-50 transition-colors">
                      <td className="py-2 pr-4">
                        <div className="font-medium text-gray-900 leading-tight">{instLabel(instruments, s.symbol)}</div>
                        <div className="text-[10px] text-gray-400 font-mono">{s.symbol}</div>
                      </td>
                      <td className="py-2 px-3 text-right text-gray-600 tabular-nums">{fmtQty(s.buyQty)}</td>
                      <td className="py-2 px-3 text-right text-gray-700 tabular-nums font-medium">
                        {format(s.buyAmount.toFixed(2), currency)}
                      </td>
                      <td className="py-2 px-3 text-right text-gray-600 tabular-nums">
                        {s.buyQty > 0 ? format((s.buyAmount / s.buyQty).toFixed(4), currency) : '—'}
                      </td>
                      <td className="py-2 px-3 text-right text-gray-600 tabular-nums">
                        {s.sellQty > 0 ? fmtQty(s.sellQty) : '—'}
                      </td>
                      <td className="py-2 px-3 text-right text-red-500 tabular-nums">
                        {s.fees > 0 ? format(s.fees.toFixed(2), currency) : '—'}
                      </td>
                      <td className="py-2 pl-3 text-right tabular-nums">
                        {currentVal !== null
                          ? <span className="font-medium text-blue-700">{format(currentVal.toFixed(2), currency)}</span>
                          : <span className="text-gray-400">—</span>
                        }
                      </td>
                    </tr>
                  )
                })}
              </tbody>
              <tfoot>
                <tr className="border-t border-gray-200">
                  <td className="pt-2 pr-4 text-gray-500 font-medium">Total</td>
                  <td className="pt-2 px-3" />
                  <td className="pt-2 px-3 text-right text-gray-900 font-semibold tabular-nums">
                    {format(kpis.invested, currency)}
                  </td>
                  <td className="pt-2 px-3" />
                  <td className="pt-2 px-3" />
                  <td className="pt-2 px-3 text-right text-red-600 font-semibold tabular-nums">
                    {format(kpis.fees, currency)}
                  </td>
                  <td className="pt-2 pl-3 text-right text-blue-700 font-semibold tabular-nums">
                    {format(currentValuation.toFixed(2), currency)}
                  </td>
                </tr>
              </tfoot>
            </table>
          </div>
        )}
      </Section>

      {showSnapshotModal && (
        <AddSnapshotModal
          portfolioId={portfolioId}
          currency={currency}
          onClose={() => setShowSnapshotModal(false)}
        />
      )}
    </div>
  )
}
