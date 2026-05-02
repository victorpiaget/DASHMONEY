import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'

interface Props {
  count: number          // nombre de catégories de dépenses à nature=NULL utilisées ce mois
  uncategorizedAmount: number  // total absolu en EUR du bucket "Non classé"
}

const DISMISS_KEY = 'budget-uncat-dismissed-day'

export default function BudgetUncategorizedAlert({ count, uncategorizedAmount }: Props) {
  const [dismissed, setDismissed] = useState(false)

  useEffect(() => {
    const stored = localStorage.getItem(DISMISS_KEY)
    const today = new Date().toISOString().slice(0, 10)
    if (stored === today) setDismissed(true)
  }, [])

  if (count === 0 || uncategorizedAmount === 0 || dismissed) return null

  function handleDismiss() {
    const today = new Date().toISOString().slice(0, 10)
    localStorage.setItem(DISMISS_KEY, today)
    setDismissed(true)
  }

  return (
    <div className="bg-yellow-50 dark:bg-yellow-900/20 border border-yellow-200 dark:border-yellow-700/50 rounded-xl p-4 flex items-start gap-3">
      <span className="text-yellow-500 dark:text-yellow-400 text-lg leading-none mt-0.5">⚠</span>
      <div className="flex-1 min-w-0">
        <p className="text-sm font-medium text-yellow-900 dark:text-yellow-100">
          {count} {count > 1 ? 'catégories non classées' : 'catégorie non classée'} faussent ta répartition
        </p>
        <p className="text-xs text-yellow-700 dark:text-yellow-300 mt-0.5">
          Classe-les en Besoin / Envie / Épargne pour obtenir une vue précise.
        </p>
      </div>
      <Link
        to="/categories"
        className="text-xs font-medium text-yellow-900 dark:text-yellow-100 hover:underline whitespace-nowrap"
      >
        Classer maintenant →
      </Link>
      <button
        onClick={handleDismiss}
        className="text-yellow-500 dark:text-yellow-400 hover:text-yellow-700 dark:hover:text-yellow-200 text-lg leading-none px-1"
        title="Masquer pour aujourd'hui"
      >
        ×
      </button>
    </div>
  )
}
