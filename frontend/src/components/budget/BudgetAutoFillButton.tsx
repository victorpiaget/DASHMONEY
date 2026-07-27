import { useEffect, useMemo, useState } from 'react'
import { useBudgetAutoFill, useBudgetEnvelopes, useUpsertEnvelope } from '../../hooks/useBudget'
import { useCurrency } from '../../context/CurrencyContext'
import type { BudgetAutoBudgetSuggestion, CategoryNature } from '../../lib/budgetApi'

interface Props {
  kind: 'INCOME' | 'EXPENSE'
}

const NATURE_BADGE: Record<CategoryNature | 'NULL', { label: string; className: string }> = {
  NEED: { label: 'Besoin', className: 'bg-blue-50 text-blue-700 dark:bg-blue-900/30 dark:text-blue-300' },
  WANT: { label: 'Envie', className: 'bg-amber-50 text-amber-700 dark:bg-amber-900/30 dark:text-amber-300' },
  SAVING: { label: 'Épargne', className: 'bg-emerald-50 text-emerald-700 dark:bg-emerald-900/30 dark:text-emerald-300' },
  NULL: { label: 'Non classé', className: 'bg-yellow-50 text-yellow-700 dark:bg-yellow-900/30 dark:text-yellow-300' },
}

function envelopeKey(cat: string, sub: string | null) {
  return `${cat}|${sub ?? ''}`
}

export default function BudgetAutoFillButton({ kind }: Props) {
  const [open, setOpen] = useState(false)
  const { data, isLoading } = useBudgetAutoFill(3, open)
  const envelopes = useBudgetEnvelopes()
  const upsert = useUpsertEnvelope()
  const { format } = useCurrency()
  const [selected, setSelected] = useState<Set<string>>(new Set())
  const [applying, setApplying] = useState(false)

  const existingSet = useMemo(() => {
    const s = new Map<string, string>()
    for (const e of envelopes.data ?? []) {
      if (e.kind !== kind) continue
      s.set(envelopeKey(e.category, e.subcategory), e.amount)
    }
    return s
  }, [envelopes.data, kind])

  const filtered: BudgetAutoBudgetSuggestion[] = (data?.suggestions ?? []).filter((s) => s.kind === kind)

  useEffect(() => {
    if (!open) {
      setSelected(new Set())
      return
    }
    const next = new Set<string>()
    for (const s of filtered) {
      const key = envelopeKey(s.category, s.subcategory)
      if (!existingSet.has(key)) next.add(key)
    }
    setSelected(next)
  }, [open, data, existingSet]) // eslint-disable-line react-hooks/exhaustive-deps

  function toggle(key: string) {
    setSelected((prev) => {
      const next = new Set(prev)
      if (next.has(key)) next.delete(key)
      else next.add(key)
      return next
    })
  }

  async function applyAll() {
    setApplying(true)
    try {
      for (const s of filtered) {
        const key = envelopeKey(s.category, s.subcategory)
        if (!selected.has(key)) continue
        await upsert.mutateAsync({
          category: s.category,
          subcategory: s.subcategory ?? null,
          kind: s.kind,
          amount: s.median_amount,
        })
      }
      setOpen(false)
    } finally {
      setApplying(false)
    }
  }

  const label = kind === 'INCOME' ? 'Pré-remplir revenus' : 'Pré-remplir dépenses'

  return (
    <>
      <button
        onClick={() => setOpen(true)}
        className="text-xs font-medium text-gray-700 dark:text-gray-200 border border-dashed border-gray-300 dark:border-gray-600 rounded-lg px-3 py-1.5 hover:bg-gray-50 dark:hover:bg-gray-700/50 transition-colors"
      >
        ⚡ {label}
      </button>

      {open && (
        <div
          className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 px-4"
          onClick={() => !applying && setOpen(false)}
        >
          <div
            className="w-full max-w-2xl bg-white dark:bg-gray-800 rounded-2xl border border-gray-100 dark:border-gray-700 shadow-xl max-h-[85vh] flex flex-col"
            onClick={(e) => e.stopPropagation()}
          >
            <div className="px-5 py-4 border-b border-gray-100 dark:border-gray-700 flex items-start justify-between gap-3">
              <div>
                <h3 className="text-sm font-semibold text-gray-900 dark:text-white">
                  Pré-remplir basé sur les 3 derniers mois
                </h3>
                <p className="text-xs text-gray-500 dark:text-gray-400 mt-0.5">
                  Médiane du montant mensuel par catégorie
                  {data ? ` — ${data.from_month} → ${data.to_month}` : ''}.
                  Les enveloppes existantes sont conservées (cochez pour écraser).
                </p>
              </div>
              <button
                onClick={() => !applying && setOpen(false)}
                className="text-gray-400 dark:text-gray-500 hover:text-gray-700 dark:hover:text-gray-200 text-xl leading-none"
              >
                ×
              </button>
            </div>

            <div className="flex-1 overflow-auto">
              {isLoading ? (
                <div className="px-5 py-8 text-center">
                  <div className="inline-block w-5 h-5 border-2 border-gray-200 border-t-gray-700 rounded-full animate-spin dark:border-gray-700 dark:border-t-gray-300" />
                </div>
              ) : filtered.length === 0 ? (
                <p className="px-5 py-8 text-center text-sm text-gray-400 dark:text-gray-500">
                  Aucune suggestion (il faut au moins 2 mois avec transactions sur la même catégorie).
                </p>
              ) : (
                <table className="w-full text-sm">
                  <thead>
                    <tr className="text-xs text-gray-400 uppercase tracking-wide border-b border-gray-100 dark:border-gray-700">
                      <th className="px-4 py-2 w-10"></th>
                      <th className="px-4 py-2 text-left font-medium">Catégorie</th>
                      <th className="px-4 py-2 text-right font-medium">Médiane</th>
                      <th className="px-4 py-2 text-right font-medium">Mois</th>
                      <th className="px-4 py-2 text-right font-medium">Existant</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-gray-50 dark:divide-gray-700/50">
                    {filtered.map((s) => {
                      const key = envelopeKey(s.category, s.subcategory)
                      const existing = existingSet.get(key)
                      const isSelected = selected.has(key)
                      const natureKey: CategoryNature | 'NULL' = s.nature ?? 'NULL'
                      const badge = NATURE_BADGE[natureKey]
                      return (
                        <tr key={key} className="hover:bg-gray-50 dark:hover:bg-gray-700/30">
                          <td className="px-4 py-2">
                            <input
                              type="checkbox"
                              checked={isSelected}
                              onChange={() => toggle(key)}
                              className="rounded"
                            />
                          </td>
                          <td className="px-4 py-2">
                            <div className="flex items-center gap-2 flex-wrap">
                              <span className="font-medium text-gray-800 dark:text-gray-200">{s.category}</span>
                              {s.subcategory && (
                                <span className="text-gray-500 dark:text-gray-400">→ {s.subcategory}</span>
                              )}
                              {kind === 'EXPENSE' && (
                                <span className={`text-[10px] font-medium rounded px-1.5 py-0.5 ${badge.className}`}>
                                  {badge.label}
                                </span>
                              )}
                            </div>
                          </td>
                          <td className="px-4 py-2 text-right tabular-nums text-gray-700 dark:text-gray-300">
                            {format(parseFloat(s.median_amount), 'EUR')}
                          </td>
                          <td className="px-4 py-2 text-right text-xs text-gray-500 dark:text-gray-400 tabular-nums">
                            {s.occurrences} / 3
                          </td>
                          <td className="px-4 py-2 text-right text-xs tabular-nums">
                            {existing ? (
                              <span className="text-gray-400 dark:text-gray-500">
                                {format(parseFloat(existing), 'EUR')}
                              </span>
                            ) : (
                              <span className="text-gray-300 dark:text-gray-600">—</span>
                            )}
                          </td>
                        </tr>
                      )
                    })}
                  </tbody>
                </table>
              )}
            </div>

            <div className="px-5 py-3 border-t border-gray-100 dark:border-gray-700 flex items-center justify-between gap-3">
              <span className="text-xs text-gray-500 dark:text-gray-400">
                {selected.size} suggestion{selected.size > 1 ? 's' : ''} sélectionnée{selected.size > 1 ? 's' : ''}
              </span>
              <div className="flex gap-2">
                <button
                  onClick={() => !applying && setOpen(false)}
                  className="text-xs font-medium px-3 py-1.5 rounded-lg text-gray-600 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-700 transition-colors"
                >
                  Annuler
                </button>
                <button
                  onClick={applyAll}
                  disabled={applying || selected.size === 0}
                  className="text-xs font-medium px-3 py-1.5 rounded-lg bg-gray-900 text-white hover:bg-gray-800 dark:bg-white dark:text-gray-900 dark:hover:bg-gray-100 disabled:opacity-40 transition-colors"
                >
                  {applying ? 'Application…' : 'Appliquer'}
                </button>
              </div>
            </div>
          </div>
        </div>
      )}
    </>
  )
}
