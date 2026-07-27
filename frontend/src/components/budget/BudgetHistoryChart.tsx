import {
  ComposedChart,
  Bar,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer,
} from 'recharts'
import { useBudgetHistory } from '../../hooks/useBudget'
import { useCurrency } from '../../context/CurrencyContext'

function shortMonth(m: string): string {
  const [y, mo] = m.split('-').map(Number)
  return new Date(y, mo - 1, 1).toLocaleDateString('fr-FR', { month: 'short' })
}

export default function BudgetHistoryChart() {
  const { data, isLoading } = useBudgetHistory(6)
  const { format } = useCurrency()

  if (isLoading || !data) {
    return (
      <div className="bg-white dark:bg-gray-800 rounded-xl border border-gray-100 dark:border-gray-700 p-4">
        <div className="h-48 animate-pulse bg-gray-100 dark:bg-gray-700 rounded" />
      </div>
    )
  }

  const chartData = data.months.map((m) => ({
    name: shortMonth(m.month),
    Revenus: parseFloat(m.income_actual),
    Dépenses: Math.abs(parseFloat(m.expense_actual)),
    'Taux épargne': parseFloat(m.savings_rate ?? '0') * 100,
  }))

  return (
    <div className="bg-white dark:bg-gray-800 rounded-xl border border-gray-100 dark:border-gray-700 p-4 flex flex-col">
      <p className="text-xs font-semibold text-gray-500 dark:text-gray-400 uppercase tracking-wide mb-3">
        Évolution 6 mois
      </p>
      <div style={{ minHeight: 200 }}>
        <ResponsiveContainer width="100%" height={220}>
          <ComposedChart data={chartData} margin={{ top: 4, right: 8, left: 0, bottom: 0 }}>
            <CartesianGrid strokeDasharray="3 3" stroke="#e5e7eb" />
            <XAxis dataKey="name" tick={{ fontSize: 11 }} />
            <YAxis
              yAxisId="left"
              tick={{ fontSize: 11 }}
              tickFormatter={(v) => format(v, 'EUR')}
              width={70}
            />
            <YAxis
              yAxisId="right"
              orientation="right"
              tick={{ fontSize: 11 }}
              tickFormatter={(v) => `${v.toFixed(0)} %`}
              width={42}
              domain={[0, (dataMax: number) => Math.max(40, Math.ceil(dataMax / 10) * 10)]}
            />
            <Tooltip
              formatter={(value, name) => {
                if (name === 'Taux épargne')
                  return [`${Number(value ?? 0).toFixed(1)} %`, String(name)]
                return [format(Number(value ?? 0), 'EUR'), String(name ?? '')]
              }}
              contentStyle={{ fontSize: 12 }}
            />
            <Legend iconSize={10} wrapperStyle={{ fontSize: 12 }} />
            <Bar yAxisId="left" dataKey="Revenus" fill="#10b981" radius={[3, 3, 0, 0]} maxBarSize={28} />
            <Bar yAxisId="left" dataKey="Dépenses" fill="#f87171" radius={[3, 3, 0, 0]} maxBarSize={28} />
            <Line
              yAxisId="right"
              type="monotone"
              dataKey="Taux épargne"
              stroke="#f59e0b"
              strokeWidth={2}
              dot={{ r: 3 }}
            />
          </ComposedChart>
        </ResponsiveContainer>
      </div>
    </div>
  )
}
