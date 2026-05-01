import { useState } from 'react'
import { useCurrency } from '../../context/CurrencyContext'
import EditableAmount from './EditableAmount'

function parseAmount(s: string): number {
  return parseFloat(s) || 0
}

function expenseBarColor(pct: number): string {
  if (pct > 100) return 'bg-red-500'
  if (pct >= 80) return 'bg-orange-400'
  return 'bg-emerald-500'
}

function incomeBarColor(pct: number): string {
  if (pct >= 100) return 'bg-emerald-500'
  if (pct >= 80) return 'bg-orange-400'
  return 'bg-red-400'
}

export interface CompRow {
  category: string
  subcategory: string | null
  kind: string
  planned: string
  actual: string
  delta: string
  percent: string
}

interface Props {
  title: string
  rows: CompRow[]
  kind: 'INCOME' | 'EXPENSE'
  onSave: (category: string, subcategory: string | null, amount: string) => void
  onDelete: (category: string, subcategory: string | null) => void
  footer?: React.ReactNode
}

export default function BudgetCategoryTable({ title, rows, kind, onSave, onDelete, footer }: Props) {
  const [expanded, setExpanded] = useState<Set<string>>(new Set())
  const { format } = useCurrency()

  const explicitCatRows = rows.filter(r => r.subcategory === null)
  const subRows = rows.filter(r => r.subcategory !== null)

  // Reconstruire un row "catégorie parent" agrégé pour les catégories qui n'ont
  // que des sous-catégories (sinon le tableau apparaît vide alors que les KPI
  // ont bien des données — bug historique sur les Revenus).
  const explicitCatNames = new Set(explicitCatRows.map(r => r.category))
  const orphanCatNames = Array.from(
    new Set(subRows.filter(s => !explicitCatNames.has(s.category)).map(s => s.category)),
  )

  const synthesizedCatRows: CompRow[] = orphanCatNames.map(cat => {
    const subs = subRows.filter(s => s.category === cat)
    const planned = subs.reduce((acc, s) => acc + parseAmount(s.planned), 0)
    const actual = subs.reduce((acc, s) => acc + parseAmount(s.actual), 0)
    const delta = kind === 'EXPENSE'
      ? Math.abs(actual) - planned
      : actual - planned
    const percent = planned > 0
      ? (Math.abs(actual) / planned) * 100
      : (actual !== 0 ? 100 : 0)
    return {
      category: cat,
      subcategory: null,
      kind,
      planned: planned.toFixed(2),
      actual: actual.toFixed(2),
      delta: delta.toFixed(2),
      percent: percent.toFixed(2),
    }
  })

  const catRows = [...explicitCatRows, ...synthesizedCatRows]
    .sort((a, b) => Math.abs(parseAmount(b.actual)) - Math.abs(parseAmount(a.actual)))

  function toggle(cat: string) {
    setExpanded(prev => {
      const next = new Set(prev)
      if (next.has(cat)) next.delete(cat)
      else next.add(cat)
      return next
    })
  }

  const barColor = kind === 'EXPENSE' ? expenseBarColor : incomeBarColor

  return (
    <div className="bg-white dark:bg-gray-800 rounded-xl border border-gray-100 dark:border-gray-700 overflow-hidden">
      <div className="px-4 py-3 border-b border-gray-100 dark:border-gray-700">
        <h2 className="text-sm font-semibold text-gray-700 dark:text-gray-300">{title}</h2>
      </div>
      <table className="w-full text-sm">
        <thead>
          <tr className="text-xs text-gray-400 uppercase tracking-wide border-b border-gray-50 dark:border-gray-700">
            <th className="px-4 py-2 text-left font-medium">Catégorie</th>
            <th className="px-4 py-2 text-right font-medium">Réel</th>
            <th className="px-4 py-2 text-right font-medium">Prévu</th>
            <th className="px-4 py-2 text-right font-medium">Écart</th>
            <th className="px-4 py-2 w-28">Progression</th>
            <th className="px-4 py-2 text-right font-medium w-14">%</th>
          </tr>
        </thead>
        <tbody className="divide-y divide-gray-50 dark:divide-gray-700/50">
          {catRows.map(row => {
            const pct = parseFloat(row.percent)
            const hasPlanned = parseFloat(row.planned) > 0
            const hasSubs = subRows.some(s => s.category === row.category)
            const isOpen = expanded.has(row.category)
            const subsForCat = subRows.filter(s => s.category === row.category)
            const delta = parseAmount(row.delta)

            return (
              <>
                <tr key={row.category} className="hover:bg-gray-50 dark:hover:bg-gray-700/30 transition-colors">
                  <td className="px-4 py-2.5">
                    <div className="flex items-center gap-2">
                      {hasSubs && (
                        <button onClick={() => toggle(row.category)} className="text-gray-400 hover:text-gray-600 text-xs w-4">
                          {isOpen ? '▾' : '▸'}
                        </button>
                      )}
                      {!hasSubs && <span className="w-4" />}
                      <span className="font-medium text-gray-800 dark:text-gray-200">{row.category}</span>
                      {hasPlanned && pct > 100 && (
                        <span className="text-xs font-semibold bg-red-100 text-red-600 dark:bg-red-900/30 dark:text-red-400 rounded px-1.5 py-0.5">Dépassé</span>
                      )}
                      {hasPlanned && pct >= 80 && pct <= 100 && (
                        <span className="text-xs font-semibold bg-orange-100 text-orange-600 dark:bg-orange-900/30 dark:text-orange-400 rounded px-1.5 py-0.5">Attention</span>
                      )}
                    </div>
                  </td>
                  <td className="px-4 py-2.5 text-right tabular-nums text-gray-700 dark:text-gray-300">
                    {format(Math.abs(parseAmount(row.actual)), 'EUR')}
                  </td>
                  <td className="px-4 py-2.5 text-right">
                    {hasSubs ? (
                      <span className="text-gray-400 text-xs italic">
                        {hasPlanned ? format(parseAmount(row.planned), 'EUR') : '—'}
                      </span>
                    ) : (
                      <EditableAmount
                        value={hasPlanned ? row.planned : null}
                        onSave={amt => onSave(row.category, null, amt)}
                        onDelete={hasPlanned ? () => onDelete(row.category, null) : undefined}
                      />
                    )}
                  </td>
                  <td className="px-4 py-2.5 text-right tabular-nums text-xs">
                    {hasPlanned ? (
                      <span className={delta > 0 ? 'text-red-500' : delta < 0 ? 'text-emerald-500' : 'text-gray-400'}>
                        {delta > 0 ? '+' : ''}{format(delta, 'EUR')}
                      </span>
                    ) : (
                      <span className="text-gray-300 dark:text-gray-600">—</span>
                    )}
                  </td>
                  <td className="px-4 py-2.5">
                    <div className="w-full bg-gray-100 dark:bg-gray-700 rounded-full h-1.5">
                      <div
                        className={`${barColor(pct)} h-1.5 rounded-full transition-all`}
                        style={{ width: `${Math.min(pct, 100)}%` }}
                      />
                    </div>
                  </td>
                  <td className="px-4 py-2.5 text-right text-xs tabular-nums text-gray-500 dark:text-gray-400">
                    {hasPlanned ? `${pct.toFixed(0)} %` : '—'}
                  </td>
                </tr>
                {isOpen && subsForCat.map(sub => {
                  const subPct = parseFloat(sub.percent)
                  const subHasPlanned = parseFloat(sub.planned) > 0
                  const subDelta = parseAmount(sub.delta)
                  return (
                    <tr key={`${sub.category}-${sub.subcategory}`} className="bg-gray-50/50 dark:bg-gray-700/20 hover:bg-gray-100/50 dark:hover:bg-gray-700/40 transition-colors">
                      <td className="px-4 py-2 pl-10">
                        <span className="text-gray-600 dark:text-gray-400">{sub.subcategory}</span>
                      </td>
                      <td className="px-4 py-2 text-right tabular-nums text-xs text-gray-600 dark:text-gray-400">
                        {format(Math.abs(parseAmount(sub.actual)), 'EUR')}
                      </td>
                      <td className="px-4 py-2 text-right text-xs">
                        <EditableAmount
                          value={subHasPlanned ? sub.planned : null}
                          onSave={amt => onSave(sub.category, sub.subcategory, amt)}
                          onDelete={subHasPlanned ? () => onDelete(sub.category, sub.subcategory) : undefined}
                        />
                      </td>
                      <td className="px-4 py-2 text-right tabular-nums text-xs">
                        {subHasPlanned ? (
                          <span className={subDelta > 0 ? 'text-red-500' : subDelta < 0 ? 'text-emerald-500' : 'text-gray-400'}>
                            {subDelta > 0 ? '+' : ''}{format(subDelta, 'EUR')}
                          </span>
                        ) : (
                          <span className="text-gray-300 dark:text-gray-600">—</span>
                        )}
                      </td>
                      <td className="px-4 py-2">
                        <div className="w-full bg-gray-100 dark:bg-gray-700 rounded-full h-1.5">
                          <div
                            className={`${barColor(subPct)} h-1.5 rounded-full transition-all`}
                            style={{ width: `${Math.min(subPct, 100)}%` }}
                          />
                        </div>
                      </td>
                      <td className="px-4 py-2 text-right text-xs tabular-nums text-gray-500 dark:text-gray-400">
                        {subHasPlanned ? `${subPct.toFixed(0)} %` : '—'}
                      </td>
                    </tr>
                  )
                })}
              </>
            )
          })}
          {catRows.length === 0 && (
            <tr>
              <td colSpan={6} className="px-4 py-6 text-center text-sm text-gray-400">
                Aucune donnée pour ce mois
              </td>
            </tr>
          )}
        </tbody>
      </table>
      {footer}
    </div>
  )
}
