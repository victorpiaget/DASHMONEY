import { useQuery } from '@tanstack/react-query'
import { netWorthApi } from '../lib/netWorthApi'

export function useNetWorthGrouped() {
  return useQuery({
    queryKey: ['net-worth', 'grouped'],
    queryFn: netWorthApi.getGrouped,
  })
}

export function useCashFlow() {
  return useQuery({
    queryKey: ['net-worth', 'cash-flow'],
    queryFn: netWorthApi.getCashFlow,
  })
}

export function useNetWorthFullTimeseries(from: string, to: string) {
  return useQuery({
    queryKey: ['net-worth-full', 'timeseries', from, to],
    queryFn: () => netWorthApi.getFullTimeseries(from, to),
    enabled: !!from && !!to,
  })
}

export function useNetWorthGroupedTimeseries(from: string, to: string) {
  return useQuery({
    queryKey: ['net-worth-grouped', 'timeseries', from, to],
    queryFn: () => netWorthApi.getGroupedTimeseries(from, to),
    enabled: !!from && !!to,
  })
}
