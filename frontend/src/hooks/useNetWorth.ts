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
