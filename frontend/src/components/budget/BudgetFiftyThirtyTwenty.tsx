import { Link } from 'react-router-dom'
import type { BudgetBuckets } from '../../lib/budgetApi'

function parseAmount(s: string): number {
  return parseFloat(s) || 0
}

interface Props {
  buckets: BudgetBuckets | undefined
}

const COLORS = {
  needs: 'bg-blue-500',
  wants: 'bg-amber-500',
  savings: 'bg-emerald-500',
  uncat: 'bg-yellow-400',
}

const TARGETS = { needs: 50, wants: 30, savings: 20 } as const

function Bar({
  label,
  pct,
  target,
  colorClass,
  hint,
}: {
  label: string
  pct: number
  target?: number
  colorClass: string
  hint?: React.ReactNode
}) {
  const drift = target != null ? pct - target : 0
  const showWarning = target != null && Math.abs(drift) > 5
  const overTooMuch = target != null && (label === 'Besoins' || label === 'Envies') && pct > target + 5
  const underTooMuch = target != null && label === 'Épargne' && pct < target - 5
  const pctColor = overTooMuch || underTooMuch
    ? 'text-red-500 dark:text-red-400'
    : showWarning
      ? 'text-amber-500 dark:text-amber-400'
      : 'text-gray-700 dark:text-gray-300'

  return (
    <div className="space-y-1">
      <div className="flex items-center justify-between text-xs">
        <span className="font-medium text-gray-700 dark:text-gray-300">{label}</span>
        <span className={`tabular-nums font-medium ${pctColor}`}>
          {pct.toFixed(0)} %
          {target != null && (
            <span className="text-gray-400 dark:text-gray-500 ml-1.5 font-normal">
              (objectif {target} %)
            </span>
          )}
        </span>
      </div>
      <div className="w-full bg-gray-100 dark:bg-gray-700 rounded-full h-2.5">
        <div
          className={`${colorClass} h-2.5 rounded-full transition-all duration-500`}
          style={{ width: `${Math.min(pct, 100)}%` }}
        />
      </div>
      {hint && <div className="text-xs text-amber-600 dark:text-amber-400">{hint}</div>}
    </div>
  )
}

export default function BudgetFiftyThirtyTwenty({ buckets }: Props) {
  const needsAbs = Math.abs(parseAmount(buckets?.needs ?? '0'))
  const wantsAbs = Math.abs(parseAmount(buckets?.wants ?? '0'))
  const savingsAbs = Math.abs(parseAmount(buckets?.savings ?? '0'))
  const uncatAbs = Math.abs(parseAmount(buckets?.uncategorized ?? '0'))

  const total = needsAbs + wantsAbs + savingsAbs + uncatAbs

  if (total <= 0) {
    return (
      <div className="bg-white dark:bg-gray-800 rounded-xl border border-gray-100 dark:border-gray-700 p-5">
        <p className="text-xs font-semibold text-gray-500 dark:text-gray-400 uppercase tracking-wide mb-3">
          Ta répartition vs 50 / 30 / 20
        </p>
        <p className="text-sm text-gray-400 dark:text-gray-500">
          Pas encore de dépenses ce mois-ci pour calculer la répartition.
        </p>
      </div>
    )
  }

  const pct = (v: number) => (v / total) * 100
  const needsPct = pct(needsAbs)
  const wantsPct = pct(wantsAbs)
  const savingsPct = pct(savingsAbs)
  const uncatPct = pct(uncatAbs)

  return (
    <div className="bg-white dark:bg-gray-800 rounded-xl border border-gray-100 dark:border-gray-700 p-5 space-y-4">
      <div className="flex items-center justify-between">
        <p className="text-xs font-semibold text-gray-500 dark:text-gray-400 uppercase tracking-wide">
          Ta répartition vs 50 / 30 / 20
        </p>
      </div>

      <Bar label="Besoins" pct={needsPct} target={TARGETS.needs} colorClass={COLORS.needs} />
      <Bar label="Envies" pct={wantsPct} target={TARGETS.wants} colorClass={COLORS.wants} />
      <Bar label="Épargne" pct={savingsPct} target={TARGETS.savings} colorClass={COLORS.savings} />

      {uncatAbs > 0 && (
        <Bar
          label="Non classé"
          pct={uncatPct}
          colorClass={COLORS.uncat}
          hint={
            <Link to="/categories" className="hover:underline">
              Classer mes catégories →
            </Link>
          }
        />
      )}
    </div>
  )
}
