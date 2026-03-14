import { api } from './api'

export interface TimeSeriesPoint {
  bucket: string
  income: string
  expense: string
  net: string
  balance_start: string
  balance_end: string
}

export interface TimeSeriesResponse {
  account_id: string
  currency: string
  date_from: string
  date_to: string
  granularity: string
  points: TimeSeriesPoint[]
}

export interface BudgetSummary {
  account_id: string
  currency: string
  range: { date_from: string | null; date_to: string | null }
  totals_by_kind: { kind: string; total: string }[]
  expense_by_category: { category: string; total: string }[]
  expense_by_subcategory: { category: string; subcategory: string; total: string }[]
  monthly_by_kind: { year: number; month: number; kind: string; total: string }[]
}

export const analysisApi = {
  timeseries: (
    accountId: string,
    from: string,
    to: string,
    granularity = 'auto',
  ): Promise<TimeSeriesResponse> =>
    api
      .get<TimeSeriesResponse>(`/accounts/${accountId}/timeseries`, {
        params: { from, to, granularity },
      })
      .then((r) => r.data),

  budgetSummary: (
    accountId: string,
    dateFrom?: string,
    dateTo?: string,
  ): Promise<BudgetSummary> =>
    api
      .get<BudgetSummary>(`/accounts/${accountId}/budget-summary`, {
        params: { date_from: dateFrom, date_to: dateTo },
      })
      .then((r) => r.data),
}
