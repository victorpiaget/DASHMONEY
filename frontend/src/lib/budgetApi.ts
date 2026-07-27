import { api } from './api'

export type CategoryNature = 'NEED' | 'WANT' | 'SAVING'

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
  savings_actual: string
  savings_rate: string  // "0.0000".."1.0000"
}

export interface BudgetBuckets {
  needs: string
  wants: string
  savings: string
  uncategorized: string
  total_expenses: string
}

export interface BudgetComparisonFull {
  month: string
  currency: string
  synthesis: BudgetSynthesis
  comparisons: BudgetComparison[]
  buckets: BudgetBuckets
  profile_id: string
}

export interface BudgetHistoryMonth {
  month: string
  income_actual: string
  expense_actual: string
  net_actual: string
  income_planned: string
  expense_planned: string
  savings_actual: string
  savings_rate: string
}

export interface BudgetHistoryResponse {
  months: BudgetHistoryMonth[]
  currency: string
  profile_id: string
}

export interface BudgetFlowIncomeSource {
  category: string
  subcategory: string | null
  amount: string
}

export interface BudgetFlowSubcategory {
  subcategory: string | null
  amount: string
}

export interface BudgetFlowExpenseCategory {
  category: string
  nature: CategoryNature | null
  amount: string
  subcategories: BudgetFlowSubcategory[]
}

export interface BudgetFlowSummary {
  total_income: string
  total_expenses: string
  total_savings: string
  total_outflows: string
  balance: string
  remaining: string
  deficit: string
}

export interface BudgetFlowResponse {
  date_from: string
  date_to: string
  currency: string
  income_sources: BudgetFlowIncomeSource[]
  expense_categories: BudgetFlowExpenseCategory[]
  summary: BudgetFlowSummary
  profile_id: string
}

export interface BudgetCategoryItem {
  category: string
  subcategories: string[]
  nature: CategoryNature | null
}

export interface BudgetCategoriesResponse {
  income: BudgetCategoryItem[]
  expense: BudgetCategoryItem[]
}

export interface BudgetAutoBudgetSuggestion {
  category: string
  subcategory: string | null
  kind: string
  nature: CategoryNature | null
  median_amount: string
  occurrences: number
}

export interface BudgetAutoBudgetResponse {
  based_on_months: number
  from_month: string
  to_month: string
  suggestions: BudgetAutoBudgetSuggestion[]
  currency: string
  profile_id: string
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

  flow: (dateFrom: string, dateTo: string): Promise<BudgetFlowResponse> =>
    api.get<BudgetFlowResponse>('/budget/flow', {
      params: { date_from: dateFrom, date_to: dateTo },
    }).then(r => r.data),

  categories: (): Promise<BudgetCategoriesResponse> =>
    api.get<BudgetCategoriesResponse>('/budget/categories').then(r => r.data),

  autoBudget: (months = 3): Promise<BudgetAutoBudgetResponse> =>
    api.get<BudgetAutoBudgetResponse>('/budget/auto-budget', { params: { months } }).then(r => r.data),
}
