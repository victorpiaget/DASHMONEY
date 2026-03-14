import { api } from './api'

export interface Transfer {
  transfer_id: string
  date: string
  amount: string
  currency: string
  label: string | null
  from_account_id: string
  from_account_name: string
  to_account_id: string
  to_account_name: string
  from_transaction_id: string
  to_transaction_id: string
}

export interface CreateTransferPayload {
  to_account_id: string
  date: string
  amount: string
  category: string
  label?: string
}

export interface UpdateTransferPayload {
  date?: string
  amount?: string
  label?: string
}

export interface AssetTransferRecord {
  sell_trade_id: string
  buy_trade_id: string | null
  date: string
  instrument_symbol: string
  quantity: string
  fees: string
  from_portfolio_id: string
  from_portfolio_name: string
  to_portfolio_id: string | null
  to_portfolio_name: string
}

export const assetTransfersApi = {
  list: (): Promise<AssetTransferRecord[]> =>
    api.get<AssetTransferRecord[]>('/asset-transfers').then((r) => r.data),

  create: (payload: {
    from_portfolio_id: string
    to_portfolio_id: string
    instrument_symbol: string
    quantity: string
    fees?: string
    date: string
  }): Promise<unknown> =>
    api.post('/asset-transfers', payload).then((r) => r.data),

  delete: (sellTradeId: string): Promise<void> =>
    api.delete(`/asset-transfers/${sellTradeId}`).then(() => undefined),
}

export const transfersApi = {
  list: (): Promise<Transfer[]> =>
    api.get<Transfer[]>('/transfers').then((r) => r.data),

  create: (fromAccountId: string, payload: CreateTransferPayload): Promise<unknown> =>
    api.post(`/accounts/${fromAccountId}/transfers`, payload).then((r) => r.data),

  update: (fromAccountId: string, transferId: string, payload: UpdateTransferPayload): Promise<unknown> =>
    api.patch(`/accounts/${fromAccountId}/transfers/${transferId}`, payload).then((r) => r.data),

  delete: (fromAccountId: string, transferId: string): Promise<void> =>
    api.delete(`/accounts/${fromAccountId}/transfers/${transferId}`).then(() => undefined),

  // Lier deux transactions existantes (même montant, comptes différents) en virement
  linkAsTransfer: (fromTxId: string, toTxId: string): Promise<unknown> =>
    api.post('/transfers/link', {
      from_transaction_id: fromTxId,
      to_transaction_id: toTxId,
    }).then((r) => r.data),

  // Convertir une transaction existante en virement (quand la contrepartie n'existe pas) :
  // 1. Créer le virement (même date/montant)
  // 2. Supprimer l'ancienne transaction
  promoteToTransfer: async (
    fromAccountId: string,
    txId: string,
    toAccountId: string,
    date: string,
    amount: string,
    label?: string,
  ): Promise<unknown> => {
    const transfer = await api.post(`/accounts/${fromAccountId}/transfers`, {
      to_account_id: toAccountId,
      date,
      amount,
      category: 'VIREMENT',
      label: label ?? undefined,
    }).then((r) => r.data)
    await api.delete(`/accounts/${fromAccountId}/transactions/${txId}`)
    return transfer
  },
}
