import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { budgetApi } from '../lib/budgetApi'

export function useBudgetEnvelopes() {
  return useQuery({
    queryKey: ['budget-envelopes'],
    queryFn: budgetApi.listEnvelopes,
  })
}

export function useBudgetComparison(month: string) {
  return useQuery({
    queryKey: ['budget-comparison', month],
    queryFn: () => budgetApi.comparison(month),
    enabled: !!month,
  })
}

export function useUpsertEnvelope() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: budgetApi.upsertEnvelope,
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['budget-envelopes'] })
      qc.invalidateQueries({ queryKey: ['budget-comparison'] })
    },
  })
}

export function useDeleteEnvelope() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: budgetApi.deleteEnvelope,
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['budget-envelopes'] })
      qc.invalidateQueries({ queryKey: ['budget-comparison'] })
    },
  })
}

export function useBudgetHistory(months = 6) {
  return useQuery({
    queryKey: ['budget-history', months],
    queryFn: () => budgetApi.history(months),
  })
}

export function useBudgetFlow(dateFrom: string, dateTo: string, enabled = true) {
  return useQuery({
    queryKey: ['budget-flow', dateFrom, dateTo],
    queryFn: () => budgetApi.flow(dateFrom, dateTo),
    enabled: enabled && !!dateFrom && !!dateTo,
  })
}

export function useBudgetCategories() {
  return useQuery({
    queryKey: ['budget-categories'],
    queryFn: budgetApi.categories,
    staleTime: 60_000,
  })
}

export function useBudgetAutoFill(months = 3, enabled = true) {
  return useQuery({
    queryKey: ['budget-auto-budget', months],
    queryFn: () => budgetApi.autoBudget(months),
    enabled,
    staleTime: 60_000,
  })
}
