import { useRef, useState } from 'react'
import {
  useBudgetComparison,
  useBudgetEnvelopes,
  useDeleteEnvelope,
  useUpsertEnvelope,
} from '../hooks/useBudget'
import BudgetKpiCards from '../components/budget/BudgetKpiCards'
import BudgetExpenseDonut from '../components/budget/BudgetExpenseDonut'
import BudgetHistoryChart from '../components/budget/BudgetHistoryChart'
import BudgetBarChart from '../components/budget/BudgetBarChart'
import BudgetCategoryTable from '../components/budget/BudgetCategoryTable'
import BudgetEmptyState from '../components/budget/BudgetEmptyState'
import AddEnvelopeForm from '../components/budget/AddEnvelopeForm'

// ── Helpers ──────────────────────────────────────────────────────────────────

function currentMonth(): string {
  const now = new Date()
  return `${now.getFullYear()}-${String(now.getMonth() + 1).padStart(2, '0')}`
}

function prevMonth(m: string): string {
  const [y, mo] = m.split('-').map(Number)
  if (mo === 1) return `${y - 1}-12`
  return `${y}-${String(mo - 1).padStart(2, '0')}`
}

function nextMonth(m: string): string {
  const [y, mo] = m.split('-').map(Number)
  if (mo === 12) return `${y + 1}-01`
  return `${y}-${String(mo + 1).padStart(2, '0')}`
}

function formatMonthLabel(m: string): string {
  const [y, mo] = m.split('-').map(Number)
  const d = new Date(y, mo - 1, 1)
  return d.toLocaleDateString('fr-FR', { month: 'long', year: 'numeric' })
}

function shortMonthLabel(m: string): string {
  const [y, mo] = m.split('-').map(Number)
  return new Date(y, mo - 1, 1).toLocaleDateString('fr-FR', { month: 'short' })
}

// ── BudgetPage ────────────────────────────────────────────────────────────────

export default function BudgetPage() {
  const [month, setMonth] = useState(currentMonth)
  const today = currentMonth()
  const prev = prevMonth(month)

  const { data, isLoading, error } = useBudgetComparison(month)
  const { data: prevData } = useBudgetComparison(prev)
  const upsert = useUpsertEnvelope()
  const remove = useDeleteEnvelope()
  const budgetEnvelopesQuery = useBudgetEnvelopes()

  const incomeFormRef = useRef<HTMLInputElement>(null)
  const expenseFormRef = useRef<HTMLInputElement>(null)

  function buildEnvKey(cat: string, sub: string | null, kind: string) {
    return `${cat}|${sub ?? ''}|${kind}`
  }

  const envIdMap = new Map<string, string>()
  if (budgetEnvelopesQuery.data) {
    for (const e of budgetEnvelopesQuery.data) {
      envIdMap.set(buildEnvKey(e.category, e.subcategory, e.kind), e.id)
    }
  }

  function handleSave(kind: string, category: string, subcategory: string | null, amount: string) {
    upsert.mutate({ category, subcategory, kind, amount })
  }

  function handleDelete(kind: string, category: string, subcategory: string | null) {
    const id = envIdMap.get(buildEnvKey(category, subcategory, kind))
    if (id) remove.mutate(id)
  }

  const incomeRows = data?.comparisons.filter(c => c.kind === 'INCOME') ?? []
  const expenseRows = data?.comparisons.filter(c => c.kind === 'EXPENSE') ?? []

  const hasEnvelopes = (budgetEnvelopesQuery.data?.length ?? 0) > 0
  const hasComparisons = (data?.comparisons.length ?? 0) > 0
  const showEmptyState = !isLoading && !error && !hasEnvelopes && !hasComparisons

  return (
    <div className="page-transition max-w-5xl mx-auto p-6 space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between flex-wrap gap-3">
        <div>
          <h1 className="text-xl font-semibold text-gray-900 dark:text-white">Budget prévisionnel</h1>
          <p className="text-sm text-gray-500 dark:text-gray-400 mt-0.5">Comparaison enveloppes vs réel</p>
        </div>
        <div className="flex items-center gap-2">
          <button
            onClick={() => setMonth(prevMonth(month))}
            className="p-1.5 rounded-lg hover:bg-gray-100 dark:hover:bg-gray-700 text-gray-500 dark:text-gray-400 transition-colors active:scale-[0.98]"
          >
            ‹
          </button>
          <span className="text-sm font-medium text-gray-700 dark:text-gray-300 min-w-32 text-center capitalize">
            {formatMonthLabel(month)}
          </span>
          <button
            onClick={() => setMonth(nextMonth(month))}
            className="p-1.5 rounded-lg hover:bg-gray-100 dark:hover:bg-gray-700 text-gray-500 dark:text-gray-400 transition-colors active:scale-[0.98]"
          >
            ›
          </button>
          {month !== today && (
            <button
              onClick={() => setMonth(today)}
              className="ml-1 px-2.5 py-1 text-xs font-medium text-gray-900 dark:text-white border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-800 rounded-lg hover:bg-gray-50 dark:hover:bg-gray-700 transition-colors active:scale-[0.98]"
            >
              Mois courant
            </button>
          )}
        </div>
      </div>

      {/* KPI Cards */}
      {isLoading ? (
        <div className="grid grid-cols-3 gap-4">
          {[0, 1, 2].map(i => (
            <div key={i} className="h-24 rounded-xl bg-gray-100 dark:bg-gray-800 animate-pulse" />
          ))}
        </div>
      ) : error ? (
        <p className="text-sm text-red-500 dark:text-red-400">Erreur de chargement</p>
      ) : (
        <BudgetKpiCards
          synthesis={data?.synthesis}
          prevSynthesis={prevData?.synthesis}
          prevMonthLabel={shortMonthLabel(prev)}
        />
      )}

      {/* Empty state */}
      {showEmptyState && (
        <BudgetEmptyState onStart={() => incomeFormRef.current?.focus()} />
      )}

      {/* Contenu principal */}
      {!isLoading && !error && (
        <>
          {/* Graphiques — affichés si des comparaisons existent */}
          {hasComparisons && (
            <>
              <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
                <BudgetExpenseDonut rows={expenseRows} />
                <BudgetHistoryChart />
              </div>
              <BudgetBarChart rows={expenseRows} />
            </>
          )}

          {/* Tableaux + formulaires — affichés dès qu'il y a des enveloppes ou des comparaisons */}
          {(hasEnvelopes || hasComparisons) && (
            <div className="space-y-6">
              <BudgetCategoryTable
                title="Revenus"
                rows={incomeRows}
                kind="INCOME"
                onSave={(cat, sub, amt) => handleSave('INCOME', cat, sub, amt)}
                onDelete={(cat, sub) => handleDelete('INCOME', cat, sub)}
                footer={
                  <AddEnvelopeForm
                    kind="INCOME"
                    focusRef={incomeFormRef}
                    onAdd={(cat, sub, amt) => handleSave('INCOME', cat, sub, amt)}
                  />
                }
              />
              <BudgetCategoryTable
                title="Dépenses"
                rows={expenseRows}
                kind="EXPENSE"
                onSave={(cat, sub, amt) => handleSave('EXPENSE', cat, sub, amt)}
                onDelete={(cat, sub) => handleDelete('EXPENSE', cat, sub)}
                footer={
                  <AddEnvelopeForm
                    kind="EXPENSE"
                    focusRef={expenseFormRef}
                    onAdd={(cat, sub, amt) => handleSave('EXPENSE', cat, sub, amt)}
                  />
                }
              />
            </div>
          )}
        </>
      )}
    </div>
  )
}
