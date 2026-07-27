import { useCurrency } from '../../context/CurrencyContext'
import type { BudgetSynthesis } from '../../lib/budgetApi'

function parseAmount(s: string): number {
  return parseFloat(s) || 0
}

type KpiVariant = 'money' | 'rate'

function KpiCard({
  label,
  variant,
  actual,
  planned,
  pct,
  delta,
  deltaSuffix,
  deltaPrevLabel,
  color,
}: {
  label: string
  variant: KpiVariant
  actual: number
  planned: number
  pct: number | null
  delta: number | null
  deltaSuffix: string
  deltaPrevLabel: string
  color: 'green' | 'red' | 'blue' | 'amber'
}) {
  const { format } = useCurrency()
  const colorMap = {
    green: 'text-emerald-600 dark:text-emerald-400',
    red: 'text-red-500 dark:text-red-400',
    blue: 'text-blue-600 dark:text-blue-400',
    amber: 'text-amber-600 dark:text-amber-400',
  }
  const deltaColor = delta == null ? '' : delta >= 0 ? 'text-emerald-500' : 'text-red-400'
  const formatValue = (v: number) =>
    variant === 'rate' ? `${(v * 100).toFixed(1)} %` : format(v, 'EUR')
  const formatDelta = (v: number) => {
    if (variant === 'rate') {
      const pts = (v * 100)
      return `${pts >= 0 ? '+' : ''}${pts.toFixed(1)} pts`
    }
    return `${v >= 0 ? '+' : ''}${format(v, 'EUR')}`
  }

  return (
    <div className="bg-white dark:bg-gray-800 rounded-xl border border-gray-100 dark:border-gray-700 p-4 flex flex-col gap-1">
      <p className="text-xs text-gray-500 dark:text-gray-400 uppercase tracking-wide">{label}</p>
      <p className={`text-xl font-bold tabular-nums ${colorMap[color]}`}>
        {formatValue(actual)}
      </p>
      {variant === 'money' && planned !== 0 && (
        <p className="text-xs text-gray-400 dark:text-gray-500">
          prévu {format(planned, 'EUR')}
        </p>
      )}
      {pct !== null && (
        <p className="text-xs font-medium text-gray-500">{pct.toFixed(0)} %</p>
      )}
      {delta !== null && (
        <p className={`text-xs font-medium ${deltaColor}`}>
          {formatDelta(delta)} {deltaSuffix} {deltaPrevLabel}
        </p>
      )}
    </div>
  )
}

interface Props {
  synthesis: BudgetSynthesis | undefined
  prevSynthesis: BudgetSynthesis | undefined
  prevMonthLabel: string
}

export default function BudgetKpiCards({ synthesis, prevSynthesis, prevMonthLabel }: Props) {
  const incActual = Math.abs(parseAmount(synthesis?.total_income_actual ?? '0'))
  const incPlanned = parseAmount(synthesis?.total_income_planned ?? '0')
  const expActual = Math.abs(parseAmount(synthesis?.total_expense_actual ?? '0'))
  const expPlanned = parseAmount(synthesis?.total_expense_planned ?? '0')
  const netActual = parseAmount(synthesis?.net_actual ?? '0')
  const netPlanned = parseAmount(synthesis?.net_planned ?? '0')
  const savingsRate = parseAmount(synthesis?.savings_rate ?? '0')

  const incPct = incPlanned > 0 ? (incActual / incPlanned * 100) : null
  const expPct = expPlanned > 0 ? (expActual / expPlanned * 100) : null

  const prevIncActual = prevSynthesis ? Math.abs(parseAmount(prevSynthesis.total_income_actual)) : null
  const prevExpActual = prevSynthesis ? Math.abs(parseAmount(prevSynthesis.total_expense_actual)) : null
  const prevNetActual = prevSynthesis ? parseAmount(prevSynthesis.net_actual) : null
  const prevSavingsRate = prevSynthesis ? parseAmount(prevSynthesis.savings_rate) : null

  const incDelta = prevIncActual != null ? incActual - prevIncActual : null
  const expDelta = prevExpActual != null ? expActual - prevExpActual : null
  const netDelta = prevNetActual != null ? netActual - prevNetActual : null
  const savingsDelta = prevSavingsRate != null ? savingsRate - prevSavingsRate : null

  return (
    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
      <KpiCard
        label="Revenus"
        variant="money"
        actual={incActual}
        planned={incPlanned}
        pct={incPct}
        delta={incDelta}
        deltaSuffix="vs"
        deltaPrevLabel={prevMonthLabel}
        color="green"
      />
      <KpiCard
        label="Dépenses"
        variant="money"
        actual={expActual}
        planned={expPlanned}
        pct={expPct}
        delta={expDelta != null ? -expDelta : null}
        deltaSuffix="vs"
        deltaPrevLabel={prevMonthLabel}
        color="red"
      />
      <KpiCard
        label="Solde net"
        variant="money"
        actual={netActual}
        planned={netPlanned}
        pct={null}
        delta={netDelta}
        deltaSuffix="vs"
        deltaPrevLabel={prevMonthLabel}
        color={netActual >= 0 ? 'blue' : 'red'}
      />
      <KpiCard
        label="Taux d'épargne"
        variant="rate"
        actual={savingsRate}
        planned={0}
        pct={null}
        delta={savingsDelta}
        deltaSuffix="vs"
        deltaPrevLabel={prevMonthLabel}
        color="amber"
      />
    </div>
  )
}
