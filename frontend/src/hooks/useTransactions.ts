import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { transactionsApi, type CreateTransactionPayload, type Transaction, type TransactionFilters } from '../lib/transactionsApi'

export function useTransactions(accountId: string, filters: TransactionFilters = {}) {
  return useQuery({
    queryKey: ['transactions', accountId, filters],
    queryFn: () => transactionsApi.list(accountId, filters),
    enabled: !!accountId,
  })
}

export function useCreateTransaction(accountId: string) {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (payload: CreateTransactionPayload) => transactionsApi.create(accountId, payload),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['transactions', accountId] })
      qc.invalidateQueries({ queryKey: ['account-balance', accountId] })
    },
  })
}

export function useUpdateTransaction(accountId: string) {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: ({ txId, payload }: { txId: string; payload: Partial<CreateTransactionPayload> }) =>
      transactionsApi.update(accountId, txId, payload),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['transactions', accountId] })
      qc.invalidateQueries({ queryKey: ['account-balance', accountId] })
    },
  })
}

export function useDeleteTransaction(accountId: string) {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (txId: string) => transactionsApi.delete(accountId, txId),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['transactions', accountId] })
      qc.invalidateQueries({ queryKey: ['account-balance', accountId] })
    },
  })
}

// Re-export type for convenience
export type { Transaction }
