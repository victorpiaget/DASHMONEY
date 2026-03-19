import { useState, useRef } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { useWorkspaceNetWorth, useWorkspaceNetWorthTimeseries, useMe } from '../hooks/useWorkspace'
import { useProfile } from '../context/ProfileContext'
import PeriodPicker, { resolveDates } from '../components/PeriodPicker'
import type { PeriodSelection } from '../components/PeriodPicker'
import type { WorkspaceNetWorthPoint } from '../lib/workspaceApi'

function fmt(eur: string, decimals = 0): string {
  const n = parseFloat(eur)
  if (isNaN(n)) return '—'
  return new Intl.NumberFormat('fr-FR', { style: 'currency', currency: 'EUR', maximumFractionDigits: decimals }).format(n)
}

const PROFILE_COLORS = ['#6366f1', '#f59e0b', '#10b981', '#ef4444', '#8b5cf6', '#06b6d4']

// ── Donut ────────────────────────────────────────────────────────────────────

const TYPE_LABELS: Record<string, string> = {
  CHECKING: 'Courant', SAVINGS: 'Épargne', INVESTMENT: 'Investissement',
  PORTFOLIOS: 'Portefeuilles', OTHER: 'Autre',
}
const TYPE_ORDER = ['CHECKING', 'SAVINGS', 'INVESTMENT', 'PORTFOLIOS', 'OTHER']
const TYPE_COLORS: Record<string, string> = {
  CHECKING: '#111827', SAVINGS: '#4b5563', INVESTMENT: '#6b7280',
  PORTFOLIOS: '#9ca3af', OTHER: '#d1d5db',
}

interface DonutSlice { key: string; label: string; value: number; color: string }

function WorkspaceDonut({ slices }: { slices: DonutSlice[] }) {
  const [hovered, setHovered] = useState<string | null>(null)
  const total = slices.reduce((s, d) => s + Math.max(0, d.value), 0)

  if (total <= 0) return (
    <div className="flex flex-col items-center justify-center h-full text-sm text-gray-400 gap-2">
      <span className="text-3xl opacity-20">◎</span>Aucune donnée
    </div>
  )

  const R = 68, cx = 85, cy = 85, stroke = 24
  let cum = -Math.PI / 2

  const arcs = slices.map((s) => {
    const v = Math.max(0, s.value)
    const a = (v / total) * 2 * Math.PI
    const sa = cum; cum += a
    const x1 = cx + R * Math.cos(sa), y1 = cy + R * Math.sin(sa)
    const x2 = cx + R * Math.cos(cum), y2 = cy + R * Math.sin(cum)
    return { ...s, pct: (v / total) * 100, path: `M ${x1} ${y1} A ${R} ${R} 0 ${a > Math.PI ? 1 : 0} 1 ${x2} ${y2}` }
  })

  const hov = arcs.find((a) => a.key === hovered)

  return (
    <div className="flex items-center gap-5 h-full">
      <svg viewBox="0 0 170 170" className="flex-shrink-0" width={150} height={150}>
        {arcs.map((a) => (
          <path key={a.key} d={a.path} fill="none" stroke={a.color}
            strokeWidth={hovered === a.key ? stroke + 5 : stroke} strokeLinecap="butt"
            onMouseEnter={() => setHovered(a.key)} onMouseLeave={() => setHovered(null)}
            style={{ cursor: 'pointer', transition: 'stroke-width 0.12s' }} />
        ))}
        <text x={cx} y={cy - 9} textAnchor="middle" fontSize={8} fill="#9ca3af">{hov ? hov.label : 'Total'}</text>
        <text x={cx} y={cy + 7} textAnchor="middle" fontSize={13} fontWeight={700} fill="#111827">
          {hov ? `${hov.pct.toFixed(1)}%` : '100%'}
        </text>
        {hov && <text x={cx} y={cy + 22} textAnchor="middle" fontSize={8} fill="#6b7280">{fmt(hov.value.toFixed(2), 2)}</text>}
      </svg>
      <div className="flex flex-col gap-2.5 flex-1 min-w-0">
        {arcs.map((a) => (
          <div key={a.key} className="flex items-center gap-2.5 cursor-pointer group"
            onMouseEnter={() => setHovered(a.key)} onMouseLeave={() => setHovered(null)}>
            <div className="w-2 h-2 rounded-full flex-shrink-0 transition-transform group-hover:scale-125" style={{ background: a.color }} />
            <div className="min-w-0 flex-1">
              <div className="flex items-center justify-between gap-2">
                <p className="text-xs text-gray-500 truncate">{a.label}</p>
                <p className="text-xs font-medium text-gray-900 tabular-nums flex-shrink-0">{a.pct.toFixed(0)}%</p>
              </div>
              <p className="text-[10px] text-gray-400 tabular-nums">{fmt(a.value.toFixed(2), 2)}</p>
            </div>
          </div>
        ))}
      </div>
    </div>
  )
}

// ── Chart ────────────────────────────────────────────────────────────────────

function NwChartDetailed({ points, profileNames, profileColors }: {
  points: WorkspaceNetWorthPoint[]
  profileNames: Record<string, string>
  profileColors: Record<string, string>
}) {
  const [hoveredIdx, setHoveredIdx] = useState<number | null>(null)
  const svgRef = useRef<SVGSVGElement>(null)

  if (!points.length)
    return <p className="text-xs text-gray-400 text-center py-8">Pas de données historiques.</p>

  const profileIds = Object.keys(points[0]?.by_profile ?? {})
  const allValues = [...points.map((p) => parseFloat(p.total_eur)),
    ...points.flatMap((p) => Object.values(p.by_profile).map((v) => parseFloat(v))), 0]
  const maxVal = Math.max(...allValues), minVal = Math.min(...allValues)
  const range = maxVal - minVal || 1

  const W = 620, H = 260
  const pad = { top: 16, right: 88, bottom: 28, left: 8 }
  const cw = W - pad.left - pad.right, ch = H - pad.top - pad.bottom

  const xAt = (i: number) => pad.left + (i / Math.max(points.length - 1, 1)) * cw
  const yAt = (v: number) => pad.top + ch - ((v - minVal) / range) * ch
  const yZero = yAt(0)

  const linePath = (vals: number[]) => vals.map((v, i) => `${i === 0 ? 'M' : 'L'} ${xAt(i).toFixed(1)} ${yAt(v).toFixed(1)}`).join(' ')
  const areaPath = (vals: number[]) => `${linePath(vals)} L ${xAt(vals.length - 1).toFixed(1)} ${yZero.toFixed(1)} L ${xAt(0).toFixed(1)} ${yZero.toFixed(1)} Z`
  const totalVals = points.map((p) => parseFloat(p.total_eur))

  function handleMouseMove(e: React.MouseEvent<SVGSVGElement>) {
    if (!svgRef.current || !points.length) return
    const rect = svgRef.current.getBoundingClientRect()
    const mouseX = ((e.clientX - rect.left) / rect.width) * W
    if (mouseX < pad.left - 20 || mouseX > W - pad.right + 20) { setHoveredIdx(null); return }
    let closest = 0, minDist = Infinity
    for (let i = 0; i < points.length; i++) {
      const d = Math.abs(xAt(i) - mouseX)
      if (d < minDist) { minDist = d; closest = i }
    }
    setHoveredIdx(closest)
  }

  const tipW = 150, tipH = 12 + 16 + 18 + profileIds.length * 18 + 8
  const hov = hoveredIdx
  const hovX = hov !== null ? xAt(hov) : 0
  const showLeft = hov !== null && hovX > W * 0.55
  const tipX = hov !== null ? (showLeft ? hovX - tipW - 10 : hovX + 10) : 0

  return (
    <svg ref={svgRef} viewBox={`0 0 ${W} ${H}`} className="w-full h-full" preserveAspectRatio="xMidYMid meet"
      onMouseMove={handleMouseMove} onMouseLeave={() => setHoveredIdx(null)} style={{ cursor: 'crosshair', display: 'block' }}>
      {minVal < 0 && <line x1={pad.left} y1={yZero} x2={W - pad.right} y2={yZero} stroke="#e5e7eb" strokeWidth={1} strokeDasharray="4 3" />}
      {profileIds.map((pid) => {
        const color = profileColors[pid] ?? '#6366f1'
        const vals = points.map((p) => parseFloat(p.by_profile[pid] ?? '0'))
        const labelY = Math.min(Math.max(yAt(vals[vals.length - 1]), pad.top + 8), pad.top + ch - 8)
        return (
          <g key={pid}>
            <path d={areaPath(vals)} fill={color} opacity={0.1} />
            <path d={linePath(vals)} stroke={color} strokeWidth={1.5} fill="none" strokeLinecap="round" strokeLinejoin="round" />
            <text x={W - pad.right + 8} y={labelY} dominantBaseline="middle" fontSize={10} fill={color} fontWeight={600}>{profileNames[pid] ?? '—'}</text>
          </g>
        )
      })}
      <path d={linePath(totalVals)} stroke="#111827" strokeWidth={2.5} fill="none" strokeLinecap="round" strokeLinejoin="round" />
      <text x={W - pad.right + 8} y={Math.min(Math.max(yAt(totalVals[totalVals.length - 1]), pad.top + 8), pad.top + ch - 8)}
        dominantBaseline="middle" fontSize={10} fill="#111827" fontWeight={700}>Total</text>
      {[0, points.length - 1].map((i) => (
        <text key={i} x={xAt(i)} y={H - 4} textAnchor={i === 0 ? 'start' : 'end'} fontSize={10} fill="#9ca3af">{points[i].bucket.slice(0, 7)}</text>
      ))}
      {hov !== null && (() => {
        const pt = points[hov]
        return (
          <g>
            <line x1={hovX} y1={pad.top} x2={hovX} y2={pad.top + ch} stroke="#9ca3af" strokeWidth={1} strokeDasharray="3 3" />
            {profileIds.map((pid) => (
              <circle key={pid} cx={hovX} cy={yAt(parseFloat(pt.by_profile[pid] ?? '0'))} r={4}
                fill={profileColors[pid] ?? '#6366f1'} stroke="white" strokeWidth={1.5} />
            ))}
            <circle cx={hovX} cy={yAt(parseFloat(pt.total_eur))} r={4.5} fill="#111827" stroke="white" strokeWidth={1.5} />
            <rect x={tipX} y={pad.top + 4} width={tipW} height={tipH} rx={7} fill="#1f2937" />
            <text x={tipX + 10} y={pad.top + 18} fontSize={10} fill="#9ca3af">{pt.bucket}</text>
            <text x={tipX + 10} y={pad.top + 34} fontSize={10} fill="white" fontWeight={700}>Total</text>
            <text x={tipX + tipW - 8} y={pad.top + 34} fontSize={10} fill="white" fontWeight={700} textAnchor="end">{fmt(pt.total_eur)}</text>
            {profileIds.map((pid, idx) => {
              const color = profileColors[pid] ?? '#6366f1'
              return (
                <g key={pid}>
                  <text x={tipX + 10} y={pad.top + 34 + (idx + 1) * 18} fontSize={10} fill={color} fontWeight={500}>{profileNames[pid] ?? '—'}</text>
                  <text x={tipX + tipW - 8} y={pad.top + 34 + (idx + 1) * 18} fontSize={10} fill={color} textAnchor="end">{fmt(pt.by_profile[pid] ?? '0')}</text>
                </g>
              )
            })}
          </g>
        )
      })()}
    </svg>
  )
}

// ── Page ─────────────────────────────────────────────────────────────────────

export default function WorkspaceOverviewPage() {
  const { workspaceId } = useParams<{ workspaceId: string }>()
  const navigate = useNavigate()
  const { selectProfile } = useProfile()
  const { data: me } = useMe()
  const { data: nw, isLoading: nwLoading } = useWorkspaceNetWorth(workspaceId)
  const [period, setPeriod] = useState<PeriodSelection>({ type: 'preset', preset: '1A' })
  const { from: dateFrom, to: dateTo } = resolveDates(period, '2019-01-01')
  const { data: ts } = useWorkspaceNetWorthTimeseries(workspaceId, dateFrom, dateTo, 'auto')

  const workspace = me?.workspaces.find((w) => w.id === workspaceId)
  const workspaceName = workspace?.name ?? 'Workspace'

  const profileNames: Record<string, string> = {}
  const profileColors: Record<string, string> = {}
  for (const [idx, p] of (nw?.profiles ?? []).entries()) {
    profileNames[p.profile_id] = p.display_name
    profileColors[p.profile_id] = PROFILE_COLORS[idx % PROFILE_COLORS.length]
  }

  function handleSelectProfile(profileId: string, displayName: string) {
    selectProfile(profileId, displayName, workspaceName)
    navigate('/')
  }

  return (
    <div className="h-screen flex flex-col bg-gray-50 overflow-hidden">

      {/* Header */}
      <div className="flex items-center gap-3 px-6 py-4 flex-none">
        <button onClick={() => navigate(-1)}
          className="text-gray-400 hover:text-gray-700 transition-colors text-sm px-2 py-1 rounded hover:bg-gray-100">
          ← Retour
        </button>
        <div>
          <p className="text-[10px] text-gray-400 uppercase tracking-wider font-semibold">Vue d'ensemble</p>
          <h1 className="text-xl font-semibold text-gray-900 leading-tight">{workspaceName}</h1>
        </div>
      </div>

      {/* Body */}
      {nwLoading ? (
        <div className="flex-1 flex items-center justify-center">
          <div className="w-6 h-6 border-2 border-gray-200 border-t-gray-700 rounded-full animate-spin" />
        </div>
      ) : !nw ? (
        <div className="flex-1 flex items-center justify-center">
          <p className="text-sm text-gray-400">Impossible de charger les données.</p>
        </div>
      ) : (
        <div className="flex-1 min-h-0 grid grid-cols-[380px_1fr] gap-4 px-6 pb-6">

          {/* ── Colonne gauche ── */}
          <div className="flex flex-col gap-4 min-h-0">

            {/* KPI */}
            <div className="bg-white rounded-2xl border border-gray-200 px-6 py-5 flex-none">
              <p className="text-[10px] text-gray-400 uppercase tracking-wider font-semibold mb-1">Patrimoine net total</p>
              <p className="text-4xl font-semibold text-gray-900 tabular-nums">{fmt(nw.total_eur)}</p>
              <p className="text-xs text-gray-400 mt-1.5">
                {nw.profiles.length} profil{nw.profiles.length > 1 ? 's' : ''} · en EUR
                {nw.at && ` · au ${new Date(nw.at).toLocaleDateString('fr-FR')}`}
              </p>
            </div>

            {/* Répartition */}
            <div className="bg-white rounded-2xl border border-gray-200 px-6 py-5 flex-1 min-h-0 flex flex-col">
              <p className="text-[10px] text-gray-400 uppercase tracking-wider font-semibold mb-4 flex-none">
                Répartition du patrimoine
              </p>
              <div className="flex-1 min-h-0">
                {Object.keys(nw.by_type).length > 0 ? (
                  <WorkspaceDonut
                    slices={TYPE_ORDER.filter((k) => k in nw.by_type).map((k) => ({
                      key: k, label: TYPE_LABELS[k] ?? k,
                      value: parseFloat(nw.by_type[k]),
                      color: TYPE_COLORS[k] ?? '#9ca3af',
                    }))}
                  />
                ) : (
                  <div className="flex items-center justify-center h-full text-sm text-gray-400">Aucune donnée</div>
                )}
              </div>
            </div>
          </div>

          {/* ── Colonne droite ── */}
          <div className="flex flex-col gap-4 min-h-0">

            {/* Par profil */}
            <div className="flex-none">
              <p className="text-[10px] text-gray-400 uppercase tracking-wider font-semibold mb-2">Par profil</p>
              <div className="grid grid-cols-2 gap-3">
                {nw.profiles.map((p, idx) => {
                  const total = parseFloat(p.total_eur)
                  const grandTotal = parseFloat(nw.total_eur)
                  const pct = grandTotal ? Math.round((total / grandTotal) * 100) : 0
                  const color = PROFILE_COLORS[idx % PROFILE_COLORS.length]
                  return (
                    <button key={p.profile_id} onClick={() => handleSelectProfile(p.profile_id, p.display_name)}
                      className="bg-white rounded-2xl border border-gray-200 px-4 py-3.5 text-left hover:border-gray-400 hover:shadow-sm transition-all group">
                      <div className="flex items-center justify-between mb-2">
                        <div className="flex items-center gap-2">
                          <div className="w-6 h-6 rounded-full flex items-center justify-center text-[11px] font-semibold text-white flex-shrink-0"
                            style={{ backgroundColor: color }}>
                            {p.display_name.charAt(0).toUpperCase()}
                          </div>
                          <span className="text-sm font-medium text-gray-900">{p.display_name}</span>
                        </div>
                        <span className="text-xs text-gray-400">{pct}%</span>
                      </div>
                      <p className="text-lg font-semibold text-gray-900 tabular-nums">{fmt(p.total_eur)}</p>
                      <div className="flex items-center gap-2 text-[10px] text-gray-400 mt-0.5">
                        <span>Comptes {fmt(p.accounts_eur)}</span>
                        <span>·</span>
                        <span>Portef. {fmt(p.portfolios_eur)}</span>
                      </div>
                      <div className="mt-2 h-1 bg-gray-100 rounded-full overflow-hidden">
                        <div className="h-full rounded-full" style={{ width: `${Math.max(0, pct)}%`, backgroundColor: color }} />
                      </div>
                    </button>
                  )
                })}
              </div>
            </div>

            {/* Évolution */}
            <div className="bg-white rounded-2xl border border-gray-200 px-5 py-4 flex-1 min-h-0 flex flex-col">
              <div className="flex items-center justify-between mb-3 flex-none">
                <div className="flex items-center gap-3">
                  <p className="text-[10px] text-gray-400 uppercase tracking-wider font-semibold">Évolution</p>
                  <PeriodPicker selection={period} onChange={setPeriod} minMonth="2019-01" />
                </div>
                <div className="flex items-center gap-3">
                  {nw.profiles.map((p, idx) => (
                    <div key={p.profile_id} className="flex items-center gap-1.5">
                      <div className="w-2 h-2 rounded-full" style={{ backgroundColor: PROFILE_COLORS[idx % PROFILE_COLORS.length] }} />
                      <span className="text-[10px] text-gray-500">{p.display_name}</span>
                    </div>
                  ))}
                  <div className="flex items-center gap-1.5">
                    <div className="w-2 h-2 rounded-full bg-gray-900" />
                    <span className="text-[10px] text-gray-500 font-semibold">Total</span>
                  </div>
                </div>
              </div>
              <div className="flex-1 min-h-0">
                {ts && ts.points.length > 0 ? (
                  <NwChartDetailed points={ts.points} profileNames={profileNames} profileColors={profileColors} />
                ) : (
                  <div className="flex items-center justify-center h-full text-xs text-gray-400">Pas de données historiques.</div>
                )}
              </div>
            </div>
          </div>

        </div>
      )}
    </div>
  )
}
