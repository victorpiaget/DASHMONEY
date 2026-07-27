import { useState, useMemo } from 'react'
import { Link } from 'react-router-dom'
import { usePortfoliosCompare } from '../hooks/usePortfolios'
import { useCurrency } from '../context/CurrencyContext'
import PeriodPicker from '../components/PeriodPicker'
import { type PeriodSelection, resolveDates } from '../lib/period'

// ── Couleurs par portefeuille ───────────────────────────────────────────────

const PALETTE = [
  '#111827', '#3b82f6', '#10b981', '#f59e0b',
  '#ef4444', '#8b5cf6', '#ec4899', '#06b6d4',
]

const TYPE_LABELS: Record<string, string> = {
  PEA: 'PEA', CTO: 'CTO', CRYPTO_EXCHANGE: 'Crypto', WALLET: 'Wallet', OTHER: 'Autre',
}

// ── Graphique multi-lignes ──────────────────────────────────────────────────

interface ChartPoint { date: string; value: number }
interface Series { id: string; name: string; color: string; points: ChartPoint[] }

function CompareChart({ series, mode }: { series: Series[]; mode: 'value' | 'pnl' | 'pnl_pct' }) {
  const { format } = useCurrency()
  const [hoveredDate, setHoveredDate] = useState<string | null>(null)

  const W = 600, H = 320
  const pad = { top: 16, right: 16, bottom: 32, left: 72 }
  const innerW = W - pad.left - pad.right
  const innerH = H - pad.top - pad.bottom

  const allDates = useMemo(() => {
    const s = new Set<string>()
    series.forEach((sr) => sr.points.forEach((p) => s.add(p.date)))
    return [...s].sort()
  }, [series])

  if (allDates.length === 0 || series.length === 0) {
    return (
      <div className="flex flex-col items-center justify-center h-full gap-2 text-gray-300">
        <span className="text-4xl">◎</span>
        <p className="text-sm">Pas de snapshots sur cette période</p>
      </div>
    )
  }

  const allValues = series.flatMap((sr) => sr.points.map((p) => p.value))
  const minV = Math.min(...allValues)
  const maxV = Math.max(...allValues)
  const range = maxV - minV || 1

  const toX = (dateStr: string) => {
    const idx = allDates.indexOf(dateStr)
    return pad.left + (allDates.length === 1 ? innerW / 2 : (idx / (allDates.length - 1)) * innerW)
  }
  const toY = (v: number) => pad.top + (1 - (v - minV) / range) * innerH

  const yTicks = [0, 0.5, 1].map((t) => ({ y: pad.top + (1 - t) * innerH, val: minV + t * range }))
  const step = Math.max(1, Math.ceil((allDates.length - 1) / 5))
  const xTickDates = allDates.filter((_, i) => i % step === 0 || i === allDates.length - 1)
  const fmtDate = (d: string) => new Date(d + 'T00:00:00').toLocaleDateString('fr-FR', { day: '2-digit', month: 'short', year: '2-digit' })

  const handleMouseMove = (e: React.MouseEvent<SVGSVGElement>) => {
    const rect = e.currentTarget.getBoundingClientRect()
    const svgX = ((e.clientX - rect.left) / rect.width) * W
    let closest = allDates[0]
    let minDist = Infinity
    for (const d of allDates) {
      const dist = Math.abs(toX(d) - svgX)
      if (dist < minDist) { minDist = dist; closest = d }
    }
    setHoveredDate(closest)
  }

  // Pour chaque série, valeur à la date la plus proche de hoveredDate
  const hovData = hoveredDate
    ? series.map((sr) => {
        const pt = sr.points.find((p) => p.date === hoveredDate)
          ?? [...sr.points].sort((a, b) => Math.abs(new Date(a.date).getTime() - new Date(hoveredDate).getTime()) - Math.abs(new Date(b.date).getTime() - new Date(hoveredDate).getTime()))[0]
        return { series: sr, pt }
      }).filter((d) => d.pt !== undefined)
    : []

  const fmtVal = (v: number) =>
    mode === 'pnl_pct'
      ? `${v >= 0 ? '+' : ''}${v.toFixed(2)}%`
      : `${v >= 0 && mode === 'pnl' ? '+' : ''}${format(v.toFixed(2), 'EUR')}`

  const crosshairX = hoveredDate ? toX(hoveredDate) : null

  return (
    <div className="relative flex flex-col h-full">
      <svg
        viewBox={`0 0 ${W} ${H}`}
        preserveAspectRatio="xMidYMid meet"
        style={{ width: '100%', flex: 1, minHeight: 0, cursor: 'crosshair' }}
        onMouseMove={handleMouseMove}
        onMouseLeave={() => setHoveredDate(null)}
      >
        {/* Grille Y */}
        {yTicks.map((t, i) => (
          <g key={i}>
            <line x1={pad.left} y1={t.y} x2={W - pad.right} y2={t.y} stroke="#f3f4f6" strokeWidth={1} />
            <text x={pad.left - 5} y={t.y} textAnchor="end" dominantBaseline="middle" fontSize={8.5} fill="#9ca3af">
              {mode === 'pnl_pct'
                ? `${t.val.toFixed(1)}%`
                : new Intl.NumberFormat('fr-FR', { notation: 'compact', maximumFractionDigits: 1 }).format(t.val)}
            </text>
          </g>
        ))}

        {/* Labels X */}
        {xTickDates.map((d) => (
          <text key={d} x={toX(d)} y={H - pad.bottom + 12} textAnchor="middle" fontSize={8} fill="#9ca3af">
            {fmtDate(d)}
          </text>
        ))}

        {/* Lignes */}
        {series.map((sr) => {
          if (sr.points.length === 0) return null
          const pts = sr.points.map((p) => `${toX(p.date)},${toY(p.value)}`).join(' L ')
          return (
            <path key={sr.id} d={`M ${pts}`} fill="none" stroke={sr.color}
              strokeWidth={hoveredDate ? 1.5 : 2} strokeLinejoin="round" />
          )
        })}

        {/* Crosshair vertical */}
        {crosshairX !== null && (
          <line x1={crosshairX} y1={pad.top} x2={crosshairX} y2={H - pad.bottom}
            stroke="#d1d5db" strokeWidth={1} strokeDasharray="3 3" />
        )}

        {/* Dots sur chaque série à la date survolée */}
        {hovData.map(({ series: sr, pt }) => pt && (
          <circle key={sr.id} cx={toX(pt.date)} cy={toY(pt.value)}
            r={4} fill={sr.color} stroke="white" strokeWidth={1.5} />
        ))}
      </svg>

      {/* Tooltip partagé */}
      {hoveredDate && hovData.length > 0 && (
        <div className="absolute top-2 left-1/2 -translate-x-1/2 bg-gray-900 text-white rounded-xl shadow-lg px-4 py-3 text-xs pointer-events-none z-10 min-w-[180px]">
          <p className="text-gray-400 text-center mb-2 font-medium">{fmtDate(hoveredDate)}</p>
          <div className="space-y-1.5">
            {hovData.map(({ series: sr, pt }) => pt && (
              <div key={sr.id} className="flex items-center justify-between gap-4">
                <div className="flex items-center gap-1.5">
                  <span className="w-2 h-2 rounded-full flex-shrink-0" style={{ backgroundColor: sr.color }} />
                  <span className="text-gray-300 truncate max-w-[80px]">{sr.name}</span>
                </div>
                <span className={`font-semibold tabular-nums ${
                  mode !== 'value' ? (pt.value >= 0 ? 'text-emerald-400' : 'text-red-400') : 'text-white'
                }`}>
                  {fmtVal(pt.value)}
                </span>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Légende */}
      <div className="flex flex-wrap gap-x-4 gap-y-1 mt-2 px-1">
        {series.map((sr) => (
          <div key={sr.id} className="flex items-center gap-1.5">
            <span className="w-3 h-0.5 rounded-full inline-block" style={{ backgroundColor: sr.color }} />
            <span className="text-[10px] text-gray-500">{sr.name}</span>
          </div>
        ))}
      </div>
    </div>
  )
}

// ── Page ───────────────────────────────────────────────────────────────────

export default function PortfoliosComparePage() {
  const { format, convert } = useCurrency()
  const [period, setPeriod] = useState<PeriodSelection>({ type: 'preset', preset: 'tout' })
  const [chartView, setChartView] = useState<'value' | 'pnl' | 'pnl_pct'>('value')

  const minMonth = `${new Date().getFullYear() - 10}-01`
  const dates = useMemo(() => resolveDates(period, `${minMonth}-01`), [period, minMonth])

  const { data: items = [], isLoading } = usePortfoliosCompare({
    date_from: dates.from,
    date_to: dates.to,
  })

  // Séries pour le graphique (conversion en devise d'affichage)
  const series: Series[] = useMemo(() =>
    items.map((item, i) => ({
      id: item.portfolio_id,
      name: item.portfolio_name,
      color: PALETTE[i % PALETTE.length],
      points: item.snapshots.map((s) => ({
        date: typeof s.date === 'string' ? s.date : String(s.date),
        value: chartView === 'value'
          ? convert(s.value, item.currency)
          : chartView === 'pnl'
            ? convert(s.pnl, item.currency)
            : s.net_invested > 0 ? (s.pnl / s.net_invested) * 100 : 0,
      })),
    })),
    [items, convert, chartView]
  )

  // KPIs totaux (convertis en devise d'affichage)
  const totals = useMemo(() => {
    let totalValue = 0, totalInvested = 0
    for (const item of items) {
      totalValue += convert(item.current_value, item.currency)
      totalInvested += convert(item.net_invested, item.currency)
    }
    const pnl = totalValue - totalInvested
    const pnlPct = totalInvested > 0 ? (pnl / totalInvested) * 100 : 0
    return { totalValue, totalInvested, pnl, pnlPct }
  }, [items, convert])

  return (
    <div className="h-full flex flex-col p-6 gap-4 overflow-hidden">

      {/* Header */}
      <div className="flex-none flex items-center justify-between gap-4">
        <div>
          <div className="flex items-center gap-2">
            <Link to="/portfolios" className="text-xs text-gray-400 hover:text-gray-700 transition-colors">
              ← Portefeuilles
            </Link>
          </div>
          <h1 className="text-xl font-semibold text-gray-900 mt-0.5">Comparaison des portefeuilles</h1>
        </div>
        <PeriodPicker selection={period} onChange={setPeriod} minMonth={minMonth} />
      </div>

      {/* KPI row */}
      <div className="flex-none grid grid-cols-4 gap-3">
        {[
          { label: 'Valeur totale', value: format(totals.totalValue.toFixed(2), 'EUR'), color: 'text-gray-900' },
          { label: 'Net investi', value: format(totals.totalInvested.toFixed(2), 'EUR'), color: 'text-gray-700' },
          { label: 'P&L total', value: (totals.pnl >= 0 ? '+' : '') + format(totals.pnl.toFixed(2), 'EUR'), color: totals.pnl >= 0 ? 'text-emerald-600' : 'text-red-600' },
          { label: 'Performance', value: (totals.pnlPct >= 0 ? '+' : '') + totals.pnlPct.toFixed(2) + '%', color: totals.pnlPct >= 0 ? 'text-emerald-600' : 'text-red-600' },
        ].map(({ label, value, color }) => (
          <div key={label} className="rounded-xl border border-gray-100 px-5 py-4 hover:shadow-sm transition-shadow">
            <p className="text-[10px] font-medium text-gray-400 uppercase tracking-wider">{label}</p>
            <p className={`text-[22px] font-semibold tabular-nums tracking-tight mt-2 ${color}`}>
              {isLoading ? '—' : value}
            </p>
          </div>
        ))}
      </div>

      {/* Main grid */}
      <div className="flex-1 min-h-0 grid grid-cols-5 gap-4">

        {/* Graphique multi-lignes */}
        <div className="col-span-3 rounded-xl border border-gray-100 p-4 flex flex-col min-h-0">
          <div className="flex-none flex items-center justify-between mb-3">
            <p className="text-xs font-medium text-gray-500">
              {chartView === 'value' ? 'Évolution de la valeur' : chartView === 'pnl' ? 'Évolution du P&L (€)' : 'Évolution du P&L (%)'}
            </p>
            <div className="flex items-center gap-1 bg-gray-100 rounded-lg p-0.5">
              {([['value', 'Valeur'], ['pnl', 'P&L €'], ['pnl_pct', 'P&L %']] as const).map(([key, label]) => (
                <button
                  key={key}
                  onClick={() => setChartView(key)}
                  className={`px-2.5 py-1 text-xs font-medium rounded-md transition-colors ${
                    chartView === key ? 'bg-white text-gray-900 shadow-sm' : 'text-gray-500 hover:text-gray-700'
                  }`}
                >
                  {label}
                </button>
              ))}
            </div>
          </div>
          <div className="flex-1 min-h-0">
            {isLoading ? (
              <div className="flex items-center justify-center h-full">
                <div className="w-5 h-5 border-2 border-gray-200 border-t-gray-700 rounded-full animate-spin" />
              </div>
            ) : (
              <CompareChart series={series} mode={chartView} />
            )}
          </div>
        </div>

        {/* Tableau comparatif */}
        <div className="col-span-2 rounded-xl border border-gray-100 flex flex-col overflow-hidden min-h-0">
          <div className="flex-none px-4 py-3 border-b border-gray-50">
            <p className="text-xs font-medium text-gray-500">Récapitulatif</p>
          </div>

          <div className="flex-1 overflow-y-auto">
            {isLoading ? (
              <div className="flex items-center justify-center h-full">
                <div className="w-5 h-5 border-2 border-gray-200 border-t-gray-700 rounded-full animate-spin" />
              </div>
            ) : items.length === 0 ? (
              <div className="flex flex-col items-center justify-center h-full gap-2 text-gray-300">
                <span className="text-3xl">◎</span>
                <p className="text-xs">Aucun portefeuille avec des snapshots</p>
              </div>
            ) : (
              <table className="w-full text-xs divide-y divide-gray-50">
                <thead className="sticky top-0 bg-gray-50 border-b border-gray-50">
                  <tr>
                    <th className="text-left text-[10px] uppercase tracking-wider text-gray-400 font-medium py-2.5 px-4">Portefeuille</th>
                    <th className="text-right text-[10px] uppercase tracking-wider text-gray-400 font-medium py-2.5 px-3">Valeur</th>
                    <th className="text-right text-[10px] uppercase tracking-wider text-gray-400 font-medium py-2.5 px-4">P&L</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-gray-50">
                  {items.map((item, i) => {
                    const val = convert(item.current_value, item.currency)
                    const inv = convert(item.net_invested, item.currency)
                    const pnl = val - inv
                    const pnlPct = inv > 0 ? (pnl / inv) * 100 : 0
                    const color = PALETTE[i % PALETTE.length]
                    return (
                      <tr key={item.portfolio_id} className="hover:bg-gray-50 transition-colors">
                        <td className="py-3 px-4">
                          <div className="flex items-center gap-2">
                            <span className="w-2 h-2 rounded-full flex-shrink-0" style={{ backgroundColor: color }} />
                            <div>
                              <Link
                                to={`/portfolios/${item.portfolio_id}/analyse`}
                                className="font-medium text-gray-800 hover:text-gray-900 hover:underline block leading-tight"
                              >
                                {item.portfolio_name}
                              </Link>
                              <span className="text-[10px] text-gray-400">{TYPE_LABELS[item.portfolio_type] ?? item.portfolio_type}</span>
                            </div>
                          </div>
                        </td>
                        <td className="py-3 px-3 text-right tabular-nums text-gray-700 font-medium">
                          {format(val.toFixed(2), 'EUR')}
                        </td>
                        <td className="py-3 px-4 text-right tabular-nums">
                          <span className={pnl >= 0 ? 'text-emerald-600' : 'text-red-600'}>
                            {pnl >= 0 ? '+' : ''}{format(pnl.toFixed(2), 'EUR')}
                          </span>
                          <span className={`block text-[10px] ${pnlPct >= 0 ? 'text-emerald-500' : 'text-red-500'}`}>
                            {pnlPct >= 0 ? '+' : ''}{pnlPct.toFixed(2)}%
                          </span>
                        </td>
                      </tr>
                    )
                  })}
                </tbody>
                <tfoot className="sticky bottom-0 bg-gray-50 border-t border-gray-100">
                  <tr>
                    <td className="py-3 px-4 font-semibold text-gray-900">Total</td>
                    <td className="py-3 px-3 text-right tabular-nums font-semibold text-gray-900">
                      {format(totals.totalValue.toFixed(2), 'EUR')}
                    </td>
                    <td className="py-3 px-4 text-right tabular-nums">
                      <span className={`font-semibold ${totals.pnl >= 0 ? 'text-emerald-600' : 'text-red-600'}`}>
                        {totals.pnl >= 0 ? '+' : ''}{format(totals.pnl.toFixed(2), 'EUR')}
                      </span>
                      <span className={`block text-[10px] font-medium ${totals.pnlPct >= 0 ? 'text-emerald-500' : 'text-red-500'}`}>
                        {totals.pnlPct >= 0 ? '+' : ''}{totals.pnlPct.toFixed(2)}%
                      </span>
                    </td>
                  </tr>
                </tfoot>
              </table>
            )}
          </div>
        </div>
      </div>
    </div>
  )
}
