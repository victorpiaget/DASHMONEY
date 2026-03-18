import { useParams, useNavigate } from 'react-router-dom'
import { useWorkspaceNetWorth, useWorkspaceNetWorthTimeseries, useMe } from '../hooks/useWorkspace'

function fmt(eur: string): string {
  const n = parseFloat(eur)
  if (isNaN(n)) return '—'
  return new Intl.NumberFormat('fr-FR', { style: 'currency', currency: 'EUR', maximumFractionDigits: 0 }).format(n)
}

function NwChart({ points }: { points: { bucket: string; total_eur: string }[] }) {
  if (!points.length) return <p className="text-xs text-gray-400 text-center py-8">Pas de données historiques.</p>

  const values = points.map((p) => parseFloat(p.total_eur))
  const min = Math.min(...values)
  const max = Math.max(...values)
  const range = max - min || 1
  const W = 600
  const H = 160
  const pad = { top: 16, right: 16, bottom: 32, left: 16 }
  const cw = W - pad.left - pad.right
  const ch = H - pad.top - pad.bottom

  const x = (i: number) => pad.left + (i / Math.max(points.length - 1, 1)) * cw
  const y = (v: number) => pad.top + ch - ((v - min) / range) * ch

  const pathD = points
    .map((p, i) => `${i === 0 ? 'M' : 'L'} ${x(i).toFixed(1)} ${y(parseFloat(p.total_eur)).toFixed(1)}`)
    .join(' ')

  const areaD =
    `${pathD} L ${x(points.length - 1).toFixed(1)} ${(pad.top + ch).toFixed(1)} L ${x(0).toFixed(1)} ${(pad.top + ch).toFixed(1)} Z`

  const lastVal = values[values.length - 1]
  const firstVal = values[0]
  const isUp = lastVal >= firstVal
  const color = isUp ? '#16a34a' : '#dc2626'
  const areaColor = isUp ? '#dcfce7' : '#fee2e2'

  return (
    <svg viewBox={`0 0 ${W} ${H}`} className="w-full h-auto">
      <path d={areaD} fill={areaColor} opacity={0.6} />
      <path d={pathD} stroke={color} strokeWidth={2} fill="none" strokeLinecap="round" strokeLinejoin="round" />
      {points.map((p, i) => (
        <g key={p.bucket}>
          <circle cx={x(i)} cy={y(parseFloat(p.total_eur))} r={3} fill={color} />
          {(i === 0 || i === points.length - 1 || points.length <= 6) && (
            <text
              x={x(i)}
              y={H - 6}
              textAnchor={i === 0 ? 'start' : i === points.length - 1 ? 'end' : 'middle'}
              fontSize={10}
              fill="#9ca3af"
            >
              {p.bucket.slice(0, 7)}
            </text>
          )}
        </g>
      ))}
    </svg>
  )
}

export default function WorkspaceOverviewPage() {
  const { workspaceId } = useParams<{ workspaceId: string }>()
  const navigate = useNavigate()
  const { data: me } = useMe()
  const { data: nw, isLoading: nwLoading } = useWorkspaceNetWorth(workspaceId)

  const now = new Date()
  const dateTo = now.toISOString().slice(0, 10)
  const dateFrom = new Date(now.getFullYear() - 1, now.getMonth(), now.getDate()).toISOString().slice(0, 10)
  const { data: ts } = useWorkspaceNetWorthTimeseries(workspaceId, dateFrom, dateTo, 'monthly')

  const workspace = me?.workspaces.find((w) => w.id === workspaceId)
  const workspaceName = workspace?.name ?? 'Workspace'

  return (
    <div className="min-h-screen bg-gray-50 p-6">
      <div className="max-w-3xl mx-auto space-y-6">

        {/* Header */}
        <div className="flex items-center gap-3">
          <button
            onClick={() => navigate(-1)}
            className="text-gray-400 hover:text-gray-700 transition-colors text-sm px-2 py-1 rounded hover:bg-gray-100"
          >
            ← Retour
          </button>
          <div>
            <p className="text-xs text-gray-400 uppercase tracking-wider font-semibold">Vue d'ensemble</p>
            <h1 className="text-xl font-semibold text-gray-900 mt-0.5">{workspaceName}</h1>
          </div>
        </div>

        {nwLoading ? (
          <div className="flex justify-center py-16">
            <div className="w-6 h-6 border-2 border-gray-200 border-t-gray-700 rounded-full animate-spin" />
          </div>
        ) : !nw ? (
          <p className="text-sm text-gray-400 text-center py-16">Impossible de charger les données.</p>
        ) : (
          <>
            {/* KPI total */}
            <div className="bg-white rounded-2xl border border-gray-200 px-8 py-6">
              <p className="text-xs text-gray-400 uppercase tracking-wider font-semibold mb-1">
                Patrimoine net total
              </p>
              <p className="text-4xl font-semibold text-gray-900 tabular-nums">{fmt(nw.total_eur)}</p>
              <p className="text-xs text-gray-400 mt-2">
                {nw.profiles.length} profil{nw.profiles.length > 1 ? 's' : ''} · en EUR
                {nw.at && ` · au ${new Date(nw.at).toLocaleDateString('fr-FR')}`}
              </p>
            </div>

            {/* Profils breakdown */}
            <div className="space-y-3">
              <p className="text-[10px] font-semibold text-gray-400 uppercase tracking-wider">Par profil</p>
              {nw.profiles.length === 0 ? (
                <p className="text-sm text-gray-400">Aucun profil accessible dans ce workspace.</p>
              ) : (
                <div className="grid gap-3 sm:grid-cols-2">
                  {nw.profiles.map((p) => {
                    const total = parseFloat(p.total_eur)
                    const grandTotal = parseFloat(nw.total_eur)
                    const pct = grandTotal ? Math.round((total / grandTotal) * 100) : 0
                    return (
                      <div key={p.profile_id} className="bg-white rounded-2xl border border-gray-200 px-5 py-4">
                        <div className="flex items-center justify-between mb-3">
                          <div className="flex items-center gap-2">
                            <div className="w-7 h-7 rounded-full bg-gray-100 flex items-center justify-center text-xs font-semibold text-gray-600 flex-shrink-0">
                              {p.display_name.charAt(0).toUpperCase()}
                            </div>
                            <span className="text-sm font-medium text-gray-900">{p.display_name}</span>
                          </div>
                          <span className="text-xs text-gray-400">{pct}%</span>
                        </div>
                        <p className="text-xl font-semibold text-gray-900 tabular-nums">{fmt(p.total_eur)}</p>
                        <div className="mt-2 flex items-center gap-3 text-[11px] text-gray-400">
                          <span>Comptes {fmt(p.accounts_eur)}</span>
                          <span>·</span>
                          <span>Portefeuilles {fmt(p.portfolios_eur)}</span>
                        </div>
                        {/* Barre de progression */}
                        <div className="mt-3 h-1.5 bg-gray-100 rounded-full overflow-hidden">
                          <div
                            className="h-full bg-gray-900 rounded-full transition-all"
                            style={{ width: `${pct}%` }}
                          />
                        </div>
                      </div>
                    )
                  })}
                </div>
              )}
            </div>

            {/* Courbe historique */}
            {ts && ts.points.length > 0 && (
              <div className="bg-white rounded-2xl border border-gray-200 px-6 py-5">
                <p className="text-[10px] font-semibold text-gray-400 uppercase tracking-wider mb-4">
                  Évolution sur 12 mois
                </p>
                <NwChart points={ts.points} />
              </div>
            )}
          </>
        )}
      </div>
    </div>
  )
}
