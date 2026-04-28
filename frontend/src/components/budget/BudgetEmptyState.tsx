interface Props {
  onStart: () => void
}

export default function BudgetEmptyState({ onStart }: Props) {
  return (
    <div className="flex flex-col items-center justify-center py-16 text-center">
      <svg className="w-16 h-16 text-gray-300 dark:text-gray-600 mb-4" fill="none" viewBox="0 0 64 64" stroke="currentColor" strokeWidth={1.5}>
        <rect x="8" y="12" width="48" height="40" rx="4" />
        <path d="M8 24h48M20 12v12M44 12v12M20 36h8M20 44h16" />
      </svg>
      <h3 className="text-base font-semibold text-gray-700 dark:text-gray-300 mb-1">
        Configurez votre budget mensuel
      </h3>
      <p className="text-sm text-gray-500 dark:text-gray-400 max-w-xs mb-6">
        Définissez des enveloppes pour suivre vos dépenses et revenus et comparer au réel chaque mois.
      </p>
      <button
        onClick={onStart}
        className="px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white text-sm font-medium rounded-lg transition-colors"
      >
        Commencer
      </button>
    </div>
  )
}
