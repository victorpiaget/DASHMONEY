import { api } from './api'

export interface Account {
  id: string
  name: string
  currency: string
  opening_balance: string
  opened_on: string
  account_type: 'CHECKING' | 'SAVINGS' | 'INVESTMENT' | 'OTHER'
  profile_id: string
}

export interface AccountBalance {
  balance: string
  currency: string
}

export interface CreateAccountPayload {
  id: string
  name: string
  currency: string
  opening_balance: string
  opened_on: string
  account_type: string
}

export interface BankImportResult {
  format_detected: string
  format_label: string
  imported: number
  skipped_zero: number
  errors_count: number
  errors_preview: string[]
}

export const accountsApi = {
  list: (): Promise<Account[]> =>
    api.get<Account[]>('/accounts').then((r) => r.data),

  create: (data: CreateAccountPayload): Promise<Account> =>
    api.post<Account>('/accounts', data).then((r) => r.data),

  delete: (id: string): Promise<void> =>
    api.delete(`/accounts/${id}`).then(() => undefined),

  getBalance: (accountId: string): Promise<AccountBalance> =>
    api.get<AccountBalance>(`/accounts/${accountId}/balance`).then((r) => r.data),

  importBank: (accountId: string, file: File): Promise<BankImportResult> => {
    const form = new FormData()
    form.append('file', file)
    return api
      .post<BankImportResult>(`/accounts/${accountId}/import-bank`, form, {
        headers: { 'Content-Type': 'multipart/form-data' },
      })
      .then((r) => r.data)
  },
}
