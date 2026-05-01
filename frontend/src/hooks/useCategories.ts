import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { categoriesApi, type Category, type CategoryUpdate } from '../lib/categoriesApi'

const QUERY_KEY = ['categories']

export function useCategories() {
  return useQuery({
    queryKey: QUERY_KEY,
    queryFn: () => categoriesApi.list(),
  })
}

export function useAddCategory() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (name: string) => categoriesApi.createCategory(name),
    onSuccess: () => qc.invalidateQueries({ queryKey: QUERY_KEY }),
  })
}

export function useDeleteCategory() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (categoryId: string) => categoriesApi.deleteCategory(categoryId),
    onSuccess: () => qc.invalidateQueries({ queryKey: QUERY_KEY }),
  })
}

export function useUpdateCategory() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: ({ categoryId, payload }: { categoryId: string; payload: CategoryUpdate }) =>
      categoriesApi.updateCategory(categoryId, payload),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: QUERY_KEY })
      qc.invalidateQueries({ queryKey: ['budget'] })
    },
  })
}

export function useAddSubcategory() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: ({ categoryId, name }: { categoryId: string; name: string }) =>
      categoriesApi.addSubcategory(categoryId, name),
    onSuccess: () => qc.invalidateQueries({ queryKey: QUERY_KEY }),
  })
}

export function useDeleteSubcategory() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: ({ categoryId, subcategoryId }: { categoryId: string; subcategoryId: string }) =>
      categoriesApi.deleteSubcategory(categoryId, subcategoryId),
    onSuccess: () => qc.invalidateQueries({ queryKey: QUERY_KEY }),
  })
}

export type { Category }
