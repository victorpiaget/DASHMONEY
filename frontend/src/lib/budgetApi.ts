import { api } from './api'

export interface BudgetEnvelope {
  id: string
  category: string
  subcategory: string | null
  kind: string
  amount: string
  currency: string
  profile_id: string
}

export interface BudgetComparison {
  category: string
  subcategory: string | null
  kind: string
  planned: string
  actual: string
  delta: string
  percent: string
}

export interface BudgetSynthesis {
  total_income_planned: string
  total_income_actual: string
  total_expense_planned: string
  total_expense_actual: string
  net_planned: string
  net_actual: string
}

export interface BudgetComparisonFull {
  month: string
  currency: string
  synthesis: BudgetSynthesis
  comparisons: BudgetComparison[]
  profile_id: string
}

export interface BudgetHistoryMonth {
  month: string
  income_actual: string
  expense_actual: string
  net_actual: string
  income_planned: string
  expense_planned: string
}

export interface BudgetHistoryResponse {
  months: BudgetHistoryMonth[]
  currency: string
  profile_id: string
}

export interface BudgetCategoryItem {
  category: string
  subcategories: string[]
}

export interface BudgetCategoriesResponse {
  income: BudgetCategoryItem[]
  expense: BudgetCategoryItem[]
}

export const budgetApi = {
  listEnvelopes: (): Promise<BudgetEnvelope[]> =>
    api.get<BudgetEnvelope[]>('/budget/envelopes').then(r => r.data),

  upsertEnvelope: (data: {
    category: string
    subcategory?: string | null
    kind: string
    amount: string
  }): Promise<BudgetEnvelope> =>
    api.put<BudgetEnvelope>('/budget/envelopes', data).then(r => r.data),

  deleteEnvelope: (id: string): Promise<void> =>
    api.delete(`/budget/envelopes/${id}`).then(() => undefined),

  comparison: (month: string): Promise<BudgetComparisonFull> =>
    api.get<BudgetComparisonFull>('/budget/comparison', { params: { month } }).then(r => r.data),

  history: (months = 6): Promise<BudgetHistoryResponse> =>
    api.get<BudgetHistoryResponse>('/budget/history', { params: { months } }).then(r => r.data),

  categories: (): Promise<BudgetCategoriesResponse> =>
    api.get<BudgetCategoriesResponse>('/budget/categories').then(r => r.data),
}
