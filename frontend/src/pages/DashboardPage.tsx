import { useState, useMemo } from 'react'
import { useNetWorthGrouped, useCashFlow, useNetWorthFullTimeseries, useNetWorthGroupedTimeseries } from '../hooks/useNetWorth'
import { usePnlCurve } from '../hooks/usePortfolios'
import { useCurrency } from '../context/CurrencyContext'
import { useTheme } from '../context/ThemeContext'
import PeriodPicker, { resolveDates, type PeriodSelection } from '../components/PeriodPicker'
import type { PnlPoint } from '../lib/portfoliosApi'
import type { NetWorthFullTimeseriesPoint, NetWorthGroupedTimeseriesGroup } from '../lib/netWorthApi'

const NW_TYPE_LABELS: Record<string, string> = {
  CHECKING: 'Courant', SAVINGS: 'Épargne', INVESTMENT: 'Investissement', OTHER: 'Autre',
}

// ── KPI Card ──────────────────────────────────────────────────────────────────

function KpiCard({
  label, value, sub, positive, loading,
}: { label: string; value: string; sub?: string; positive?: boolean; loading?: boolean }) {
  return (
    <div className="bg-white rounded-xl border border-gray-100 shadow-sm px-5 py-4 flex flex-col justify-between">
      <p className="text-[10px] font-medium text-gray-400 uppercase tracking-wider">{label}</p>
      {loading ? (
        <div className="h-7 w-28 bg-gray-100 rounded-md animate-pulse mt-2" />
      ) : (
        <p className={`text-xl font-semibold tabular-nums mt-1.5 ${
          positive === undefined ? 'text-gray-900' : positive ? 'text-emerald-600' : 'text-red-600'
        }`}>
          {value}
        </p>
      )}
      {sub && !loading && (
        <p className="text-[10px] text-gray-400 mt-1 tabular-nums">{sub}</p>
      )}
    </div>
  )
}

// ── Donut Chart ───────────────────────────────────────────────────────────────

const DONUT_COLORS_LIGHT = ['#111827', '#374151', '#6b7280', '#9ca3af', '#d1d5db', '#4b5563']
const DONUT_COLORS_DARK  = ['#f1f5f9', '#cbd5e1', '#94a3b8', '#64748b', '#475569', '#e2e8f0']

interface DonutSlice { key: string; value: number; label: string }

function DonutChart({ slices }: { slices: DonutSlice[] }) {
  const { format } = useCurrency()
  const { theme } = useTheme()
  const isDark = theme === 'dark'
  const DONUT_COLORS = isDark ? DONUT_COLORS_DARK : DONUT_COLORS_LIGHT
  const [hovered, setHovered] = useState<string | null>(null)

  const total = slices.reduce((s, d) => s + d.value, 0)
  if (total <= 0) {
    return (
      <div className="flex flex-col items-center justify-center h-full text-sm text-gray-400 gap-2">
        <span className="text-3xl opacity-20">◎</span>
        Aucune donnée
      </div>
    )
  }

  const R = 72, cx = 90, cy = 90, stroke = 26
  let cumAngle = -Math.PI / 2

  const arcs = slices.map((s, i) => {
    const angle = (s.value / total) * 2 * Math.PI
    const startAngle = cumAngle
    cumAngle += angle
    const endAngle = cumAngle
    const x1 = cx + R * Math.cos(startAngle)
    const y1 = cy + R * Math.sin(startAngle)
    const x2 = cx + R * Math.cos(endAngle)
    const y2 = cy + R * Math.sin(endAngle)
    const large = angle > Math.PI ? 1 : 0
    return {
      ...s,
      path: `M ${x1} ${y1} A ${R} ${R} 0 ${large} 1 ${x2} ${y2}`,
      color: DONUT_COLORS[i % DONUT_COLORS.length],
      pct: (s.value / total) * 100,
    }
  })

  const hov = arcs.find((a) => a.key === hovered)

  return (
    <div className="flex items-center gap-5 h-full">
      <div className="flex-shrink-0">
        <svg viewBox="0 0 180 180" width={160} height={160}>
          {arcs.map((a) => (
            <path
              key={a.key}
              d={a.path}
              fill="none"
              stroke={a.color}
              strokeWidth={hovered === a.key ? stroke + 5 : stroke}
              strokeLinecap="butt"
              onMouseEnter={() => setHovered(a.key)}
              onMouseLeave={() => setHovered(null)}
              style={{ cursor: 'pointer', transition: 'stroke-width 0.12s' }}
            />
          ))}
          <text x={cx} y={cy - 10} textAnchor="middle" fontSize={9} fill="#9ca3af">
            {hov ? hov.label : 'Total'}
          </text>
          <text x={cx} y={cy + 8} textAnchor="middle" fontSize={14} fontWeight={700} fill={isDark ? '#f1f5f9' : '#111827'}>
            {hov ? `${hov.pct.toFixed(1)}%` : '100%'}
          </text>
          {hov && (
            <text x={cx} y={cy + 24} textAnchor="middle" fontSize={8} fill="#6b7280">
              {format(hov.value.toFixed(2), 'EUR')}
            </text>
          )}
        </svg>
      </div>

      <div className="flex flex-col gap-2.5 min-w-0 flex-1">
        {arcs.map((a) => (
          <div
            key={a.key}
            className="flex items-center gap-2.5 cursor-pointer group"
            onMouseEnter={() => setHovered(a.key)}
            onMouseLeave={() => setHovered(null)}
          >
            <div
              className="w-2 h-2 rounded-full flex-shrink-0 transition-transform group-hover:scale-125"
              style={{ background: a.color }}
            />
            <div className="min-w-0 flex-1">
              <div className="flex items-center justify-between gap-2">
                <p className="text-xs text-gray-500 truncate">{a.label}</p>
                <p className="text-xs font-medium text-gray-900 tabular-nums flex-shrink-0">
                  {a.pct.toFixed(0)}%
                </p>
              </div>
              <p className="text-[10px] text-gray-400 tabular-nums">{format(a.value.toFixed(2), 'EUR')}</p>
            </div>
          </div>
        ))}
      </div>
    </div>
  )
}

// ── PnL Chart ─────────────────────────────────────────────────────────────────

function PnlChart({ data }: { data: PnlPoint[] }) {
  const { format } = useCurrency()
  const { theme } = useTheme()
  const isDark = theme === 'dark'
  const lineColor = isDark ? '#e2e8f0' : '#111827'
  const gridColor = isDark ? '#334155' : '#f3f4f6'
  const [hovered, setHovered] = useState<number | null>(null)

  const sorted = useMemo(() => [...data].sort((a, b) => a.date.localeCompare(b.date)), [data])

  const W = 700, H = 220
  const pad = { top: 16, right: 12, bottom: 28, left: 72 }
  const innerW = W - pad.left - pad.right
  const innerH = H - pad.top - pad.bottom

  const allValues = sorted.flatMap((p) => [p.portfolio_value, p.net_invested])
  const minV = Math.min(...allValues)
  const maxV = Math.max(...allValues)
  const range = maxV - minV || 1

  const toX = (i: number) =>
    pad.left + (sorted.length === 1 ? innerW / 2 : (i / (sorted.length - 1)) * innerW)
  const toY = (v: number) => pad.top + (1 - (v - minV) / range) * innerH

  const valuePath = 'M ' + sorted.map((p, i) => `${toX(i)},${toY(p.portfolio_value)}`).join(' L ')
  const investedPath = 'M ' + sorted.map((p, i) => `${toX(i)},${toY(p.net_invested)}`).join(' L ')

  const topPts = sorted.map((p, i) => `${toX(i)},${toY(p.portfolio_value)}`).join(' L ')
  const bottomPts = [...sorted].reverse().map((p, i) => `${toX(sorted.length - 1 - i)},${toY(p.net_invested)}`).join(' L ')
  const pnlAreaPath = `M ${topPts} L ${bottomPts} Z`

  const lastPoint = sorted[sorted.length - 1]
  const isPositive = lastPoint ? lastPoint.pnl >= 0 : true

  const yTicks = [0, 0.5, 1].map((t) => ({ y: pad.top + (1 - t) * innerH, val: minV + t * range }))
  const step = Math.max(1, Math.ceil((sorted.length - 1) / 6))
  const xTickIndices = [...new Set([
    ...Array.from({ length: sorted.length }, (_, i) => i).filter((i) => i % step === 0),
    sorted.length - 1,
  ])]

  const fmtDate = (d: string) =>
    new Date(d + 'T00:00:00').toLocaleDateString('fr-FR', { day: '2-digit', month: 'short', year: '2-digit' })

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
          <linearGradient id="pnlGradPos" x1="0" y1="0" x2="0" y2="1">
            <stop offset="0%" stopColor="#10b981" stopOpacity={0.18} />
            <stop offset="100%" stopColor="#10b981" stopOpacity={0.02} />
          </linearGradient>
          <linearGradient id="pnlGradNeg" x1="0" y1="0" x2="0" y2="1">
            <stop offset="0%" stopColor="#ef4444" stopOpacity={0.02} />
            <stop offset="100%" stopColor="#ef4444" stopOpacity={0.18} />
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

        <path d={pnlAreaPath} fill={isPositive ? 'url(#pnlGradPos)' : 'url(#pnlGradNeg)'} />
        <path d={investedPath} fill="none" stroke="#d1d5db" strokeWidth={1.5} strokeDasharray="4,3" strokeLinejoin="round" />
        <path d={valuePath} fill="none" stroke={lineColor} strokeWidth={2} strokeLinejoin="round" />

        {xTickIndices.map((idx) => (
          <text key={idx} x={toX(idx)} y={H - pad.bottom + 13} textAnchor="middle" fontSize={8.5} fill="#9ca3af">
            {new Date(sorted[idx].date + 'T00:00:00').toLocaleDateString('fr-FR', { month: 'short', year: '2-digit' })}
          </text>
        ))}

        {sorted.map((_, i) => (
          <rect key={i} x={toX(i) - 10} y={pad.top} width={20} height={innerH} fill="transparent" onMouseEnter={() => setHovered(i)} />
        ))}

        {hovered !== null && (
          <>
            <line x1={toX(hovered)} y1={pad.top} x2={toX(hovered)} y2={H - pad.bottom} stroke="#d1d5db" strokeWidth={1} strokeDasharray="3,2" />
            <circle cx={toX(hovered)} cy={toY(sorted[hovered].portfolio_value)} r={3.5} fill={lineColor} />
            <circle cx={toX(hovered)} cy={toY(sorted[hovered].net_invested)} r={2.5} fill="#d1d5db" stroke="#9ca3af" strokeWidth={1} />
          </>
        )}
      </svg>

      {hov && (
        <div className="absolute top-1 left-1/2 -translate-x-1/2 bg-gray-900 text-white text-xs px-3 py-2 rounded-xl pointer-events-none whitespace-nowrap shadow-xl z-10">
          <div className="text-gray-400 text-center mb-1">{fmtDate(hov.date)}</div>
          <div className="flex gap-4">
            <div>
              <div className="text-gray-400 text-[10px]">Valorisation</div>
              <div className="font-medium">{format(hov.portfolio_value.toFixed(2), 'EUR')}</div>
            </div>
            <div>
              <div className="text-gray-400 text-[10px]">Net investi</div>
              <div className="font-medium">{format(hov.net_invested.toFixed(2), 'EUR')}</div>
            </div>
            <div>
              <div className="text-gray-400 text-[10px]">P&L</div>
              <div className={`font-semibold ${hov.pnl >= 0 ? 'text-emerald-400' : 'text-red-400'}`}>
                {hov.pnl >= 0 ? '+' : ''}{format(hov.pnl.toFixed(2), 'EUR')}
                <span className="text-[10px] ml-1 opacity-70">({hov.pnl >= 0 ? '+' : ''}{hov.pnl_pct.toFixed(1)}%)</span>
              </div>
            </div>
          </div>
        </div>
      )}

      <div className="flex items-center gap-5 pt-2 px-1 flex-shrink-0">
        <div className="flex items-center gap-1.5">
          <div className="w-4 h-0.5 rounded" style={{ backgroundColor: lineColor }} />
          <span className="text-[10px] text-gray-400">Valorisation</span>
        </div>
        <div className="flex items-center gap-1.5">
          <div className="w-4 h-0 border-t border-dashed border-gray-300" />
          <span className="text-[10px] text-gray-400">Net investi</span>
        </div>
        <div className="flex items-center gap-1.5">
          <div className={`w-3 h-3 rounded-sm opacity-60`}
            style={{ backgroundColor: isPositive ? '#10b981' : '#ef4444' }} />
          <span className="text-[10px] text-gray-400">P&L</span>
        </div>
      </div>
    </div>
  )
}

// ── Patrimoine Chart ──────────────────────────────────────────────────────────

const STACK_ORDER = ['CHECKING', 'SAVINGS', 'INVESTMENT', 'OTHER', 'PORTFOLIOS']
const STACK_LABELS: Record<string, string> = {
  CHECKING: 'Courant', SAVINGS: 'Épargne', INVESTMENT: 'Investissement',
  OTHER: 'Autre', PORTFOLIOS: 'Portefeuilles',
}
const STACK_COLORS_LIGHT: Record<string, string> = {
  CHECKING: '#1e293b', SAVINGS: '#334155', INVESTMENT: '#6366f1',
  OTHER: '#94a3b8', PORTFOLIOS: '#a78bfa',
}
const STACK_COLORS_DARK: Record<string, string> = {
  CHECKING: '#cbd5e1', SAVINGS: '#64748b', INVESTMENT: '#818cf8',
  OTHER: '#475569', PORTFOLIOS: '#c4b5fd',
}

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
function fmtBucket(bucket: string, long = false): string {
  const d = parseBucket(bucket)
  if (/^\d{4}-W\d{2}$/.test(bucket)) return d.toLocaleDateString('fr-FR', { day: '2-digit', month: 'short' })
  if (/^\d{4}-\d{2}-\d{2}$/.test(bucket)) return d.toLocaleDateString('fr-FR', { day: '2-digit', month: 'short' })
  if (long) return d.toLocaleDateString('fr-FR', { day: '2-digit', month: 'short', year: '2-digit' })
  return d.toLocaleDateString('fr-FR', { month: 'short', year: '2-digit' })
}

function PatrimoineChart({ fullPoints, groups }: {
  fullPoints: NetWorthFullTimeseriesPoint[]
  groups: NetWorthGroupedTimeseriesGroup[]
}) {
  const { format } = useCurrency()
  const { theme } = useTheme()
  const isDark = theme === 'dark'
  const STACK_COLORS = isDark ? STACK_COLORS_DARK : STACK_COLORS_LIGHT
  const gridColor = isDark ? '#334155' : '#f3f4f6'
  const lineColor = isDark ? '#f1f5f9' : '#111827'
  const [hovered, setHovered] = useState<number | null>(null)

  const n = fullPoints.length
  if (n < 2) return (
    <div className="flex items-center justify-center h-full text-xs text-gray-400">Pas encore assez de données.</div>
  )

  // Valeurs par groupe (accounts)
  const groupMap: Record<string, number[]> = {}
  for (const g of groups) {
    groupMap[g.key] = g.points.map((p) => Math.max(0, parseFloat(p.balance_end)))
  }

  // Patrimoine total (comptes + portefeuilles)
  const totalVals = fullPoints.map((p) => Math.max(0, parseFloat(p.balance_end)))

  // Portefeuilles = total - somme des comptes
  const accountSum = (i: number) =>
    ['CHECKING', 'SAVINGS', 'INVESTMENT', 'OTHER'].reduce((s, k) => s + (groupMap[k]?.[i] ?? 0), 0)
  groupMap['PORTFOLIOS'] = totalVals.map((tot, i) => Math.max(0, tot - accountSum(i)))

  // Y axis démarre à 0
  const maxVal = Math.max(...totalVals, 1)

  const W = 700, H = 210
  const pad = { top: 12, right: 12, bottom: 26, left: 72 }
  const innerW = W - pad.left - pad.right
  const innerH = H - pad.top - pad.bottom

  const xAt = (i: number) => pad.left + (n === 1 ? innerW / 2 : (i / (n - 1)) * innerW)
  const yAt = (v: number) => pad.top + (1 - Math.min(v, maxVal) / maxVal) * innerH

  // Calcul des aires empilées cumulatives
  const cumVals: Record<string, number[]> = {}
  let prev = new Array(n).fill(0)
  for (const key of STACK_ORDER) {
    const vals = groupMap[key] ?? new Array(n).fill(0)
    cumVals[key] = vals.map((v, i) => prev[i] + v)
    prev = cumVals[key]
  }

  function buildArea(topKey: string, botKey: string | null): string {
    const top = cumVals[topKey]
    const bot = botKey ? cumVals[botKey] : new Array(n).fill(0)
    const fwd = top.map((v, i) => `${xAt(i).toFixed(1)},${yAt(v).toFixed(1)}`).join(' L ')
    const bwd = [...bot].reverse().map((v, i) => `${xAt(n - 1 - i).toFixed(1)},${yAt(v).toFixed(1)}`).join(' L ')
    return `M ${fwd} L ${bwd} Z`
  }

  const yTicks = [0, 0.25, 0.5, 0.75, 1].map((t) => ({ y: pad.top + (1 - t) * innerH, val: t * maxVal }))
  const step = Math.max(1, Math.ceil((n - 1) / 6))
  const xTickIndices = [...new Set([
    ...Array.from({ length: n }, (_, i) => i).filter((i) => i % step === 0),
    n - 1,
  ])]

  const activeGroups = STACK_ORDER.filter((k) => (groupMap[k] ?? []).some((v) => v > 1))

  return (
    <div className="relative flex flex-col h-full">
      <svg
        viewBox={`0 0 ${W} ${H}`}
        preserveAspectRatio="xMidYMid meet"
        style={{ width: '100%', flex: 1, minHeight: 0 }}
        onMouseLeave={() => setHovered(null)}
      >
        {/* Grid */}
        {yTicks.map((t, i) => (
          <g key={i}>
            <line x1={pad.left} y1={t.y} x2={W - pad.right} y2={t.y} stroke={gridColor} strokeWidth={1} />
            <text x={pad.left - 5} y={t.y} textAnchor="end" dominantBaseline="middle" fontSize={8} fill="#9ca3af">
              {new Intl.NumberFormat('fr-FR', { notation: 'compact', maximumFractionDigits: 0 }).format(t.val)}
            </text>
          </g>
        ))}

        {/* Aires empilées */}
        {STACK_ORDER.map((key, idx) => (
          <path
            key={key}
            d={buildArea(key, idx > 0 ? STACK_ORDER[idx - 1] : null)}
            fill={STACK_COLORS[key]}
            opacity={0.7}
          />
        ))}

        {/* Ligne totale */}
        <path
          d={'M ' + totalVals.map((v, i) => `${xAt(i).toFixed(1)},${yAt(v).toFixed(1)}`).join(' L ')}
          fill="none" stroke={lineColor} strokeWidth={1.5} strokeLinejoin="round"
        />

        {/* Labels X */}
        {xTickIndices.map((idx) => (
          <text key={idx} x={xAt(idx)} y={H - pad.bottom + 12} textAnchor="middle" fontSize={8} fill="#9ca3af">
            {fmtBucket(fullPoints[idx].bucket)}
          </text>
        ))}

        {/* Zones hover invisibles */}
        {fullPoints.map((_, i) => (
          <rect key={i} x={xAt(i) - 10} y={pad.top} width={20} height={innerH}
            fill="transparent" onMouseEnter={() => setHovered(i)} />
        ))}

        {/* Crosshair */}
        {hovered !== null && (
          <>
            <line x1={xAt(hovered)} y1={pad.top} x2={xAt(hovered)} y2={pad.top + innerH}
              stroke="#9ca3af" strokeWidth={1} strokeDasharray="3,2" />
            <circle cx={xAt(hovered)} cy={yAt(totalVals[hovered])} r={3}
              fill={lineColor} stroke="white" strokeWidth={1.5} />
          </>
        )}
      </svg>

      {/* Tooltip */}
      {hovered !== null && (
        <div className="absolute top-1 left-1/2 -translate-x-1/2 bg-gray-900 text-white text-xs px-3 py-2 rounded-xl pointer-events-none whitespace-nowrap shadow-xl z-10">
          <div className="text-gray-400 text-center mb-1.5">{fmtBucket(fullPoints[hovered].bucket, true)}</div>
          <div className="font-semibold mb-1">{format(totalVals[hovered].toFixed(2), 'EUR')}</div>
          {activeGroups.filter((k) => (groupMap[k]?.[hovered] ?? 0) > 1).map((k) => (
            <div key={k} className="flex items-center gap-3">
              <div className="w-2 h-2 rounded-sm flex-shrink-0" style={{ backgroundColor: STACK_COLORS[k] }} />
              <span className="text-gray-400">{STACK_LABELS[k]}</span>
              <span className="ml-auto tabular-nums">{format((groupMap[k]?.[hovered] ?? 0).toFixed(0), 'EUR')}</span>
            </div>
          ))}
        </div>
      )}

      {/* Légende */}
      <div className="flex items-center gap-3 pt-1 px-1 flex-shrink-0 flex-wrap">
        {activeGroups.map((k) => (
          <div key={k} className="flex items-center gap-1.5">
            <div className="w-2.5 h-2.5 rounded-sm opacity-70" style={{ backgroundColor: STACK_COLORS[k] }} />
            <span className="text-[10px] text-gray-400">{STACK_LABELS[k]}</span>
          </div>
        ))}
      </div>
    </div>
  )
}

// ── Dashboard ─────────────────────────────────────────────────────────────────

export default function DashboardPage() {
  const { format } = useCurrency()
  const { data: nw, isLoading: nwLoading } = useNetWorthGrouped()
  const { data: pnlData = [], isLoading: pnlLoading } = usePnlCurve()
  const { data: cf, isLoading: cfLoading } = useCashFlow()
  const [chartTab, setChartTab] = useState<'patrimoine' | 'pnl'>('patrimoine')
  const [nwPeriod, setNwPeriod] = useState<PeriodSelection>({ type: 'preset', preset: '1A' })
  const { from: nwFrom, to: nwTo } = resolveDates(nwPeriod, '2015-01-01')
  const { data: nwTs, isLoading: nwTsLoading } = useNetWorthFullTimeseries(nwFrom, nwTo)
  const { data: nwGrouped, isLoading: nwGroupedLoading } = useNetWorthGroupedTimeseries(nwFrom, nwTo)

  const currency = nw?.currency ?? 'EUR'
  const lastPnl = pnlData.length > 0 ? pnlData[pnlData.length - 1] : null

  const accountsNet = nw ? parseFloat(nw.total) : 0
  const portfolioValue = lastPnl ? lastPnl.portfolio_value : 0
  const totalPatrimoine = accountsNet + portfolioValue

  const donutSlices: DonutSlice[] = useMemo(() => {
    const slices: DonutSlice[] = (nw?.groups ?? [])
      .map((g) => ({ key: g.key, value: Math.max(0, parseFloat(g.net_worth)), label: NW_TYPE_LABELS[g.key] ?? g.key }))
    if (lastPnl && lastPnl.portfolio_value > 0)
      slices.push({ key: '__portfolios', value: lastPnl.portfolio_value, label: 'Portefeuilles' })
    return slices.filter((s) => s.value > 0)
  }, [nw, lastPnl])

  const curIncome = cf ? parseFloat(cf.current.income) : 0
  const curExpenses = cf ? parseFloat(cf.current.expenses) : 0

  const fmtMonth = (m: string) => {
    const [y, mo] = m.split('-')
    return new Date(parseInt(y), parseInt(mo) - 1, 1).toLocaleDateString('fr-FR', { month: 'long' })
  }
  const monthLabel = cf ? fmtMonth(cf.current.month) : ''

  return (
    <div className="h-full flex flex-col p-6 gap-4 overflow-hidden">

      {/* Header */}
      <div className="flex-none flex items-baseline justify-between">
        <div>
          <h1 className="text-xl font-semibold text-gray-900">Dashboard</h1>
          <p className="text-xs text-gray-400 mt-0.5">Vue d'ensemble du patrimoine</p>
        </div>
        {cf && (
          <p className="text-xs text-gray-400 capitalize">{monthLabel}</p>
        )}
      </div>

      {/* KPI row */}
      <div className="flex-none grid grid-cols-4 gap-3">
        <KpiCard
          label="Patrimoine total"
          value={format(totalPatrimoine.toFixed(2), currency)}
          sub={nw ? `dont ${format(nw.total, currency)} net` : undefined}
          loading={nwLoading || pnlLoading}
        />
        <KpiCard
          label="Performance portef."
          value={lastPnl ? `${lastPnl.pnl >= 0 ? '+' : ''}${format(lastPnl.pnl.toFixed(2), 'EUR')}` : '—'}
          sub={lastPnl ? `${lastPnl.pnl >= 0 ? '+' : ''}${lastPnl.pnl_pct.toFixed(1)}% all-time` : undefined}
          positive={lastPnl ? lastPnl.pnl >= 0 : undefined}
          loading={pnlLoading}
        />
        <KpiCard
          label={`Revenus — ${monthLabel}`}
          value={cf ? format(curIncome.toFixed(2), cf.currency) : '—'}
          loading={cfLoading}
          positive={curIncome > 0 ? true : undefined}
        />
        <KpiCard
          label={`Dépenses — ${monthLabel}`}
          value={cf && curExpenses > 0 ? `−${format(curExpenses.toFixed(2), cf.currency)}` : '—'}
          loading={cfLoading}
          positive={curExpenses > 0 ? false : undefined}
        />
      </div>

      {/* Main grid — fills remaining height */}
      <div className="flex-1 min-h-0 grid grid-cols-5 gap-4">

        {/* Répartition — 2/5 */}
        <div className="col-span-2 bg-white rounded-2xl border border-gray-100 shadow-sm p-5 flex flex-col min-h-0">
          <p className="text-[10px] font-medium text-gray-400 uppercase tracking-wider mb-4 flex-none">
            Répartition du patrimoine
          </p>
          <div className="flex-1 min-h-0">
            {nwLoading || pnlLoading ? (
              <div className="h-full bg-gray-50 rounded-xl animate-pulse" />
            ) : (
              <DonutChart slices={donutSlices} />
            )}
          </div>
        </div>

        {/* Chart — 3/5 */}
        <div className="col-span-3 bg-white rounded-2xl border border-gray-100 shadow-sm p-5 flex flex-col min-h-0">

          {/* Header + Tabs */}
          <div className="flex-none flex items-start justify-between mb-3">
            <div className="flex flex-col gap-1.5">
              {/* Tabs */}
              <div className="flex items-center gap-1 bg-gray-100 dark:bg-slate-700/50 rounded-lg p-0.5 w-fit">
                <button
                  onClick={() => setChartTab('patrimoine')}
                  className={`px-3 py-1 text-[11px] font-medium rounded-md transition-all ${
                    chartTab === 'patrimoine'
                      ? 'bg-white dark:bg-slate-600 shadow-sm text-gray-900 dark:text-slate-100'
                      : 'text-gray-500 dark:text-slate-400 hover:text-gray-700 dark:hover:text-slate-200'
                  }`}
                >
                  Patrimoine
                </button>
                <button
                  onClick={() => setChartTab('pnl')}
                  className={`px-3 py-1 text-[11px] font-medium rounded-md transition-all ${
                    chartTab === 'pnl'
                      ? 'bg-white dark:bg-slate-600 shadow-sm text-gray-900 dark:text-slate-100'
                      : 'text-gray-500 dark:text-slate-400 hover:text-gray-700 dark:hover:text-slate-200'
                  }`}
                >
                  P&L Portefeuilles
                </button>
              </div>

              {/* Sous-titre selon le tab actif */}
              {chartTab === 'patrimoine' ? (
                nwTs && (
                  <span className="text-lg font-semibold tabular-nums text-gray-900">
                    {format(parseFloat(nwTs.points[nwTs.points.length - 1]?.balance_end ?? '0').toFixed(2), 'EUR')}
                  </span>
                )
              ) : (
                lastPnl && !pnlLoading && (
                  <div className="flex items-baseline gap-2">
                    <span className={`text-lg font-semibold tabular-nums ${lastPnl.pnl >= 0 ? 'text-emerald-600' : 'text-red-600'}`}>
                      {lastPnl.pnl >= 0 ? '+' : ''}{format(lastPnl.pnl.toFixed(2), 'EUR')}
                    </span>
                    <span className={`text-xs font-medium px-1.5 py-0.5 rounded-full ${lastPnl.pnl >= 0 ? 'bg-emerald-50 text-emerald-700' : 'bg-red-50 text-red-600'}`}>
                      {lastPnl.pnl >= 0 ? '+' : ''}{lastPnl.pnl_pct.toFixed(1)}%
                    </span>
                  </div>
                )
              )}
            </div>

            <div className="flex items-center gap-3">
              {chartTab === 'patrimoine' && (
                <PeriodPicker selection={nwPeriod} onChange={setNwPeriod} minMonth="2015-01" />
              )}
              {chartTab === 'pnl' && lastPnl && !pnlLoading && (
                <div className="text-right">
                  <p className="text-[10px] text-gray-400">Net investi</p>
                  <p className="text-sm font-medium text-gray-700 tabular-nums">
                    {format(lastPnl.net_invested.toFixed(2), 'EUR')}
                  </p>
                </div>
              )}
            </div>
          </div>

          <div className="flex-1 min-h-0">
            {chartTab === 'patrimoine' ? (
              nwTsLoading || nwGroupedLoading ? (
                <div className="h-full bg-gray-50 rounded-xl animate-pulse" />
              ) : !nwTs || nwTs.points.length < 2 ? (
                <div className="flex flex-col items-center justify-center h-full gap-2 text-gray-400">
                  <span className="text-4xl opacity-20">◎</span>
                  <p className="text-sm">Pas encore assez de données</p>
                </div>
              ) : (
                <PatrimoineChart fullPoints={nwTs.points} groups={nwGrouped?.groups ?? []} />
              )
            ) : (
              pnlLoading ? (
                <div className="h-full bg-gray-50 rounded-xl animate-pulse" />
              ) : pnlData.length < 2 ? (
                <div className="flex flex-col items-center justify-center h-full gap-2 text-gray-400">
                  <span className="text-4xl opacity-20">◎</span>
                  <p className="text-sm">Pas encore assez de snapshots</p>
                </div>
              ) : (
                <PnlChart data={pnlData} />
              )
            )}
          </div>
        </div>

      </div>
    </div>
  )
}
