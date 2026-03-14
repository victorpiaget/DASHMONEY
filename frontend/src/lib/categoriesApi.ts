import { api } from './api'

export interface Subcategory {
  id: string
  name: string
}

export interface Category {
  id: string
  name: string
  subcategories: Subcategory[]
}

export const categoriesApi = {
  list: (): Promise<Category[]> =>
    api.get<Category[]>('/categories').then((r) => r.data),

  createCategory: (name: string): Promise<Category> =>
    api.post<Category>('/categories', { name }).then((r) => r.data),

  deleteCategory: (categoryId: string): Promise<void> =>
    api.delete(`/categories/${categoryId}`).then(() => undefined),

  addSubcategory: (categoryId: string, name: string): Promise<Subcategory> =>
    api.post<Subcategory>(`/categories/${categoryId}/subcategories`, { name }).then((r) => r.data),

  deleteSubcategory: (categoryId: string, subcategoryId: string): Promise<void> =>
    api.delete(`/categories/${categoryId}/subcategories/${subcategoryId}`).then(() => undefined),
}
