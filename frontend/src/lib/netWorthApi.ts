import { api } from './api'
import type { AxiosResponse } from 'axios'

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

export interface CashFlowMonth {
  month: string
  income: string
  expenses: string
}

export interface CashFlowResponse {
  currency: string
  current: CashFlowMonth
  previous: CashFlowMonth
}

export interface NetWorthFullTimeseriesPoint {
  bucket: string
  balance_end: string
}

export interface NetWorthFullTimeseriesResponse {
  currency: string
  date_from: string
  date_to: string
  granularity: string
  points: NetWorthFullTimeseriesPoint[]
}

export interface NetWorthGroupedTimeseriesGroup {
  key: string
  points: { bucket: string; balance_end: string }[]
}

export interface NetWorthGroupedTimeseriesResponse {
  currency: string
  date_from: string
  date_to: string
  granularity: string
  total_points: { bucket: string; balance_end: string }[]
  groups: NetWorthGroupedTimeseriesGroup[]
}

export const netWorthApi = {
  get: (): Promise<NetWorthResponse> =>
    api.get<NetWorthResponse>('/net-worth').then((r) => r.data),

  getGrouped: (): Promise<NetWorthGroupedResponse> =>
    api.get<NetWorthGroupedResponse>('/net-worth/grouped').then((r) => r.data),

  getCashFlow: (): Promise<CashFlowResponse> =>
    api.get<CashFlowResponse>('/net-worth/cash-flow').then((r) => r.data),

  getFullTimeseries: (from: string, to: string, granularity = 'auto'): Promise<NetWorthFullTimeseriesResponse> =>
    api
      .get<NetWorthFullTimeseriesResponse>('/net-worth/full/timeseries', { params: { from, to, granularity } })
      .then((r: AxiosResponse<NetWorthFullTimeseriesResponse>) => r.data),

  getGroupedTimeseries: (from: string, to: string, granularity = 'auto'): Promise<NetWorthGroupedTimeseriesResponse> =>
    api
      .get<NetWorthGroupedTimeseriesResponse>('/net-worth/timeseries/grouped', { params: { from, to, granularity } })
      .then((r: AxiosResponse<NetWorthGroupedTimeseriesResponse>) => r.data),
}
