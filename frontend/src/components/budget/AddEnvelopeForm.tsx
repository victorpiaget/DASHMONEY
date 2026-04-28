import { useState, useRef, useEffect } from 'react'
import { useBudgetCategories } from '../../hooks/useBudget'

interface Props {
  kind: 'INCOME' | 'EXPENSE'
  onAdd: (category: string, subcategory: string | null, amount: string) => void
  focusRef?: React.RefObject<HTMLInputElement | null>
}

export default function AddEnvelopeForm({ kind, onAdd, focusRef }: Props) {
  const { data: cats } = useBudgetCategories()
  const [category, setCategory] = useState('')
  const [subcategory, setSubcategory] = useState('')
  const [amount, setAmount] = useState('')
  const [catSuggestions, setCatSuggestions] = useState<string[]>([])
  const [subSuggestions, setSubSuggestions] = useState<string[]>([])
  const [showCatSugg, setShowCatSugg] = useState(false)
  const [showSubSugg, setShowSubSugg] = useState(false)
  const catRef = focusRef ?? useRef<HTMLInputElement>(null)

  const kindList = kind === 'INCOME' ? (cats?.income ?? []) : (cats?.expense ?? [])

  useEffect(() => {
    const filtered = kindList
      .map(i => i.category)
      .filter(c => c.toLowerCase().includes(category.toLowerCase()) && c !== category)
    setCatSuggestions(filtered)
  }, [category, cats])

  useEffect(() => {
    const found = kindList.find(i => i.category === category)
    const filtered = (found?.subcategories ?? [])
      .filter(s => s.toLowerCase().includes(subcategory.toLowerCase()) && s !== subcategory)
    setSubSuggestions(filtered)
  }, [subcategory, category, cats])

  function handleSubmit(e: React.FormEvent) {
    e.preventDefault()
    const trimCat = category.trim()
    const trimSub = subcategory.trim() || null
    const amt = parseFloat(amount)
    if (!trimCat || isNaN(amt) || amt <= 0) return
    onAdd(trimCat, trimSub, amt.toFixed(2))
    setCategory('')
    setSubcategory('')
    setAmount('')
  }

  return (
    <form onSubmit={handleSubmit} className="px-4 py-3 border-t border-gray-100 dark:border-gray-700 flex items-center gap-2 flex-wrap">
      <div className="relative flex-1 min-w-36">
        <input
          ref={catRef}
          type="text"
          placeholder="Catégorie"
          value={category}
          onChange={e => { setCategory(e.target.value); setShowCatSugg(true) }}
          onFocus={() => setShowCatSugg(true)}
          onBlur={() => setTimeout(() => setShowCatSugg(false), 150)}
          className="w-full text-sm border border-gray-200 dark:border-gray-600 rounded-lg px-3 py-1.5 bg-white dark:bg-gray-700 text-gray-800 dark:text-gray-200 focus:outline-none focus:border-blue-400"
        />
        {showCatSugg && catSuggestions.length > 0 && (
          <ul className="absolute z-10 bottom-full left-0 right-0 mb-1 bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-600 rounded-lg shadow-lg text-sm max-h-40 overflow-y-auto">
            {catSuggestions.map(s => (
              <li
                key={s}
                onMouseDown={() => { setCategory(s); setShowCatSugg(false) }}
                className="px-3 py-1.5 cursor-pointer hover:bg-gray-50 dark:hover:bg-gray-700 text-gray-700 dark:text-gray-300"
              >
                {s}
              </li>
            ))}
          </ul>
        )}
      </div>
      <div className="relative flex-1 min-w-28">
        <input
          type="text"
          placeholder="Sous-catégorie (optionnel)"
          value={subcategory}
          onChange={e => { setSubcategory(e.target.value); setShowSubSugg(true) }}
          onFocus={() => setShowSubSugg(true)}
          onBlur={() => setTimeout(() => setShowSubSugg(false), 150)}
          className="w-full text-sm border border-gray-200 dark:border-gray-600 rounded-lg px-3 py-1.5 bg-white dark:bg-gray-700 text-gray-800 dark:text-gray-200 focus:outline-none focus:border-blue-400"
        />
        {showSubSugg && subSuggestions.length > 0 && (
          <ul className="absolute z-10 bottom-full left-0 right-0 mb-1 bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-600 rounded-lg shadow-lg text-sm max-h-40 overflow-y-auto">
            {subSuggestions.map(s => (
              <li
                key={s}
                onMouseDown={() => { setSubcategory(s); setShowSubSugg(false) }}
                className="px-3 py-1.5 cursor-pointer hover:bg-gray-50 dark:hover:bg-gray-700 text-gray-700 dark:text-gray-300"
              >
                {s}
              </li>
            ))}
          </ul>
        )}
      </div>
      <input
        type="number"
        placeholder="Montant €"
        min="0"
        step="0.01"
        value={amount}
        onChange={e => setAmount(e.target.value)}
        className="w-28 text-sm border border-gray-200 dark:border-gray-600 rounded-lg px-3 py-1.5 bg-white dark:bg-gray-700 text-gray-800 dark:text-gray-200 focus:outline-none focus:border-blue-400 text-right"
      />
      <button
        type="submit"
        className="px-3 py-1.5 bg-blue-600 hover:bg-blue-700 text-white text-sm font-medium rounded-lg transition-colors whitespace-nowrap"
      >
        Ajouter
      </button>
    </form>
  )
}
