import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Cell,
  ResponsiveContainer,
} from 'recharts'
import type { BudgetComparison } from '../../lib/budgetApi'
import { useCurrency } from '../../context/CurrencyContext'

interface Props {
  rows: BudgetComparison[]
}

export default function BudgetBarChart({ rows }: Props) {
  const { format } = useCurrency()

  const catRows = rows
    .filter(r => r.subcategory === null)
    .map(r => ({
      name: r.category,
      actual: Math.abs(parseFloat(r.actual)),
      planned: parseFloat(r.planned),
      percent: parseFloat(r.percent),
    }))
    .filter(r => r.actual > 0 || r.planned > 0)
    .sort((a, b) => b.actual - a.actual)
    .slice(0, 10)

  if (catRows.length === 0) {
    return null
  }

  return (
    <div className="bg-white dark:bg-gray-800 rounded-xl border border-gray-100 dark:border-gray-700 p-4">
      <p className="text-xs font-semibold text-gray-500 dark:text-gray-400 uppercase tracking-wide mb-4">
        Prévu vs réel par catégorie
      </p>
      <ResponsiveContainer width="100%" height={catRows.length * 42 + 20}>
        <BarChart
          layout="vertical"
          data={catRows}
          margin={{ top: 0, right: 16, left: 80, bottom: 0 }}
          barGap={2}
          barCategoryGap={8}
        >
          <CartesianGrid strokeDasharray="3 3" horizontal={false} stroke="#e5e7eb" />
          <XAxis
            type="number"
            tick={{ fontSize: 11 }}
            tickFormatter={v => format(v, 'EUR').replace(/\s/g, '\u00a0')}
          />
          <YAxis type="category" dataKey="name" tick={{ fontSize: 12 }} width={80} />
          <Tooltip
            formatter={(value, name) => [format(Number(value ?? 0), 'EUR'), name === 'planned' ? 'Prévu' : 'Réel']}
            contentStyle={{ fontSize: 12 }}
          />
          <Bar dataKey="planned" name="Prévu" fill="#d1d5db" radius={[0, 3, 3, 0]} maxBarSize={14} />
          <Bar dataKey="actual" name="Réel" radius={[0, 3, 3, 0]} maxBarSize={14}>
            {catRows.map((row, i) => (
              <Cell
                key={i}
                fill={row.percent > 100 ? '#ef4444' : row.percent >= 80 ? '#f59e0b' : '#10b981'}
              />
            ))}
          </Bar>
        </BarChart>
      </ResponsiveContainer>
    </div>
  )
}
