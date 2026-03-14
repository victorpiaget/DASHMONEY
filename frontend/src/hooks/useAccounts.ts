import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { accountsApi, type CreateAccountPayload } from '../lib/accountsApi'

export function useAccountBalance(accountId: string) {
  return useQuery({
    queryKey: ['account-balance', accountId],
    queryFn: () => accountsApi.getBalance(accountId),
  })
}

export function useAccounts() {
  return useQuery({ queryKey: ['accounts'], queryFn: accountsApi.list })
}

export function useCreateAccount() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (data: CreateAccountPayload) => accountsApi.create(data),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['accounts'] }),
  })
}

export function useDeleteAccount() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (id: string) => accountsApi.delete(id),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['accounts'] }),
  })
}

export function useImportVictor(accountId: string) {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (file: File) => accountsApi.importVictor(accountId, file),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['accounts'] })
      qc.invalidateQueries({ queryKey: ['account-balance', accountId] })
    },
  })
}
