import { PieChart, Pie, Cell, Legend, Tooltip, ResponsiveContainer } from 'recharts'
import type { BudgetComparison } from '../../lib/budgetApi'
import { useCurrency } from '../../context/CurrencyContext'

const COLORS = ['#10b981', '#3b82f6', '#f59e0b', '#ef4444', '#8b5cf6', '#ec4899', '#14b8a6', '#f97316']

interface Props {
  rows: BudgetComparison[]
}

export default function BudgetExpenseDonut({ rows }: Props) {
  const { format } = useCurrency()

  const data = rows
    .filter(r => r.subcategory === null)
    .map(r => ({ name: r.category, value: Math.abs(parseFloat(r.actual)) }))
    .filter(d => d.value > 0)
    .sort((a, b) => b.value - a.value)

  if (data.length === 0) {
    return (
      <div className="bg-white dark:bg-gray-800 rounded-xl border border-gray-100 dark:border-gray-700 p-4 flex flex-col">
        <p className="text-xs font-semibold text-gray-500 dark:text-gray-400 uppercase tracking-wide mb-3">Répartition dépenses</p>
        <div className="flex-1 flex items-center justify-center">
          <p className="text-sm text-gray-400 dark:text-gray-500">Aucune dépense ce mois</p>
        </div>
      </div>
    )
  }

  return (
    <div className="bg-white dark:bg-gray-800 rounded-xl border border-gray-100 dark:border-gray-700 p-4 flex flex-col">
      <p className="text-xs font-semibold text-gray-500 dark:text-gray-400 uppercase tracking-wide mb-3">Répartition dépenses</p>
      <div className="flex-1" style={{ minHeight: 200 }}>
        <ResponsiveContainer width="100%" height={200}>
          <PieChart>
            <Pie
              data={data}
              cx="40%"
              cy="50%"
              innerRadius={55}
              outerRadius={85}
              dataKey="value"
              paddingAngle={2}
            >
              {data.map((_, i) => (
                <Cell key={i} fill={COLORS[i % COLORS.length]} />
              ))}
            </Pie>
            <Tooltip
              formatter={(value) => format(Number(value ?? 0), 'EUR')}
              contentStyle={{ fontSize: 12 }}
            />
            <Legend
              layout="vertical"
              align="right"
              verticalAlign="middle"
              iconSize={10}
              iconType="circle"
              formatter={(value: string) => (
                <span className="text-xs text-gray-600 dark:text-gray-300">{value}</span>
              )}
            />
          </PieChart>
        </ResponsiveContainer>
      </div>
    </div>
  )
}
