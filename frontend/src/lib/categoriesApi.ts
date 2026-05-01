import { api } from './api'

export type CategoryNature = 'NEED' | 'WANT' | 'SAVING'

export interface Subcategory {
  id: string
  name: string
}

export interface Category {
  id: string
  name: string
  nature: CategoryNature | null
  subcategories: Subcategory[]
}

export interface CategoryUpdate {
  name?: string
  nature?: CategoryNature | null
  clear_nature?: boolean
}

export const categoriesApi = {
  list: (): Promise<Category[]> =>
    api.get<Category[]>('/categories').then((r) => r.data),

  createCategory: (name: string, nature?: CategoryNature | null): Promise<Category> =>
    api.post<Category>('/categories', { name, nature: nature ?? null }).then((r) => r.data),

  updateCategory: (categoryId: string, payload: CategoryUpdate): Promise<Category> =>
    api.patch<Category>(`/categories/${categoryId}`, payload).then((r) => r.data),

  deleteCategory: (categoryId: string): Promise<void> =>
    api.delete(`/categories/${categoryId}`).then(() => undefined),

  addSubcategory: (categoryId: string, name: string): Promise<Subcategory> =>
    api.post<Subcategory>(`/categories/${categoryId}/subcategories`, { name }).then((r) => r.data),

  deleteSubcategory: (categoryId: string, subcategoryId: string): Promise<void> =>
    api.delete(`/categories/${categoryId}/subcategories/${subcategoryId}`).then(() => undefined),
}
