import { useCurrency } from '../../context/CurrencyContext'
import type { BudgetSynthesis } from '../../lib/budgetApi'

function parseAmount(s: string): number {
  return parseFloat(s) || 0
}

function KpiCard({
  label,
  actual,
  planned,
  pct,
  delta,
  deltaPrevLabel,
  color,
}: {
  label: string
  actual: number
  planned: number
  pct: number | null
  delta: number | null
  deltaPrevLabel: string
  color: 'green' | 'red' | 'blue'
}) {
  const { format } = useCurrency()
  const colorMap = {
    green: 'text-emerald-600 dark:text-emerald-400',
    red: 'text-red-500 dark:text-red-400',
    blue: 'text-blue-600 dark:text-blue-400',
  }
  const deltaColor = delta == null ? '' : delta >= 0 ? 'text-emerald-500' : 'text-red-400'

  return (
    <div className="bg-white dark:bg-gray-800 rounded-xl border border-gray-100 dark:border-gray-700 p-4 flex flex-col gap-1">
      <p className="text-xs text-gray-500 dark:text-gray-400 uppercase tracking-wide">{label}</p>
      <p className={`text-xl font-bold tabular-nums ${colorMap[color]}`}>
        {format(actual, 'EUR')}
      </p>
      {planned !== 0 && (
        <p className="text-xs text-gray-400 dark:text-gray-500">
          prévu {format(planned, 'EUR')}
        </p>
      )}
      {pct !== null && (
        <p className="text-xs font-medium text-gray-500">{pct.toFixed(0)} %</p>
      )}
      {delta !== null && (
        <p className={`text-xs font-medium ${deltaColor}`}>
          {delta >= 0 ? '+' : ''}{format(delta, 'EUR')} vs {deltaPrevLabel}
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

  const incPct = incPlanned > 0 ? (incActual / incPlanned * 100) : null
  const expPct = expPlanned > 0 ? (expActual / expPlanned * 100) : null

  const prevIncActual = prevSynthesis ? Math.abs(parseAmount(prevSynthesis.total_income_actual)) : null
  const prevExpActual = prevSynthesis ? Math.abs(parseAmount(prevSynthesis.total_expense_actual)) : null
  const prevNetActual = prevSynthesis ? parseAmount(prevSynthesis.net_actual) : null

  const incDelta = prevIncActual != null ? incActual - prevIncActual : null
  const expDelta = prevExpActual != null ? expActual - prevExpActual : null
  const netDelta = prevNetActual != null ? netActual - prevNetActual : null

  return (
    <div className="grid grid-cols-3 gap-4">
      <KpiCard
        label="Revenus"
        actual={incActual}
        planned={incPlanned}
        pct={incPct}
        delta={incDelta}
        deltaPrevLabel={prevMonthLabel}
        color="green"
      />
      <KpiCard
        label="Dépenses"
        actual={expActual}
        planned={expPlanned}
        pct={expPct}
        delta={expDelta != null ? -expDelta : null}
        deltaPrevLabel={prevMonthLabel}
        color="red"
      />
      <KpiCard
        label="Solde net"
        actual={netActual}
        planned={netPlanned}
        pct={null}
        delta={netDelta}
        deltaPrevLabel={prevMonthLabel}
        color={netActual >= 0 ? 'blue' : 'red'}
      />
    </div>
  )
}
