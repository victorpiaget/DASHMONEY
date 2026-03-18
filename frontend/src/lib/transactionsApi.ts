import { api } from './api'

export type TransactionKind = 'INCOME' | 'EXPENSE' | 'TRANSFER'

export interface Transaction {
  id: string
  account_id: string
  date: string
  sequence: number
  amount: string
  currency: string
  kind: TransactionKind
  category: string
  subcategory: string | null
  label: string | null
  created_at: string
  transfer_id: string | null
}

export type SortField = 'date' | 'amount' | 'kind' | 'category' | 'subcategory' | 'label'
export type SortDir = 'asc' | 'desc'

export interface TransactionFilters {
  q?: string
  date_from?: string
  date_to?: string
  kinds?: TransactionKind[]
  categories?: string[]
  subcategories?: string[]
  sort_by?: SortField
  sort_dir?: SortDir
}

export interface CreateTransactionPayload {
  date: string
  amount: string
  kind: TransactionKind
  category: string
  subcategory?: string
  label?: string
}

export interface GlobalTransaction extends Transaction {
  account_name: string
  account_currency: string
}

export interface GlobalTransactionFilters {
  account_ids?: string
  date_from?: string
  date_to?: string
  kinds?: TransactionKind[]
  categories?: string[]
  q?: string
  sort_by?: SortField
  sort_dir?: SortDir
  limit?: number
}

export const transactionsApi = {
  list: (accountId: string, filters: TransactionFilters = {}): Promise<Transaction[]> =>
    api
      .get<Transaction[]>(`/accounts/${accountId}/transactions`, {
        params: { sort_by: 'date', sort_dir: 'desc', ...filters },
      })
      .then((r) => r.data),

  create: (accountId: string, payload: CreateTransactionPayload): Promise<Transaction> =>
    api.post<Transaction>(`/accounts/${accountId}/transactions`, payload).then((r) => r.data),

  update: (accountId: string, txId: string, payload: Partial<CreateTransactionPayload>): Promise<Transaction> =>
    api.patch<Transaction>(`/accounts/${accountId}/transactions/${txId}`, payload).then((r) => r.data),

  delete: (accountId: string, txId: string): Promise<void> =>
    api.delete(`/accounts/${accountId}/transactions/${txId}`).then(() => undefined),

  listGlobal: (filters: GlobalTransactionFilters = {}): Promise<GlobalTransaction[]> =>
    api.get<GlobalTransaction[]>('/transactions', { params: filters }).then((r) => r.data),
}
