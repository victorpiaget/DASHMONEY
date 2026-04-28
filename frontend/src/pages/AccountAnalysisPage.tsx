import { useState, useMemo } from 'react'
import { Link, useParams } from 'react-router-dom'
import { useAccounts, useAccountBalance } from '../hooks/useAccounts'
import { useAccountTimeSeries, useAccountBudgetSummary } from '../hooks/useAccountAnalysis'
import { useCurrency } from '../context/CurrencyContext'
import { useTheme } from '../context/ThemeContext'
import PeriodPicker, { type PeriodSelection, resolveDates } from '../components/PeriodPicker'
import type { TimeSeriesPoint } from '../lib/analysisApi'

// ── Bucket helpers ─────────────────────────────────────────────────────────────

function parseBucket(bucket: string): Date {
  if (/^\d{4}-\d{2}-\d{2}$/.test(bucket)) return new Date(bucket + 'T00:00:00')
  if (/^\d{4}-W\d{2}$/.test(bucket)) {
    const [yearStr, weekStr] = bucket.split('-W')
    const year = parseInt(yearStr), week = parseInt(weekStr)
    const jan4 = new Date(year, 0, 4)
    const dayOfWeek = jan4.getDay() || 7
    const monday = new Date(jan4)
    monday.setDate(jan4.getDate() - (dayOfWeek - 1) + (week - 1) * 7)
    return monday
  }
  if (/^\d{4}-\d{2}$/.test(bucket)) {
    const [y, m] = bucket.split('-')
    return new Date(parseInt(y), parseInt(m) - 1, 1)
  }
  if (/^\d{4}$/.test(bucket)) return new Date(parseInt(bucket), 0, 1)
  return new Date(bucket)
}

function formatBucketLabel(bucket: string): string {
  const d = parseBucket(bucket)
  if (/^\d{4}-\d{2}-\d{2}$/.test(bucket)) return d.toLocaleDateString('fr-FR', { day: '2-digit', month: 'short' })
  if (/^\d{4}-W\d{2}$/.test(bucket)) return d.toLocaleDateString('fr-FR', { day: '2-digit', month: 'short' })
  if (/^\d{4}-\d{2}$/.test(bucket)) return d.toLocaleDateString('fr-FR', { month: 'short', year: '2-digit' })
  return bucket
}

function formatBucketTooltip(bucket: string): string {
  const d = parseBucket(bucket)
  if (/^\d{4}-\d{2}-\d{2}$/.test(bucket)) return d.toLocaleDateString('fr-FR', { day: '2-digit', month: 'long', year: 'numeric' })
  if (/^\d{4}-W\d{2}$/.test(bucket)) return `Semaine ${bucket.split('-W')[1]} · ${d.toLocaleDateString('fr-FR', { day: '2-digit', month: 'short', year: 'numeric' })}`
  if (/^\d{4}-\d{2}$/.test(bucket)) return d.toLocaleDateString('fr-FR', { month: 'long', year: 'numeric' })
  return bucket
}

type Granularity = 'auto' | 'daily' | 'weekly' | 'monthly' | 'yearly'

const GRANULARITIES: { key: Granularity; label: string }[] = [
  { key: 'auto', label: 'Auto' },
  { key: 'daily', label: 'Jour' },
  { key: 'weekly', label: 'Sem.' },
  { key: 'monthly', label: 'Mois' },
  { key: 'yearly', label: 'An' },
]

// ── Balance Line Chart ─────────────────────────────────────────────────────────

function BalanceChart({ points, currency }: { points: TimeSeriesPoint[]; currency: string }) {
  const { format } = useCurrency()
  const { theme } = useTheme()
  const isDark = theme === 'dark'
  const lineColor = isDark ? '#e2e8f0' : '#111827'
  const gridColor = isDark ? '#334155' : '#f3f4f6'
  const [hovered, setHovered] = useState<number | null>(null)

  const W = 600, H = 320
  const pad = { top: 16, right: 12, bottom: 32, left: 68 }
  const innerW = W - pad.left - pad.right
  const innerH = H - pad.top - pad.bottom

  const values = points.map((p) => parseFloat(p.balance_end))
  const minV = Math.min(0, ...values)
  const maxV = Math.max(...values, 0)
  const range = maxV - minV || 1

  const toX = (i: number) => pad.left + (points.length === 1 ? innerW / 2 : (i / (points.length - 1)) * innerW)
  const toY = (v: number) => pad.top + (1 - (v - minV) / range) * innerH
  const zeroY = toY(0)

  const pathPts = points.map((p, i) => `${toX(i)},${toY(parseFloat(p.balance_end))}`)
  const linePath = 'M ' + pathPts.join(' L ')
  const areaPath = `${linePath} L ${toX(points.length - 1)} ${zeroY} L ${toX(0)} ${zeroY} Z`

  const yTicks = [0, 0.25, 0.5, 0.75, 1].map((t) => ({ y: pad.top + (1 - t) * innerH, val: minV + t * range }))
  const step = Math.max(1, Math.ceil((points.length - 1) / 5))
  const xTickIndices = [...new Set([
    ...Array.from({ length: points.length }, (_, i) => i).filter((i) => i % step === 0),
    points.length - 1,
  ])]

  const hoveredPoint = hovered !== null ? points[hovered] : null

  return (
    <div className="relative flex flex-col h-full">
      <svg
        viewBox={`0 0 ${W} ${H}`}
        preserveAspectRatio="xMidYMid meet"
        style={{ width: '100%', flex: 1, minHeight: 0 }}
        onMouseLeave={() => setHovered(null)}
      >
        <defs>
          <linearGradient id="balGrad" x1="0" y1="0" x2="0" y2="1">
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
        <path d={areaPath} fill="url(#balGrad)" />
        <path d={linePath} fill="none" stroke={lineColor} strokeWidth={1.5} strokeLinejoin="round" />
        {xTickIndices.map((idx) => (
          <text key={idx} x={toX(idx)} y={H - pad.bottom + 13} textAnchor="middle" fontSize={8.5} fill="#9ca3af">
            {formatBucketLabel(points[idx].bucket)}
          </text>
        ))}
        {points.map((_, i) => (
          <rect key={i} x={toX(i) - 8} y={pad.top} width={16} height={innerH} fill="transparent" onMouseEnter={() => setHovered(i)} />
        ))}
        {hovered !== null && (
          <>
            <line x1={toX(hovered)} y1={pad.top} x2={toX(hovered)} y2={H - pad.bottom} stroke={gridColor} strokeWidth={1} strokeDasharray="3,2" />
            <circle cx={toX(hovered)} cy={toY(parseFloat(points[hovered].balance_end))} r={3} fill={lineColor} />
          </>
        )}
      </svg>
      {hoveredPoint && (
        <div className="absolute top-1 left-1/2 -translate-x-1/2 bg-gray-900 text-white text-xs px-2.5 py-1.5 rounded-lg pointer-events-none whitespace-nowrap shadow-lg z-10">
          <span className="text-gray-400 mr-2">{formatBucketTooltip(hoveredPoint.bucket)}</span>
          {format(hoveredPoint.balance_end, currency)}
        </div>
      )}
    </div>
  )
}

// ── Monthly Bar Chart ──────────────────────────────────────────────────────────

interface MonthBar { label: string; income: number; expense: number }

function MonthlyChart({ bars, currency }: { bars: MonthBar[]; currency: string }) {
  const { format } = useCurrency()
  const [hovered, setHovered] = useState<number | null>(null)
  const maxVal = Math.max(...bars.flatMap((b) => [b.income, Math.abs(b.expense)]), 1)
  const BAR_H = 80
  const hov = hovered !== null ? bars[hovered] : null

  return (
    <div>
      <div className="flex items-center gap-6 mb-2 min-h-[20px]">
        <span className="flex items-center gap-1.5 text-xs">
          <span className="w-2.5 h-2.5 rounded-sm bg-emerald-400 inline-block flex-shrink-0" />
          {hov
            ? <span className="text-emerald-600 font-semibold tabular-nums">+{format(hov.income.toFixed(2), currency)}</span>
            : <span className="text-gray-500">Revenus</span>
          }
        </span>
        <span className="flex items-center gap-1.5 text-xs">
          <span className="w-2.5 h-2.5 rounded-sm bg-red-300 inline-block flex-shrink-0" />
          {hov
            ? <span className="text-red-500 font-semibold tabular-nums">{format(hov.expense.toFixed(2), currency)}</span>
            : <span className="text-gray-500">Dépenses</span>
          }
        </span>
        {hov && <span className="text-xs text-gray-400 ml-auto">{hov.label}</span>}
      </div>
      <div className="overflow-x-auto">
        <div className="flex items-end gap-1.5 min-w-max pb-1" style={{ height: BAR_H + 20 }}>
          {bars.map((b, i) => (
            <div
              key={i}
              className={`flex flex-col items-center gap-1 cursor-default transition-opacity ${hovered !== null && hovered !== i ? 'opacity-30' : 'opacity-100'}`}
              onMouseEnter={() => setHovered(i)}
              onMouseLeave={() => setHovered(null)}
            >
              <div className="flex items-end gap-0.5" style={{ height: BAR_H }}>
                <div className={`w-3.5 rounded-t transition-colors ${hovered === i ? 'bg-emerald-500' : 'bg-emerald-400'}`} style={{ height: `${(b.income / maxVal) * 100}%` }} />
                <div className={`w-3.5 rounded-t transition-colors ${hovered === i ? 'bg-red-400' : 'bg-red-300'}`} style={{ height: `${(Math.abs(b.expense) / maxVal) * 100}%` }} />
              </div>
              <span className={`text-[9px] whitespace-nowrap ${hovered === i ? 'text-gray-700 font-medium' : 'text-gray-400'}`}>{b.label}</span>
            </div>
          ))}
        </div>
      </div>
    </div>
  )
}

// ── Cashflow Panel ─────────────────────────────────────────────────────────────

function CashflowPanel({
  incomeByCategory, incomeBySubcategory, expenseByCategory, expenseBySubcategory, income, expense, currency,
}: {
  incomeByCategory: { category: string; total: string }[]
  incomeBySubcategory: { category: string; subcategory: string; total: string }[]
  expenseByCategory: { category: string; total: string }[]
  expenseBySubcategory: { category: string; subcategory: string; total: string }[]
  income: string
  expense: string
  currency: string
}) {
  const { format } = useCurrency()
  const [expanded, setExpanded] = useState<Set<string>>(new Set())

  const toggle = (cat: string) =>
    setExpanded((prev) => { const next = new Set(prev); next.has(cat) ? next.delete(cat) : next.add(cat); return next })

  const incomeSubsByCat = useMemo(() => {
    const map: Record<string, { subcategory: string; total: string }[]> = {}
    for (const s of incomeBySubcategory) {
      if (!map[s.category]) map[s.category] = []
      map[s.category].push({ subcategory: s.subcategory, total: s.total })
    }
    return map
  }, [incomeBySubcategory])

  const subsByCat = useMemo(() => {
    const map: Record<string, { subcategory: string; total: string }[]> = {}
    for (const s of expenseBySubcategory) {
      if (!map[s.category]) map[s.category] = []
      map[s.category].push({ subcategory: s.subcategory, total: s.total })
    }
    return map
  }, [expenseBySubcategory])

  const totalIn = parseFloat(income)
  const totalOut = Math.abs(parseFloat(expense))
  const net = totalIn - totalOut
  const maxIncome = Math.max(...incomeByCategory.map((d) => parseFloat(d.total)), 1)
  const maxExpense = Math.max(...expenseByCategory.map((d) => Math.abs(parseFloat(d.total))), 1)

  return (
    <div className="flex flex-col h-full gap-3">
      {/* Net flow bar */}
      <div className="flex-none">
        <div className="flex items-center justify-between mb-1.5">
          <span className="text-[10px] font-medium text-gray-400 uppercase tracking-wider">Cash flow net</span>
          <span className={`text-sm font-semibold tabular-nums ${net >= 0 ? 'text-emerald-600' : 'text-red-500'}`}>
            {net >= 0 ? '+' : ''}{format(net.toFixed(2), currency)}
          </span>
        </div>
        {(totalIn > 0 || totalOut > 0) && (
          <div className="h-2 rounded-full bg-gray-100 overflow-hidden flex">
            <div
              className="h-full bg-emerald-400 rounded-full transition-all"
              style={{ width: `${Math.min(100, (totalIn / Math.max(totalIn, totalOut)) * 100)}%` }}
            />
          </div>
        )}
        <div className="flex justify-between mt-1">
          <span className="text-[10px] text-emerald-600 tabular-nums">+{format(income, currency)}</span>
          <span className="text-[10px] text-red-500 tabular-nums">{format(expense, currency)}</span>
        </div>
      </div>

      <div className="flex-1 min-h-0 flex gap-3 overflow-hidden">
        {/* Revenus */}
        <div className="flex-1 min-w-0 flex flex-col gap-1 overflow-y-auto">
          <p className="text-[9px] font-semibold text-emerald-600 uppercase tracking-wider flex-none">Revenus</p>
          {incomeByCategory.length === 0 ? (
            <p className="text-[10px] text-gray-400 italic">Aucun revenu</p>
          ) : incomeByCategory.map((d) => {
            const pct = (parseFloat(d.total) / maxIncome) * 100
            const isExpanded = expanded.has('in_' + d.category)
            const subs = incomeSubsByCat[d.category] ?? []
            const hasSubs = subs.length > 0
            const subMax = Math.max(...subs.map((s) => parseFloat(s.total)), 1)
            return (
              <div key={d.category}>
                <div
                  className={`flex items-center gap-1.5 py-0.5 rounded transition-colors ${hasSubs ? 'cursor-pointer hover:bg-gray-50' : ''}`}
                  onClick={() => hasSubs && toggle('in_' + d.category)}
                >
                  {hasSubs && (
                    <span className={`text-[8px] text-gray-400 flex-shrink-0 transition-transform inline-block ${isExpanded ? 'rotate-90' : ''}`}>▶</span>
                  )}
                  <span className="text-[10px] text-gray-600 truncate w-20 flex-shrink-0">{d.category || '—'}</span>
                  <div className="flex-1 h-1.5 bg-gray-100 rounded-full overflow-hidden">
                    <div className="h-full bg-emerald-400 rounded-full" style={{ width: `${pct}%` }} />
                  </div>
                  <span className="text-[10px] text-gray-500 tabular-nums w-16 text-right flex-shrink-0">{format(d.total, currency)}</span>
                </div>
                {isExpanded && subs.length > 0 && (
                  <div className="ml-3 border-l border-gray-100 pl-2 space-y-0.5 mb-0.5">
                    {subs.map((s) => {
                      const sp = (parseFloat(s.total) / subMax) * 100
                      return (
                        <div key={s.subcategory} className="flex items-center gap-1.5 py-0.5">
                          <span className="text-[9px] text-gray-400 truncate w-20 flex-shrink-0">{s.subcategory || '—'}</span>
                          <div className="flex-1 h-1 bg-gray-100 rounded-full overflow-hidden">
                            <div className="h-full bg-emerald-300 rounded-full" style={{ width: `${sp}%` }} />
                          </div>
                          <span className="text-[9px] text-gray-400 tabular-nums w-16 text-right flex-shrink-0">{format(s.total, currency)}</span>
                        </div>
                      )
                    })}
                  </div>
                )}
              </div>
            )
          })}
        </div>

        {/* Séparateur */}
        <div className="w-px bg-gray-100 flex-none" />

        {/* Dépenses */}
        <div className="flex-1 min-w-0 flex flex-col gap-0.5 overflow-y-auto">
          <p className="text-[9px] font-semibold text-red-500 uppercase tracking-wider flex-none mb-0.5">Dépenses</p>
          {expenseByCategory.length === 0 ? (
            <p className="text-[10px] text-gray-400 italic">Aucune dépense</p>
          ) : expenseByCategory.map((d) => {
            const pct = (Math.abs(parseFloat(d.total)) / maxExpense) * 100
            const isExpanded = expanded.has(d.category)
            const subs = subsByCat[d.category] ?? []
            const hasSubs = subs.length > 0
            const subMax = Math.max(...subs.map((s) => Math.abs(parseFloat(s.total))), 1)
            return (
              <div key={d.category}>
                <div
                  className={`flex items-center gap-1.5 py-0.5 rounded transition-colors ${hasSubs ? 'cursor-pointer hover:bg-gray-50' : ''}`}
                  onClick={() => hasSubs && toggle(d.category)}
                >
                  {hasSubs && (
                    <span className={`text-[8px] text-gray-400 flex-shrink-0 transition-transform inline-block ${isExpanded ? 'rotate-90' : ''}`}>▶</span>
                  )}
                  <span className="text-[10px] text-gray-600 truncate w-20 flex-shrink-0">{d.category || '—'}</span>
                  <div className="flex-1 h-1.5 bg-gray-100 rounded-full overflow-hidden">
                    <div className="h-full bg-red-400 rounded-full" style={{ width: `${pct}%` }} />
                  </div>
                  <span className="text-[10px] text-gray-500 tabular-nums w-16 text-right flex-shrink-0">{format(d.total, currency)}</span>
                </div>
                {isExpanded && subs.length > 0 && (
                  <div className="ml-3 border-l border-gray-100 pl-2 space-y-0.5 mb-0.5">
                    {subs.map((s) => {
                      const sp = (Math.abs(parseFloat(s.total)) / subMax) * 100
                      return (
                        <div key={s.subcategory} className="flex items-center gap-1.5 py-0.5">
                          <span className="text-[9px] text-gray-400 truncate w-20 flex-shrink-0">{s.subcategory || '—'}</span>
                          <div className="flex-1 h-1 bg-gray-100 rounded-full overflow-hidden">
                            <div className="h-full bg-red-300 rounded-full" style={{ width: `${sp}%` }} />
                          </div>
                          <span className="text-[9px] text-gray-400 tabular-nums w-16 text-right flex-shrink-0">{format(s.total, currency)}</span>
                        </div>
                      )
                    })}
                  </div>
                )}
              </div>
            )
          })}
        </div>
      </div>
    </div>
  )
}

// ── Segmented Control ──────────────────────────────────────────────────────────

function SegmentedControl<T extends string>({ options, value, onChange }: {
  options: { key: T; label: string }[]; value: T; onChange: (v: T) => void
}) {
  return (
    <div className="flex items-center gap-0.5 bg-gray-100 rounded-lg p-0.5">
      {options.map((o) => (
        <button
          key={o.key}
          onClick={() => onChange(o.key)}
          className={`px-2 py-1 text-xs font-medium rounded-md transition-colors ${value === o.key ? 'bg-white text-gray-900 shadow-sm' : 'text-gray-500 hover:text-gray-700'}`}
        >
          {o.label}
        </button>
      ))}
    </div>
  )
}

// ── Page ──────────────────────────────────────────────────────────────────────

export default function AccountAnalysisPage() {
  const { id } = useParams<{ id: string }>()
  const { data: accounts = [] } = useAccounts()
  const account = accounts.find((a) => a.id === id)
  const { data: balanceData } = useAccountBalance(id ?? '')

  const [selection, setSelection] = useState<PeriodSelection>({ type: 'preset', preset: '6M' })
  const [granularity, setGranularity] = useState<Granularity>('auto')

  const dates = useMemo(() => {
    if (!account) return null
    return resolveDates(selection, account.opened_on)
  }, [selection, account])

  const { data: timeseries, isLoading: tsLoading } = useAccountTimeSeries(
    id ?? '', dates?.from ?? '', dates?.to ?? '', granularity,
  )
  const { data: budget, isLoading: budgetLoading } = useAccountBudgetSummary(
    id ?? '', dates?.from, dates?.to,
  )

  const currency = account?.currency ?? 'EUR'
  const { format } = useCurrency()

  const income = budget?.totals_by_kind.find((k) => k.kind === 'INCOME')?.total ?? '0'
  const expense = budget?.totals_by_kind.find((k) => k.kind === 'EXPENSE')?.total ?? '0'
  const netFlow = (parseFloat(income) + parseFloat(expense)).toFixed(2) // expense is negative

  const monthlyBars = useMemo((): MonthBar[] => {
    if (!budget) return []
    const map: Record<string, MonthBar> = {}
    for (const m of budget.monthly_by_kind) {
      const key = `${m.year}-${String(m.month).padStart(2, '0')}`
      if (!map[key]) map[key] = { label: new Date(m.year, m.month - 1, 1).toLocaleDateString('fr-FR', { month: 'short', year: '2-digit' }), income: 0, expense: 0 }
      if (m.kind === 'INCOME') map[key].income += parseFloat(m.total)
      else if (m.kind === 'EXPENSE') map[key].expense += parseFloat(m.total)
    }
    return Object.entries(map).sort(([a], [b]) => a.localeCompare(b)).map(([, v]) => v)
  }, [budget])

  const minMonth = `${new Date().getFullYear() - 10}-01`

  return (
    <div className="h-full flex flex-col p-6 gap-4 overflow-hidden">

      {/* Header */}
      <div className="flex-none flex items-center justify-between gap-4 flex-wrap">
        <div className="flex items-center gap-3">
          <Link to={`/accounts/${id}`} className="text-xs text-gray-400 hover:text-gray-700 transition-colors">
            ←
          </Link>
          <div>
            <h1 className="text-xl font-semibold text-gray-900">{account?.name ?? '…'}</h1>
            <p className="text-xs text-gray-400">Analyse · {currency}</p>
          </div>
        </div>
        <div className="flex items-center gap-3">
          <SegmentedControl options={GRANULARITIES} value={granularity} onChange={setGranularity} />
          <PeriodPicker selection={selection} onChange={setSelection} minMonth={minMonth} />
        </div>
      </div>

      {/* KPI row */}
      <div className="flex-none grid grid-cols-4 gap-3">
        {[
          { label: 'Solde actuel', value: balanceData ? format(balanceData.balance, currency) : null, color: 'text-gray-900' },
          { label: 'Revenus (période)', value: budget ? format(income, currency) : null, color: 'text-emerald-600' },
          { label: 'Dépenses (période)', value: budget ? format(expense, currency) : null, color: 'text-red-600' },
          { label: 'Cash flow net', value: budget ? format(netFlow, currency) : null, color: parseFloat(netFlow) >= 0 ? 'text-gray-900' : 'text-red-600' },
        ].map(({ label, value, color }) => (
          <div key={label} className="rounded-xl border border-gray-100 px-5 py-4 hover:shadow-sm transition-shadow">
            <p className="text-[10px] font-medium text-gray-400 uppercase tracking-wider">{label}</p>
            {value !== null
              ? <p className={`text-lg font-semibold tabular-nums mt-1 ${color}`}>{value}</p>
              : <div className="h-6 w-24 bg-gray-100 rounded animate-pulse mt-1" />
            }
          </div>
        ))}
      </div>

      {/* Main grid */}
      <div className="flex-1 min-h-0 grid grid-cols-5 gap-4">

        {/* Left — charts */}
        <div className="col-span-3 flex flex-col gap-4 min-h-0">

          {/* Évolution du solde */}
          <div className="flex-1 min-h-0 rounded-xl border border-gray-100 p-4 flex flex-col">
            <p className="text-[10px] font-medium text-gray-400 uppercase tracking-wider mb-2 flex-none">
              Évolution du solde
            </p>
            <div className="flex-1 min-h-0">
              {tsLoading ? (
                <div className="h-full bg-gray-50 rounded-xl animate-pulse" />
              ) : timeseries && timeseries.points.length > 1 ? (
                <BalanceChart points={timeseries.points} currency={currency} />
              ) : (
                <div className="flex items-center justify-center h-full text-sm text-gray-400">
                  Pas assez de données sur cette période
                </div>
              )}
            </div>
          </div>

          {/* Revenus & dépenses par mois */}
          <div className="flex-none rounded-xl border border-gray-100 p-4">
            <p className="text-[10px] font-medium text-gray-400 uppercase tracking-wider mb-2">
              Revenus & dépenses par mois
            </p>
            {budgetLoading ? (
              <div className="h-24 bg-gray-50 rounded-xl animate-pulse" />
            ) : monthlyBars.length > 0 ? (
              <MonthlyChart bars={monthlyBars} currency={currency} />
            ) : (
              <div className="flex items-center justify-center h-20 text-sm text-gray-400">
                Aucune transaction sur cette période
              </div>
            )}
          </div>

        </div>

        {/* Right — cashflow */}
        <div className="col-span-2 rounded-xl border border-gray-100 p-4 flex flex-col min-h-0">
          {budgetLoading ? (
            <div className="space-y-2">
              {[1, 2, 3, 4, 5].map((i) => <div key={i} className="h-8 bg-gray-50 rounded-lg animate-pulse" />)}
            </div>
          ) : budget ? (
            <CashflowPanel
              incomeByCategory={budget.income_by_category ?? []}
              incomeBySubcategory={budget.income_by_subcategory ?? []}
              expenseByCategory={budget.expense_by_category}
              expenseBySubcategory={budget.expense_by_subcategory}
              income={income}
              expense={expense}
              currency={currency}
            />
          ) : (
            <div className="flex items-center justify-center h-full text-sm text-gray-400">
              Aucune donnée sur cette période
            </div>
          )}
        </div>

      </div>
    </div>
  )
}
