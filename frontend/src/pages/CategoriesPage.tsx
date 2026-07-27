import { useState } from 'react'
import {
  useCategories,
  useAddCategory,
  useDeleteCategory,
  useAddSubcategory,
  useDeleteSubcategory,
  useUpdateCategory,
} from '../hooks/useCategories'
import type { CategoryNature } from '../lib/categoriesApi'

const NATURE_LABELS: Record<CategoryNature | 'NULL', string> = {
  NEED: 'Besoin',
  WANT: 'Envie',
  SAVING: 'Épargne',
  NULL: 'Non classé',
}

const NATURE_OPTIONS: { value: CategoryNature | 'NULL'; label: string }[] = [
  { value: 'NULL', label: NATURE_LABELS.NULL },
  { value: 'NEED', label: NATURE_LABELS.NEED },
  { value: 'WANT', label: NATURE_LABELS.WANT },
  { value: 'SAVING', label: NATURE_LABELS.SAVING },
]

const NATURE_BADGE_CLASS: Record<CategoryNature | 'NULL', string> = {
  NEED: 'bg-blue-50 text-blue-700 dark:bg-blue-900/30 dark:text-blue-300',
  WANT: 'bg-purple-50 text-purple-700 dark:bg-purple-900/30 dark:text-purple-300',
  SAVING: 'bg-emerald-50 text-emerald-700 dark:bg-emerald-900/30 dark:text-emerald-300',
  NULL: 'bg-amber-50 text-amber-700 dark:bg-amber-900/30 dark:text-amber-300',
}

export default function CategoriesPage() {
  const { data: categories = [], isLoading } = useCategories()
  const addCategory = useAddCategory()
  const deleteCategory = useDeleteCategory()
  const updateCategory = useUpdateCategory()
  const addSubcategory = useAddSubcategory()
  const deleteSubcategory = useDeleteSubcategory()

  const [newCategoryName, setNewCategoryName] = useState('')
  const [expandedCategory, setExpandedCategory] = useState<string | null>(null)
  const [newSubNames, setNewSubNames] = useState<Record<string, string>>({})

  const handleAddCategory = () => {
    const trimmed = newCategoryName.trim()
    if (!trimmed) return
    addCategory.mutate(trimmed, { onSuccess: () => setNewCategoryName('') })
  }

  const handleAddSubcategory = (categoryId: string) => {
    const val = (newSubNames[categoryId] ?? '').trim()
    if (!val) return
    addSubcategory.mutate(
      { categoryId, name: val },
      { onSuccess: () => setNewSubNames((prev) => ({ ...prev, [categoryId]: '' })) },
    )
  }

  const handleNatureChange = (categoryId: string, value: CategoryNature | 'NULL') => {
    if (value === 'NULL') {
      updateCategory.mutate({ categoryId, payload: { clear_nature: true } })
    } else {
      updateCategory.mutate({ categoryId, payload: { nature: value } })
    }
  }

  return (
    <div className="p-8">
      {/* Header */}
      <div className="mb-8">
        <h1 className="text-xl font-semibold text-gray-900 dark:text-white">Catégories</h1>
        <p className="text-xs text-gray-400 dark:text-gray-500 mt-1">
          Gérez vos catégories, leur nature (Besoin / Envie / Épargne) et les sous-catégories
        </p>
      </div>

      {/* Add Category Section */}
      <div className="mb-6">
        <div className="flex gap-3 max-w-sm">
          <input
            type="text"
            placeholder="Nouvelle catégorie…"
            value={newCategoryName}
            onChange={(e) => setNewCategoryName(e.target.value)}
            onKeyDown={(e) => e.key === 'Enter' && handleAddCategory()}
            className={inputClass}
          />
          <button
            onClick={handleAddCategory}
            disabled={!newCategoryName.trim() || addCategory.isPending}
            className="px-4 py-2.5 bg-gray-900 text-white text-sm font-medium rounded-xl hover:bg-gray-800 active:scale-[0.98] disabled:opacity-40 transition-all whitespace-nowrap dark:bg-white dark:text-gray-900 dark:hover:bg-gray-100"
          >
            Ajouter
          </button>
        </div>
      </div>

      {/* Categories List */}
      {isLoading ? (
        <div className="flex justify-center py-16">
          <div className="w-6 h-6 border-2 border-gray-200 border-t-gray-700 rounded-full animate-spin dark:border-gray-700 dark:border-t-gray-300" />
        </div>
      ) : (
        <div className="space-y-3">
          {categories.map((cat) => {
            const natureKey: CategoryNature | 'NULL' = cat.nature ?? 'NULL'
            return (
              <div
                key={cat.id}
                className="rounded-xl border border-gray-100 dark:border-gray-700 bg-white dark:bg-gray-800 hover:shadow-sm transition-shadow overflow-hidden"
              >
                {/* Category Header */}
                <div className="flex items-center gap-3 px-5 py-4 flex-wrap">
                  <button
                    className="flex items-center gap-3 flex-1 text-left min-w-0"
                    onClick={() => setExpandedCategory(expandedCategory === cat.id ? null : cat.id)}
                  >
                    <span className="text-sm font-medium text-gray-900 dark:text-white truncate">{cat.name}</span>
                    <span className={`text-xs font-medium rounded px-2 py-0.5 ${NATURE_BADGE_CLASS[natureKey]}`}>
                      {NATURE_LABELS[natureKey]}
                    </span>
                    <span className="text-xs text-gray-400 dark:text-gray-500">
                      {cat.subcategories.length} sous-cat.
                    </span>
                    <span
                      className={`text-gray-300 dark:text-gray-600 ml-auto text-xs transition-transform duration-200 ${
                        expandedCategory === cat.id ? 'rotate-180' : ''
                      }`}
                    >
                      ▼
                    </span>
                  </button>

                  <select
                    value={natureKey}
                    onChange={(e) => handleNatureChange(cat.id, e.target.value as CategoryNature | 'NULL')}
                    disabled={updateCategory.isPending}
                    className="text-xs rounded-lg border border-gray-200 dark:border-gray-600 bg-white dark:bg-gray-700 text-gray-700 dark:text-gray-200 px-2 py-1 focus:outline-none focus:ring-2 focus:ring-gray-900 dark:focus:ring-gray-300 transition-all disabled:opacity-40"
                    title="Nature de la catégorie"
                  >
                    {NATURE_OPTIONS.map((opt) => (
                      <option key={opt.value} value={opt.value}>
                        {opt.label}
                      </option>
                    ))}
                  </select>

                  <button
                    onClick={() => deleteCategory.mutate(cat.id)}
                    disabled={deleteCategory.isPending}
                    className="text-xs text-gray-400 dark:text-gray-500 hover:text-red-500 dark:hover:text-red-400 transition-colors disabled:opacity-40"
                    title="Supprimer la catégorie"
                  >
                    Supprimer
                  </button>
                </div>

                {/* Subcategories Section */}
                {expandedCategory === cat.id && (
                  <div className="border-t border-gray-50 dark:border-gray-700 px-5 py-4 space-y-4 transition-all duration-200">
                    {/* Subcategory Tags */}
                    <div className="flex flex-wrap gap-2">
                      {cat.subcategories.length === 0 && (
                        <span className="text-xs text-gray-400 dark:text-gray-500">Aucune sous-catégorie</span>
                      )}
                      {cat.subcategories.map((sub) => (
                        <span
                          key={sub.id}
                          className="inline-flex items-center gap-2 px-3 py-1.5 bg-gray-50 dark:bg-gray-700 rounded-lg text-xs text-gray-700 dark:text-gray-200 hover:bg-gray-100 dark:hover:bg-gray-600 transition-colors"
                        >
                          {sub.name}
                          <button
                            onClick={() => deleteSubcategory.mutate({ categoryId: cat.id, subcategoryId: sub.id })}
                            className="text-gray-400 hover:text-red-500 dark:hover:text-red-400 leading-none transition-colors font-medium"
                            title="Supprimer"
                          >
                            ×
                          </button>
                        </span>
                      ))}
                    </div>

                    {/* Add Subcategory */}
                    <div className="flex gap-3 max-w-xs pt-2">
                      <input
                        type="text"
                        placeholder="Nouvelle sous-catégorie…"
                        value={newSubNames[cat.id] ?? ''}
                        onChange={(e) => setNewSubNames((prev) => ({ ...prev, [cat.id]: e.target.value }))}
                        onKeyDown={(e) => e.key === 'Enter' && handleAddSubcategory(cat.id)}
                        className={inputClass}
                      />
                      <button
                        onClick={() => handleAddSubcategory(cat.id)}
                        disabled={!(newSubNames[cat.id] ?? '').trim() || addSubcategory.isPending}
                        className="px-3 py-2.5 bg-gray-900 text-white text-xs font-medium rounded-xl hover:bg-gray-800 active:scale-[0.98] disabled:opacity-40 transition-all whitespace-nowrap dark:bg-white dark:text-gray-900 dark:hover:bg-gray-100"
                      >
                        +
                      </button>
                    </div>
                  </div>
                )}
              </div>
            )
          })}
        </div>
      )}
    </div>
  )
}

const inputClass =
  'w-full px-4 py-2.5 rounded-xl border border-gray-200 dark:border-gray-700 text-sm text-gray-900 dark:text-gray-100 placeholder-gray-400 dark:placeholder-gray-500 focus:outline-none focus:ring-2 focus:ring-gray-900 dark:focus:ring-gray-300 focus:border-transparent transition-all bg-white dark:bg-gray-800'
