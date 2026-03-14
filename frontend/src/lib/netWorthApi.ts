import { api } from './api'

export interface NetWorthResponse {
  currency: string
  at: string | null
  net_worth: string
}

export interface NetWorthGroupedResponse {
  currency: string
  at: string | null
  total: string
  groups: { key: string; net_worth: string }[]
}

export const netWorthApi = {
  get: (): Promise<NetWorthResponse> =>
    api.get<NetWorthResponse>('/net-worth').then((r) => r.data),

  getGrouped: (): Promise<NetWorthGroupedResponse> =>
    api.get<NetWorthGroupedResponse>('/net-worth/grouped').then((r) => r.data),
}
