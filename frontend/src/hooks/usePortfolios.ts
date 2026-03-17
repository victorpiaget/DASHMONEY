import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import {
  portfoliosApi,
  tradesApi,
  instrumentsApi,
  pricesApi,
  snapshotsApi,
  importApi,
  type CreatePortfolioPayload,
  type CreateTradePayload,
  type PatchTradePayload,
  type CreateSnapshotPayload,
} from '../lib/portfoliosApi'

// ── Portfolios ─────────────────────────────────────────────────────────────────

export function usePortfolios() {
  return useQuery({ queryKey: ['portfolios'], queryFn: portfoliosApi.list })
}

export function useCreatePortfolio() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (payload: CreatePortfolioPayload) => portfoliosApi.create(payload),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['portfolios'] }),
  })
}

export function useDeletePortfolio() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (id: string) => portfoliosApi.delete(id),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['portfolios'] }),
  })
}

// ── Trades ─────────────────────────────────────────────────────────────────────

export function useTrades(portfolioId: string, params?: Record<string, unknown>) {
  return useQuery({
    queryKey: ['trades', portfolioId, params],
    queryFn: () => tradesApi.list(portfolioId, params),
    enabled: !!portfolioId,
  })
}

export function useCreateTrade(portfolioId: string) {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (payload: CreateTradePayload) => tradesApi.create(portfolioId, payload),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['trades', portfolioId] })
      qc.invalidateQueries({ queryKey: ['positions', portfolioId] })
    },
  })
}

export function usePatchTrade(portfolioId: string) {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: ({ tradeId, payload }: { tradeId: string; payload: PatchTradePayload }) =>
      tradesApi.patch(portfolioId, tradeId, payload),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['trades', portfolioId] })
      qc.invalidateQueries({ queryKey: ['positions', portfolioId] })
    },
  })
}

export function useDeleteTrade(portfolioId: string) {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (tradeId: string) => tradesApi.delete(portfolioId, tradeId),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['trades', portfolioId] })
      qc.invalidateQueries({ queryKey: ['positions', portfolioId] })
    },
  })
}

// ── Positions ──────────────────────────────────────────────────────────────────

export function usePositions(portfolioId: string) {
  return useQuery({
    queryKey: ['positions', portfolioId],
    queryFn: () => tradesApi.positions(portfolioId),
    enabled: !!portfolioId,
  })
}

// ── Snapshots ──────────────────────────────────────────────────────────────────

export function useSnapshots(portfolioId: string) {
  return useQuery({
    queryKey: ['snapshots', portfolioId],
    queryFn: () => portfoliosApi.listSnapshots(portfolioId),
    enabled: !!portfolioId,
  })
}

export function useAddSnapshot(portfolioId: string) {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (payload: CreateSnapshotPayload) => portfoliosApi.addSnapshot(portfolioId, payload),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['snapshots', portfolioId] }),
  })
}

// ── PnL curve ──────────────────────────────────────────────────────────────────

export function usePnlCurve() {
  return useQuery({
    queryKey: ['snapshots', 'pnl-curve'],
    queryFn: snapshotsApi.pnlCurve,
    staleTime: 5 * 60 * 1000,
  })
}

// ── Prices ─────────────────────────────────────────────────────────────────────

export function useLatestPrices() {
  return useQuery({
    queryKey: ['prices', 'latest-all'],
    queryFn: pricesApi.latestAll,
    staleTime: 5 * 60 * 1000,
  })
}

export function usePriceHistory(symbol: string | null, dateFrom: string, dateTo: string) {
  return useQuery({
    queryKey: ['prices', 'history', symbol, dateFrom, dateTo],
    queryFn: () => pricesApi.history(symbol!, dateFrom, dateTo),
    enabled: !!symbol && !!dateFrom && !!dateTo,
    staleTime: 10 * 60 * 1000,
  })
}

// ── Instruments ────────────────────────────────────────────────────────────────

export function useInstruments() {
  return useQuery({ queryKey: ['instruments'], queryFn: instrumentsApi.list })
}

export function useCreateInstrument() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (payload: { symbol: string; kind: string; currency: string; name?: string; ticker?: string }) =>
      instrumentsApi.create(payload),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['instruments'] }),
  })
}

export function useUpdateInstrument() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: ({ symbol, payload }: { symbol: string; payload: { kind: string; currency: string; name: string; ticker: string } }) =>
      instrumentsApi.update(symbol, payload),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['instruments'] }),
  })
}

export function useDeleteInstrument() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (symbol: string) => instrumentsApi.delete(symbol),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['instruments'] }),
  })
}

// ── Import ──────────────────────────────────────────────────────────────────

export function useImportBoursorama(portfolioId: string) {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (file: File) => importApi.boursorama(portfolioId, file),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['trades', portfolioId] })
      qc.invalidateQueries({ queryKey: ['positions', portfolioId] })
      qc.invalidateQueries({ queryKey: ['instruments'] })
    },
  })
}

export function useImportBinance(portfolioId: string) {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (file: File) => importApi.binance(portfolioId, file),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['trades', portfolioId] })
      qc.invalidateQueries({ queryKey: ['positions', portfolioId] })
      qc.invalidateQueries({ queryKey: ['instruments'] })
    },
  })
}
