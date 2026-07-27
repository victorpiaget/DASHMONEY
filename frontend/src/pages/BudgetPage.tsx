import { useMemo, useRef, useState } from 'react'
import {
  useBudgetCategories,
  useBudgetComparison,
  useBudgetEnvelopes,
  useBudgetFlow,
  useDeleteEnvelope,
  useUpsertEnvelope,
} from '../hooks/useBudget'
import type { CategoryNature } from '../lib/budgetApi'
import { useAccounts } from '../hooks/useAccounts'
import { useCurrency } from '../context/CurrencyContext'
import PeriodPicker from '../components/PeriodPicker'
import { resolveDates, type PeriodSelection } from '../lib/period'
import BudgetKpiCards from '../components/budget/BudgetKpiCards'
import BudgetFlowSankey from '../components/budget/BudgetFlowSankey'
import BudgetExpenseDonut from '../components/budget/BudgetExpenseDonut'
import BudgetHistoryChart from '../components/budget/BudgetHistoryChart'
import BudgetBarChart from '../components/budget/BudgetBarChart'
import BudgetCategoryTable from '../components/budget/BudgetCategoryTable'
import BudgetEmptyState from '../components/budget/BudgetEmptyState'
import BudgetFiftyThirtyTwenty from '../components/budget/BudgetFiftyThirtyTwenty'
import BudgetUncategorizedAlert from '../components/budget/BudgetUncategorizedAlert'
import BudgetAutoFillButton from '../components/budget/BudgetAutoFillButton'
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

type BudgetView = 'flow' | 'planning'

function BudgetViewSwitch({
  view,
  onChange,
}: {
  view: BudgetView
  onChange: (view: BudgetView) => void
}) {
  return (
    <div className="inline-flex rounded-xl border border-gray-200 dark:border-gray-700 bg-gray-100 dark:bg-gray-900 p-1">
      {([
        ['flow', 'Flux réels'],
        ['planning', 'Prévision mensuelle'],
      ] as const).map(([key, label]) => (
        <button
          key={key}
          type="button"
          onClick={() => onChange(key)}
          className={`px-3 py-1.5 rounded-lg text-xs font-medium transition-all ${
            view === key
              ? 'bg-white dark:bg-gray-700 text-gray-900 dark:text-white shadow-sm'
              : 'text-gray-500 dark:text-gray-400 hover:text-gray-700 dark:hover:text-gray-200'
          }`}
        >
          {label}
        </button>
      ))}
    </div>
  )
}

// ── BudgetPage ────────────────────────────────────────────────────────────────

export default function BudgetPage() {
  const [view, setView] = useState<BudgetView>('flow')
  const [period, setPeriod] = useState<PeriodSelection>({ type: 'preset', preset: '1M' })
  const [month, setMonth] = useState(currentMonth)
  const { format } = useCurrency()
  const { data: accounts = [] } = useAccounts()
  const today = currentMonth()
  const prev = prevMonth(month)
  const fallbackMinMonth = `${new Date().getFullYear() - 10}-01`
  const minMonth = useMemo(
    () => accounts.length > 0
      ? accounts.map((account) => account.opened_on.slice(0, 7)).sort()[0]
      : fallbackMinMonth,
    [accounts, fallbackMinMonth],
  )
  const flowDates = useMemo(
    () => resolveDates(period, `${minMonth}-01`, true),
    [period, minMonth],
  )

  const { data, isLoading, error } = useBudgetComparison(month)
  const { data: prevData } = useBudgetComparison(prev)
  const flowQuery = useBudgetFlow(flowDates.from, flowDates.to, view === 'flow')
  const upsert = useUpsertEnvelope()
  const remove = useDeleteEnvelope()
  const budgetEnvelopesQuery = useBudgetEnvelopes()
  const categoriesQuery = useBudgetCategories()

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

  const incomeRows = useMemo(
    () => data?.comparisons.filter((comparison) => comparison.kind === 'INCOME') ?? [],
    [data?.comparisons],
  )
  const expenseRows = useMemo(
    () => data?.comparisons.filter((comparison) => comparison.kind === 'EXPENSE') ?? [],
    [data?.comparisons],
  )

  // Mapping {category_name: nature} pour la pastille
  const natureMap = useMemo<Record<string, CategoryNature | null>>(() => {
    const map: Record<string, CategoryNature | null> = {}
    const cats = categoriesQuery.data
    if (!cats) return map
    for (const c of cats.income) map[c.category] = c.nature
    for (const c of cats.expense) map[c.category] = c.nature
    return map
  }, [categoriesQuery.data])

  // Compte des catégories de dépense présentes ce mois mais à nature=NULL
  const uncategorizedCount = useMemo(() => {
    const expenseCatsThisMonth = new Set(
      expenseRows.map((r) => r.category),
    )
    let n = 0
    for (const cat of expenseCatsThisMonth) {
      const nat = natureMap[cat]
      if (nat == null) n += 1
    }
    return n
  }, [expenseRows, natureMap])

  const uncategorizedAmount = Math.abs(parseFloat(data?.buckets?.uncategorized ?? '0'))

  const hasEnvelopes = (budgetEnvelopesQuery.data?.length ?? 0) > 0
  const hasComparisons = (data?.comparisons.length ?? 0) > 0
  const showEmptyState = !isLoading && !error && !hasEnvelopes && !hasComparisons
  const flowData = flowQuery.data
  const flowBalance = Number(flowData?.summary.balance ?? '0')
  const flowUncategorized = flowData?.expense_categories.filter(
    (category) => category.nature == null,
  ) ?? []
  const flowUncategorizedAmount = flowUncategorized.reduce(
    (sum, category) => sum + Number(category.amount),
    0,
  )

  if (view === 'flow') {
    return (
      <div className="page-transition max-w-6xl mx-auto p-6 space-y-6">
        <div className="flex items-center justify-between flex-wrap gap-3">
          <div>
            <h1 className="text-xl font-semibold text-gray-900 dark:text-white">Budget</h1>
            <p className="text-sm text-gray-500 dark:text-gray-400 mt-0.5">
              Visualise comment tes revenus se répartissent sur la période
            </p>
          </div>
          <div className="flex items-center gap-3 flex-wrap">
            <BudgetViewSwitch view={view} onChange={setView} />
            <PeriodPicker
              selection={period}
              onChange={setPeriod}
              minMonth={minMonth}
              exactPresetCount
            />
          </div>
        </div>

        {!flowQuery.isLoading && !flowQuery.error && flowUncategorized.length > 0 && (
          <BudgetUncategorizedAlert
            count={flowUncategorized.length}
            uncategorizedAmount={flowUncategorizedAmount}
          />
        )}

        {flowQuery.isLoading ? (
          <>
            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
              {[0, 1, 2, 3].map((index) => (
                <div
                  key={index}
                  className="h-24 rounded-xl bg-gray-100 dark:bg-gray-800 animate-pulse"
                />
              ))}
            </div>
            <div className="h-[520px] rounded-2xl bg-gray-100 dark:bg-gray-800 animate-pulse" />
          </>
        ) : flowQuery.error ? (
          <div className="rounded-xl border border-red-100 dark:border-red-900/40 bg-red-50 dark:bg-red-900/20 px-4 py-3">
            <p className="text-sm text-red-600 dark:text-red-400">
              Impossible de charger les flux de cette période.
            </p>
          </div>
        ) : flowData ? (
          <>
            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
              {[
                {
                  label: 'Revenus',
                  value: flowData.summary.total_income,
                  detail: 'Entrées de la période',
                  color: 'text-emerald-600 dark:text-emerald-400',
                },
                {
                  label: 'Dépenses',
                  value: flowData.summary.total_expenses,
                  detail: 'Hors flux d’épargne',
                  color: 'text-red-500 dark:text-red-400',
                },
                {
                  label: 'Épargne',
                  value: flowData.summary.total_savings,
                  detail: 'Catégories classées Épargne',
                  color: 'text-blue-600 dark:text-blue-400',
                },
                {
                  label: 'Solde de la période',
                  value: String(Math.abs(flowBalance)),
                  detail: flowBalance >= 0 ? 'Reste disponible' : 'Déficit à financer',
                  color: flowBalance >= 0
                    ? 'text-teal-600 dark:text-teal-400'
                    : 'text-red-500 dark:text-red-400',
                  prefix: flowBalance < 0 ? '−' : '',
                },
              ].map((card) => (
                <div
                  key={card.label}
                  className="bg-white dark:bg-gray-800 rounded-xl border border-gray-100 dark:border-gray-700 p-4"
                >
                  <p className="text-xs text-gray-500 dark:text-gray-400 uppercase tracking-wide">
                    {card.label}
                  </p>
                  <p className={`text-xl font-bold tabular-nums mt-1 ${card.color}`}>
                    {card.prefix}{format(card.value, flowData.currency)}
                  </p>
                  <p className="text-xs text-gray-400 dark:text-gray-500 mt-1">
                    {card.detail}
                  </p>
                </div>
              ))}
            </div>
            <BudgetFlowSankey data={flowData} />
          </>
        ) : null}
      </div>
    )
  }

  return (
    <div className="page-transition max-w-6xl mx-auto p-6 space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between flex-wrap gap-3">
        <div>
          <h1 className="text-xl font-semibold text-gray-900 dark:text-white">Budget</h1>
          <p className="text-sm text-gray-500 dark:text-gray-400 mt-0.5">
            Compare tes enveloppes mensuelles au réel et à la règle 50 / 30 / 20
          </p>
        </div>
        <div className="flex items-center gap-3 flex-wrap">
          <BudgetViewSwitch view={view} onChange={setView} />
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
      </div>

      {/* Bandeau "Non classé" */}
      {!isLoading && !error && (
        <BudgetUncategorizedAlert
          count={uncategorizedCount}
          uncategorizedAmount={uncategorizedAmount}
        />
      )}

      {/* KPI Cards */}
      {isLoading ? (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
          {[0, 1, 2, 3].map((i) => (
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
          {/* Section 50/30/20 */}
          {hasComparisons && <BudgetFiftyThirtyTwenty buckets={data?.buckets} />}

          {/* Graphiques — affichés si des comparaisons existent */}
          {hasComparisons && (
            <>
              <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
                <BudgetExpenseDonut rows={expenseRows} buckets={data?.buckets} />
                <BudgetHistoryChart />
              </div>
              <BudgetBarChart rows={expenseRows} />
            </>
          )}

          {/* Tableaux + formulaires */}
          {(hasEnvelopes || hasComparisons) && (
            <div className="space-y-6">
              <BudgetCategoryTable
                title="Revenus"
                rows={incomeRows}
                kind="INCOME"
                natureMap={natureMap}
                onSave={(cat, sub, amt) => handleSave('INCOME', cat, sub, amt)}
                onDelete={(cat, sub) => handleDelete('INCOME', cat, sub)}
                footer={
                  <div className="px-4 py-3 border-t border-gray-100 dark:border-gray-700 flex items-center gap-3 flex-wrap">
                    <AddEnvelopeForm
                      kind="INCOME"
                      focusRef={incomeFormRef}
                      onAdd={(cat, sub, amt) => handleSave('INCOME', cat, sub, amt)}
                    />
                    <BudgetAutoFillButton kind="INCOME" />
                  </div>
                }
              />
              <BudgetCategoryTable
                title="Dépenses"
                rows={expenseRows}
                kind="EXPENSE"
                natureMap={natureMap}
                onSave={(cat, sub, amt) => handleSave('EXPENSE', cat, sub, amt)}
                onDelete={(cat, sub) => handleDelete('EXPENSE', cat, sub)}
                footer={
                  <div className="px-4 py-3 border-t border-gray-100 dark:border-gray-700 flex items-center gap-3 flex-wrap">
                    <AddEnvelopeForm
                      kind="EXPENSE"
                      focusRef={expenseFormRef}
                      onAdd={(cat, sub, amt) => handleSave('EXPENSE', cat, sub, amt)}
                    />
                    <BudgetAutoFillButton kind="EXPENSE" />
                  </div>
                }
              />
            </div>
          )}
        </>
      )}
    </div>
  )
}
