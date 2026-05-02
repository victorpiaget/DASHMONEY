import BudgetAutoFillButton from './BudgetAutoFillButton'

interface Props {
  onStart: () => void
}

export default function BudgetEmptyState({ onStart }: Props) {
  return (
    <div className="flex flex-col items-center justify-center py-16 text-center">
      <svg
        className="w-16 h-16 text-gray-300 dark:text-gray-600 mb-4"
        fill="none"
        viewBox="0 0 64 64"
        stroke="currentColor"
        strokeWidth={1.5}
      >
        <rect x="8" y="12" width="48" height="40" rx="4" />
        <path d="M8 24h48M20 12v12M44 12v12M20 36h8M20 44h16" />
      </svg>
      <h3 className="text-base font-semibold text-gray-700 dark:text-gray-300 mb-1">
        Configure ton budget mensuel
      </h3>
      <p className="text-sm text-gray-500 dark:text-gray-400 max-w-sm mb-6">
        Définis des enveloppes pour suivre tes dépenses et revenus, ou laisse l'auto-budget
        proposer des montants basés sur tes 3 derniers mois.
      </p>
      <div className="flex gap-3 flex-wrap items-center justify-center">
        <button
          onClick={onStart}
          className="px-4 py-2 bg-gray-900 dark:bg-white dark:text-gray-900 text-white text-sm font-medium rounded-lg hover:bg-gray-800 dark:hover:bg-gray-100 transition-colors"
        >
          Commencer manuellement
        </button>
        <BudgetAutoFillButton kind="EXPENSE" />
      </div>
    </div>
  )
}
