import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { transfersApi } from '../lib/transfersApi'
import type { CreateTransferPayload, UpdateTransferPayload } from '../lib/transfersApi'

const TRANSFERS_KEY = ['transfers']

export function useTransfers() {
  return useQuery({
    queryKey: TRANSFERS_KEY,
    queryFn: transfersApi.list,
  })
}

export function useCreateTransfer() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: ({ fromAccountId, payload }: { fromAccountId: string; payload: CreateTransferPayload }) =>
      transfersApi.create(fromAccountId, payload),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: TRANSFERS_KEY })
      qc.invalidateQueries({ queryKey: ['accounts'] })
      qc.invalidateQueries({ queryKey: ['transactions'] })
    },
  })
}

export function useUpdateTransfer() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: ({ fromAccountId, transferId, payload }: { fromAccountId: string; transferId: string; payload: UpdateTransferPayload }) =>
      transfersApi.update(fromAccountId, transferId, payload),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: TRANSFERS_KEY })
      qc.invalidateQueries({ queryKey: ['accounts'] })
      qc.invalidateQueries({ queryKey: ['transactions'] })
    },
  })
}

export function useDeleteTransfer() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: ({ fromAccountId, transferId }: { fromAccountId: string; transferId: string }) =>
      transfersApi.delete(fromAccountId, transferId),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: TRANSFERS_KEY })
      qc.invalidateQueries({ queryKey: ['accounts'] })
      qc.invalidateQueries({ queryKey: ['transactions'] })
    },
  })
}

export function useLinkAsTransfer() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: ({ fromTxId, toTxId }: { fromTxId: string; toTxId: string }) =>
      transfersApi.linkAsTransfer(fromTxId, toTxId),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: TRANSFERS_KEY })
      qc.invalidateQueries({ queryKey: ['accounts'] })
      qc.invalidateQueries({ queryKey: ['transactions'] })
    },
  })
}

export function usePromoteToTransfer() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: ({
      fromAccountId,
      txId,
      toAccountId,
      date,
      amount,
      label,
    }: {
      fromAccountId: string
      txId: string
      toAccountId: string
      date: string
      amount: string
      label?: string
    }) => transfersApi.promoteToTransfer(fromAccountId, txId, toAccountId, date, amount, label),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: TRANSFERS_KEY })
      qc.invalidateQueries({ queryKey: ['accounts'] })
      qc.invalidateQueries({ queryKey: ['transactions'] })
    },
  })
}
