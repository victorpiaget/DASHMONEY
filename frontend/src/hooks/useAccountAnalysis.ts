import { useQuery } from '@tanstack/react-query'
import { analysisApi } from '../lib/analysisApi'

export function useAccountTimeSeries(
  accountId: string,
  from: string,
  to: string,
  granularity = 'auto',
) {
  return useQuery({
    queryKey: ['account-timeseries', accountId, from, to, granularity],
    queryFn: () => analysisApi.timeseries(accountId, from, to, granularity),
    enabled: !!accountId && !!from && !!to,
  })
}

export function useAccountBudgetSummary(
  accountId: string,
  dateFrom?: string,
  dateTo?: string,
) {
  return useQuery({
    queryKey: ['account-budget-summary', accountId, dateFrom, dateTo],
    queryFn: () => analysisApi.budgetSummary(accountId, dateFrom, dateTo),
    enabled: !!accountId,
  })
}
