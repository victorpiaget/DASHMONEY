import { useState, useMemo } from 'react'
import { useAccountBalance, useAccounts } from '../hooks/useAccounts'
import { useNetWorthGrouped } from '../hooks/useNetWorth'
import { usePnlCurve } from '../hooks/usePortfolios'
import { formatAmount } from '../lib/formatters'
import { Link } from 'react-router-dom'
import type { PnlPoint } from '../lib/portfoliosApi'

// ── Account card ──────────────────────────────────────────────────────────────

function AccountCard({ account }: { account: { id: string; name: string; currency: string; account_type: string } }) {
  const { data: balanceData } = useAccountBalance(account.id)
  const balance = balanceData?.balance ?? null
  const negative = balance !== null && parseFloat(balance) < 0
  return (
    <Link
      to={`/accounts/${account.id}`}
      className="bg-white rounded-xl border border-gray-100 shadow-sm px-5 py-3.5 flex items-center justify-between hover:border-gray-200 hover:shadow transition-all block"
    >
      <div>
        <p className="text-sm font-medium text-gray-900">{account.name}</p>
        <p className="text-xs text-gray-400 mt-0.5">{ACCOUNT_TYPE_LABELS[account.account_type] ?? account.account_type}</p>
      </div>
      <p className={`text-sm font-medium tabular-nums ${negative ? 'text-red-600' : 'text-gray-900'}`}>
        {balance !== null ? formatAmount(balance, balanceData!.currency) : '—'}
      </p>
    </Link>
  )
}

const ACCOUNT_TYPE_LABELS: Record<string, string> = {
  CHECKING: 'Courant', SAVINGS: 'Épargne', INVESTMENT: 'Investissement', OTHER: 'Autre',
}

const NW_TYPE_LABELS: Record<string, string> = {
  CHECKING: 'Courant', SAVINGS: 'Épargne', INVESTMENT: 'Investissement', OTHER: 'Autre',
}

// ── PnL Chart ─────────────────────────────────────────────────────────────────

function PnlChart({ data }: { data: PnlPoint[] }) {
  const [hovered, setHovered] = useState<number | null>(null)

  const sorted = useMemo(() => [...data].sort((a, b) => a.date.localeCompare(b.date)), [data])

  const W = 700, H = 200
  const pad = { top: 20, right: 16, bottom: 32, left: 80 }
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

  // Area between value and invested (P&L zone)
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
    <div className="relative">
      <svg viewBox={`0 0 ${W} ${H}`} className="w-full" style={{ height: 220 }} onMouseLeave={() => setHovered(null)}>
        <defs>
          <linearGradient id="pnlGradPos" x1="0" y1="0" x2="0" y2="1">
            <stop offset="0%" stopColor="#10b981" stopOpacity={0.15} />
            <stop offset="100%" stopColor="#10b981" stopOpacity={0.02} />
          </linearGradient>
          <linearGradient id="pnlGradNeg" x1="0" y1="0" x2="0" y2="1">
            <stop offset="0%" stopColor="#ef4444" stopOpacity={0.02} />
            <stop offset="100%" stopColor="#ef4444" stopOpacity={0.15} />
          </linearGradient>
        </defs>

        {/* Grid */}
        {yTicks.map((t, i) => (
          <g key={i}>
            <line x1={pad.left} y1={t.y} x2={W - pad.right} y2={t.y} stroke="#f3f4f6" strokeWidth={1} />
            <text x={pad.left - 6} y={t.y} textAnchor="end" dominantBaseline="middle" fontSize={9} fill="#9ca3af">
              {new Intl.NumberFormat('fr-FR', { notation: 'compact', maximumFractionDigits: 1 }).format(t.val)}
            </text>
          </g>
        ))}

        {/* P&L shaded area */}
        <path d={pnlAreaPath} fill={isPositive ? 'url(#pnlGradPos)' : 'url(#pnlGradNeg)'} />

        {/* Net invested line (dashed) */}
        <path d={investedPath} fill="none" stroke="#d1d5db" strokeWidth={1.5} strokeDasharray="4,3" strokeLinejoin="round" />

        {/* Portfolio value line */}
        <path d={valuePath} fill="none" stroke="#111827" strokeWidth={2} strokeLinejoin="round" />

        {/* X axis ticks */}
        {xTickIndices.map((idx) => (
          <text key={idx} x={toX(idx)} y={H - pad.bottom + 14} textAnchor="middle" fontSize={9} fill="#9ca3af">
            {new Date(sorted[idx].date + 'T00:00:00').toLocaleDateString('fr-FR', { month: 'short', year: '2-digit' })}
          </text>
        ))}

        {/* Hover zones */}
        {sorted.map((_, i) => (
          <rect key={i} x={toX(i) - 10} y={pad.top} width={20} height={innerH} fill="transparent" onMouseEnter={() => setHovered(i)} />
        ))}

        {/* Hover indicator */}
        {hovered !== null && (
          <>
            <line x1={toX(hovered)} y1={pad.top} x2={toX(hovered)} y2={H - pad.bottom} stroke="#d1d5db" strokeWidth={1} strokeDasharray="3,2" />
            <circle cx={toX(hovered)} cy={toY(sorted[hovered].portfolio_value)} r={4} fill="#111827" />
            <circle cx={toX(hovered)} cy={toY(sorted[hovered].net_invested)} r={3} fill="#d1d5db" stroke="#9ca3af" strokeWidth={1} />
          </>
        )}
      </svg>

      {/* Tooltip */}
      {hov && (
        <div className="absolute top-2 left-1/2 -translate-x-1/2 bg-gray-900 text-white text-xs px-3 py-2 rounded-xl pointer-events-none whitespace-nowrap shadow-xl">
          <div className="text-gray-400 text-center mb-1.5">{fmtDate(hov.date)}</div>
          <div className="flex gap-4">
            <div>
              <div className="text-gray-400 text-[10px]">Valorisation</div>
              <div className="font-medium">{formatAmount(hov.portfolio_value.toFixed(2), 'EUR')}</div>
            </div>
            <div>
              <div className="text-gray-400 text-[10px]">Net investi</div>
              <div className="font-medium">{formatAmount(hov.net_invested.toFixed(2), 'EUR')}</div>
            </div>
            <div>
              <div className="text-gray-400 text-[10px]">P&L</div>
              <div className={`font-semibold ${hov.pnl >= 0 ? 'text-emerald-400' : 'text-red-400'}`}>
                {hov.pnl >= 0 ? '+' : ''}{formatAmount(hov.pnl.toFixed(2), 'EUR')}
                <span className="text-[10px] ml-1 opacity-80">({hov.pnl >= 0 ? '+' : ''}{hov.pnl_pct.toFixed(1)}%)</span>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Legend */}
      <div className="flex items-center gap-5 mt-2 px-1">
        <div className="flex items-center gap-1.5">
          <div className="w-5 h-0.5 bg-gray-900 rounded" />
          <span className="text-[10px] text-gray-400">Valorisation</span>
        </div>
        <div className="flex items-center gap-1.5">
          <div className="w-5 h-0 border-t border-dashed border-gray-300" />
          <span className="text-[10px] text-gray-400">Net investi</span>
        </div>
        <div className="flex items-center gap-1.5">
          <div className={`w-3 h-3 rounded-sm ${isPositive ? 'bg-emerald-100' : 'bg-red-100'}`} />
          <span className="text-[10px] text-gray-400">P&L</span>
        </div>
      </div>
    </div>
  )
}

// ── Dashboard ─────────────────────────────────────────────────────────────────

export default function DashboardPage() {
  const { data: nw, isLoading: nwLoading } = useNetWorthGrouped()
  const { data: accounts = [], isLoading: accLoading } = useAccounts()
  const { data: pnlData = [], isLoading: pnlLoading } = usePnlCurve()

  const currency = nw?.currency ?? 'EUR'

  const lastPnl = pnlData.length > 0 ? pnlData[pnlData.length - 1] : null

  return (
    <div className="p-8">
      <div className="mb-8">
        <h1 className="text-2xl font-semibold text-gray-900">Dashboard</h1>
        <p className="text-sm text-gray-400 mt-0.5">Vue d'ensemble de votre patrimoine</p>
      </div>

      {/* Patrimoine net */}
      <div className="bg-white rounded-2xl border border-gray-100 shadow-sm p-8 mb-6">
        <p className="text-xs font-medium text-gray-400 uppercase tracking-wider mb-2">Patrimoine net</p>
        {nwLoading ? (
          <div className="h-10 w-48 bg-gray-100 rounded-lg animate-pulse" />
        ) : (
          <p className="text-4xl font-semibold text-gray-900 tabular-nums">
            {formatAmount(nw?.total ?? '0', currency)}
          </p>
        )}

        {nw && nw.groups.length > 0 && (
          <div className="mt-6 pt-6 border-t border-gray-50 flex gap-8">
            {nw.groups.map((g) => (
              <div key={g.key}>
                <p className="text-xs text-gray-400 mb-1">{NW_TYPE_LABELS[g.key] ?? g.key}</p>
                <p className="text-sm font-medium text-gray-700 tabular-nums">
                  {formatAmount(g.net_worth, currency)}
                </p>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* P&L global */}
      <div className="bg-white rounded-2xl border border-gray-100 shadow-sm p-6 mb-6">
        <div className="flex items-start justify-between mb-5">
          <div>
            <p className="text-xs font-medium text-gray-400 uppercase tracking-wider mb-1">Performance portefeuilles</p>
            {lastPnl && !pnlLoading && (
              <div className="flex items-baseline gap-3">
                <span className={`text-2xl font-semibold tabular-nums ${lastPnl.pnl >= 0 ? 'text-emerald-600' : 'text-red-600'}`}>
                  {lastPnl.pnl >= 0 ? '+' : ''}{formatAmount(lastPnl.pnl.toFixed(2), 'EUR')}
                </span>
                <span className={`text-sm font-medium tabular-nums px-2 py-0.5 rounded-full ${lastPnl.pnl >= 0 ? 'bg-emerald-50 text-emerald-700' : 'bg-red-50 text-red-600'}`}>
                  {lastPnl.pnl >= 0 ? '+' : ''}{lastPnl.pnl_pct.toFixed(1)}%
                </span>
              </div>
            )}
          </div>
          {lastPnl && !pnlLoading && (
            <div className="text-right">
              <p className="text-xs text-gray-400 mb-1">Net investi</p>
              <p className="text-sm font-medium text-gray-700 tabular-nums">
                {formatAmount(lastPnl.net_invested.toFixed(2), 'EUR')}
              </p>
            </div>
          )}
        </div>

        {pnlLoading ? (
          <div className="h-48 bg-gray-50 rounded-xl animate-pulse" />
        ) : pnlData.length < 2 ? (
          <div className="flex items-center justify-center h-32">
            <p className="text-sm text-gray-400">Pas encore assez de snapshots</p>
          </div>
        ) : (
          <PnlChart data={pnlData} />
        )}
      </div>

      {/* Comptes */}
      <div>
        <div className="flex items-center justify-between mb-3">
          <h2 className="text-sm font-medium text-gray-900">Comptes</h2>
          <Link to="/accounts" className="text-xs text-gray-400 hover:text-gray-700 transition-colors">
            Voir tout →
          </Link>
        </div>

        {accLoading ? (
          <div className="space-y-2">
            {[1, 2, 3].map((i) => (
              <div key={i} className="bg-white rounded-xl border border-gray-100 h-14 animate-pulse" />
            ))}
          </div>
        ) : accounts.length === 0 ? (
          <div className="bg-white rounded-2xl border border-dashed border-gray-200 p-8 text-center">
            <p className="text-sm text-gray-400 mb-2">Aucun compte</p>
            <Link to="/accounts" className="text-sm text-gray-900 font-medium hover:underline">
              Créer votre premier compte
            </Link>
          </div>
        ) : (
          <div className="space-y-2">
            {accounts.slice(0, 5).map((account) => (
              <AccountCard key={account.id} account={account} />
            ))}
            {accounts.length > 5 && (
              <Link to="/accounts" className="block text-center text-xs text-gray-400 py-2 hover:text-gray-700">
                +{accounts.length - 5} autres comptes
              </Link>
            )}
          </div>
        )}
      </div>
    </div>
  )
}
