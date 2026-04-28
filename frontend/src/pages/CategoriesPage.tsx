import { useState } from 'react'
import { useCategories, useAddCategory, useDeleteCategory, useAddSubcategory, useDeleteSubcategory } from '../hooks/useCategories'

export default function CategoriesPage() {
  const { data: categories = [], isLoading } = useCategories()
  const addCategory = useAddCategory()
  const deleteCategory = useDeleteCategory()
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

  return (
    <div className="p-8">
      {/* Header */}
      <div className="mb-8">
        <h1 className="text-xl font-semibold text-gray-900">Catégories</h1>
        <p className="text-xs text-gray-400 mt-1">Gérez vos catégories et sous-catégories de transactions</p>
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
            className="px-4 py-2.5 bg-gray-900 text-white text-sm font-medium rounded-xl hover:bg-gray-800 active:scale-[0.98] disabled:opacity-40 transition-all whitespace-nowrap"
          >
            Ajouter
          </button>
        </div>
      </div>

      {/* Categories List */}
      {isLoading ? (
        <div className="flex justify-center py-16">
          <div className="w-6 h-6 border-2 border-gray-200 border-t-gray-700 rounded-full animate-spin" />
        </div>
      ) : (
        <div className="space-y-3">
          {categories.map((cat) => (
            <div
              key={cat.id}
              className="rounded-xl border border-gray-100 bg-white hover:shadow-sm transition-shadow overflow-hidden"
            >
              {/* Category Header */}
              <div className="flex items-center justify-between px-5 py-4">
                <button
                  className="flex items-center gap-3 flex-1 text-left"
                  onClick={() => setExpandedCategory(expandedCategory === cat.id ? null : cat.id)}
                >
                  <span className="text-sm font-medium text-gray-900">{cat.name}</span>
                  <span className="text-xs text-gray-400">
                    {cat.subcategories.length} sous-catégorie{cat.subcategories.length !== 1 ? 's' : ''}
                  </span>
                  <span
                    className={`text-gray-300 ml-auto text-xs transition-transform duration-200 ${
                      expandedCategory === cat.id ? 'rotate-180' : ''
                    }`}
                  >
                    ▼
                  </span>
                </button>
                <button
                  onClick={() => deleteCategory.mutate(cat.id)}
                  disabled={deleteCategory.isPending}
                  className="ml-4 text-xs text-gray-400 hover:text-red-500 transition-colors disabled:opacity-40"
                  title="Supprimer la catégorie"
                >
                  Supprimer
                </button>
              </div>

              {/* Subcategories Section */}
              {expandedCategory === cat.id && (
                <div className="border-t border-gray-50 px-5 py-4 space-y-4 transition-all duration-200">
                  {/* Subcategory Tags */}
                  <div className="flex flex-wrap gap-2">
                    {cat.subcategories.length === 0 && (
                      <span className="text-xs text-gray-400">Aucune sous-catégorie</span>
                    )}
                    {cat.subcategories.map((sub) => (
                      <span
                        key={sub.id}
                        className="inline-flex items-center gap-2 px-3 py-1.5 bg-gray-50 rounded-lg text-xs text-gray-700 hover:bg-gray-100 transition-colors"
                      >
                        {sub.name}
                        <button
                          onClick={() => deleteSubcategory.mutate({ categoryId: cat.id, subcategoryId: sub.id })}
                          className="text-gray-400 hover:text-red-500 leading-none transition-colors font-medium"
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
                      className="px-3 py-2.5 bg-gray-900 text-white text-xs font-medium rounded-xl hover:bg-gray-800 active:scale-[0.98] disabled:opacity-40 transition-all whitespace-nowrap"
                    >
                      +
                    </button>
                  </div>
                </div>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  )
}

const inputClass = 'w-full px-4 py-2.5 rounded-xl border border-gray-200 text-sm text-gray-900 placeholder-gray-400 focus:outline-none focus:ring-2 focus:ring-gray-900 focus:border-transparent transition-all bg-white'
