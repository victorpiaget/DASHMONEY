import { useState } from 'react'
import { PieChart, Pie, Cell, Legend, Tooltip, ResponsiveContainer } from 'recharts'
import type { BudgetBuckets, BudgetComparison } from '../../lib/budgetApi'
import { useCurrency } from '../../context/CurrencyContext'

const CATEGORY_COLORS = ['#10b981', '#3b82f6', '#f59e0b', '#ef4444', '#8b5cf6', '#ec4899', '#14b8a6', '#f97316']
const NATURE_COLORS = {
  Besoins: '#3b82f6',
  Envies: '#f59e0b',
  Épargne: '#10b981',
  'Non classé': '#facc15',
}

type ViewMode = 'nature' | 'category'

interface Props {
  rows: BudgetComparison[]
  buckets: BudgetBuckets | undefined
}

function parseAbs(s: string): number {
  return Math.abs(parseFloat(s) || 0)
}

export default function BudgetExpenseDonut({ rows, buckets }: Props) {
  const [view, setView] = useState<ViewMode>('nature')
  const { format } = useCurrency()

  const natureData = buckets
    ? [
        { name: 'Besoins', value: parseAbs(buckets.needs) },
        { name: 'Envies', value: parseAbs(buckets.wants) },
        { name: 'Épargne', value: parseAbs(buckets.savings) },
        { name: 'Non classé', value: parseAbs(buckets.uncategorized) },
      ].filter((d) => d.value > 0)
    : []

  const categoryData = rows
    .filter((r) => r.subcategory === null)
    .map((r) => ({ name: r.category, value: parseAbs(r.actual) }))
    .filter((d) => d.value > 0)
    .sort((a, b) => b.value - a.value)

  const data = view === 'nature' ? natureData : categoryData

  return (
    <div className="bg-white dark:bg-gray-800 rounded-xl border border-gray-100 dark:border-gray-700 p-4 flex flex-col">
      <div className="flex items-center justify-between mb-3">
        <p className="text-xs font-semibold text-gray-500 dark:text-gray-400 uppercase tracking-wide">
          Répartition dépenses
        </p>
        <div className="inline-flex rounded-lg border border-gray-200 dark:border-gray-700 p-0.5 text-xs bg-gray-50 dark:bg-gray-900">
          {(['nature', 'category'] as const).map((v) => (
            <button
              key={v}
              onClick={() => setView(v)}
              className={`px-2.5 py-1 rounded-md transition-all ${
                view === v
                  ? 'bg-white dark:bg-gray-700 text-gray-900 dark:text-white shadow-sm'
                  : 'text-gray-500 dark:text-gray-400 hover:text-gray-700 dark:hover:text-gray-200'
              }`}
            >
              {v === 'nature' ? 'Nature' : 'Catégories'}
            </button>
          ))}
        </div>
      </div>

      {data.length === 0 ? (
        <div className="flex-1 flex items-center justify-center min-h-[200px]">
          <p className="text-sm text-gray-400 dark:text-gray-500">Aucune dépense ce mois</p>
        </div>
      ) : (
        <div className="flex-1" style={{ minHeight: 200 }}>
          <ResponsiveContainer width="100%" height={220}>
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
                {data.map((d, i) => (
                  <Cell
                    key={i}
                    fill={
                      view === 'nature'
                        ? NATURE_COLORS[d.name as keyof typeof NATURE_COLORS] ?? '#94a3b8'
                        : CATEGORY_COLORS[i % CATEGORY_COLORS.length]
                    }
                  />
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
      )}
    </div>
  )
}
