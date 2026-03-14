import { api } from './api'

// ── Types ──────────────────────────────────────────────────────────────────────

export type PortfolioType = 'PEA' | 'CTO' | 'CRYPTO_EXCHANGE' | 'WALLET' | 'OTHER'
export type TradeSide = 'BUY' | 'SELL'
export type InstrumentKind = 'STOCK' | 'ETF' | 'CRYPTO' | 'OTHER'

export interface Portfolio {
  id: string
  name: string
  currency: string
  portfolio_type: PortfolioType
  opened_on: string
  cash_account_id: string
}

export interface PortfolioSnapshot {
  id: string
  portfolio_id: string
  date: string
  value: string
  currency: string
  note: string | null
}

export type TradeType = 'TRADE' | 'TRANSFER'

export interface Trade {
  id: string
  portfolio_id: string
  date: string
  side: TradeSide
  trade_type: TradeType
  instrument_symbol: string
  quantity: string
  price: string
  fees: string
  currency: string
  label: string | null
  linked_cash_tx_id: string | null
}

export interface Position {
  instrument_symbol: string
  quantity: string
}

export interface Instrument {
  symbol: string
  kind: InstrumentKind
  currency: string
  name: string
  ticker: string
}

// ── Payloads ───────────────────────────────────────────────────────────────────

export interface CreatePortfolioPayload {
  name: string
  currency: string
  portfolio_type: string
  opened_on: string
}

export interface CreateTradePayload {
  date: string
  side: string
  instrument_symbol: string
  quantity: string
  price: string
  fees?: string
  label?: string
}

export interface PatchTradePayload {
  date?: string
  quantity?: string
  price?: string
  fees?: string
  label?: string
}

export interface CreateSnapshotPayload {
  date: string
  value: string
  currency: string
  note?: string
}

// ── API clients ────────────────────────────────────────────────────────────────

export const portfoliosApi = {
  list: (): Promise<Portfolio[]> =>
    api.get<Portfolio[]>('/portfolios').then((r) => r.data),

  get: (id: string): Promise<Portfolio> =>
    api.get<Portfolio>(`/portfolios/${id}`).then((r) => r.data),

  create: (payload: CreatePortfolioPayload): Promise<Portfolio> =>
    api.post<Portfolio>('/portfolios', payload).then((r) => r.data),

  update: (id: string, payload: { name?: string; portfolio_type?: string }): Promise<Portfolio> =>
    api.patch<Portfolio>(`/portfolios/${id}`, payload).then((r) => r.data),

  delete: (id: string): Promise<void> =>
    api.delete(`/portfolios/${id}`).then(() => undefined),

  listSnapshots: (portfolioId: string, params?: { from?: string; to?: string }): Promise<PortfolioSnapshot[]> =>
    api.get<PortfolioSnapshot[]>(`/portfolios/${portfolioId}/snapshots`, { params }).then((r) => r.data),

  addSnapshot: (portfolioId: string, payload: CreateSnapshotPayload): Promise<PortfolioSnapshot> =>
    api.post<PortfolioSnapshot>(`/portfolios/${portfolioId}/snapshots`, payload).then((r) => r.data),
}

export const tradesApi = {
  list: (portfolioId: string, params?: Record<string, unknown>): Promise<Trade[]> =>
    api.get<Trade[]>(`/portfolios/${portfolioId}/trades`, { params }).then((r) => r.data),

  create: (portfolioId: string, payload: CreateTradePayload): Promise<Trade> =>
    api.post<Trade>(`/portfolios/${portfolioId}/trades`, payload).then((r) => r.data),

  patch: (portfolioId: string, tradeId: string, payload: PatchTradePayload): Promise<Trade> =>
    api.patch<Trade>(`/portfolios/${portfolioId}/trades/${tradeId}`, payload).then((r) => r.data),

  delete: (portfolioId: string, tradeId: string): Promise<void> =>
    api.delete(`/portfolios/${portfolioId}/trades/${tradeId}`).then(() => undefined),

  positions: (portfolioId: string, asOf?: string): Promise<Position[]> =>
    api
      .get<Position[]>(`/portfolios/${portfolioId}/positions`, {
        params: asOf ? { as_of: asOf } : {},
      })
      .then((r) => r.data),
}

export interface ImportBoursoramaResult {
  imported: number
  skipped_duplicates: number
  skipped_csv_duplicates: number
  created_instruments: string[]
  errors_count: number
  errors_preview: string[]
  note?: string
}

const _importFile = (url: string, portfolioId: string, file: File): Promise<ImportBoursoramaResult> => {
  const form = new FormData()
  form.append('file', file)
  return api.post<ImportBoursoramaResult>(url.replace(':id', portfolioId), form, {
    headers: { 'Content-Type': 'multipart/form-data' },
  }).then((r) => r.data)
}

export const importApi = {
  boursorama: (portfolioId: string, file: File) =>
    _importFile(`/portfolios/${portfolioId}/import-boursorama`, portfolioId, file),
  binance: (portfolioId: string, file: File) =>
    _importFile(`/portfolios/${portfolioId}/import-binance`, portfolioId, file),
}

export interface PricePoint {
  symbol: string
  day: string
  price: string
  currency: string
  source: string
  captured_at: string
}

export interface PnlPoint {
  date: string
  portfolio_value: number
  net_invested: number
  pnl: number
  pnl_pct: number
}

export const snapshotsApi = {
  pnlCurve: (): Promise<PnlPoint[]> =>
    api.get<PnlPoint[]>('/snapshots/pnl-curve').then((r) => r.data),
}

export const pricesApi = {
  latestAll: (): Promise<PricePoint[]> =>
    api.get<PricePoint[]>('/prices/latest-all').then((r) => r.data),

  history: (symbol: string, dateFrom: string, dateTo: string): Promise<PricePoint[]> =>
    api.get<PricePoint[]>('/prices', { params: { symbol, date_from: dateFrom, date_to: dateTo } }).then((r) => r.data),
}

export const instrumentsApi = {
  list: (): Promise<Instrument[]> =>
    api.get<Instrument[]>('/instruments').then((r) => r.data),

  create: (payload: { symbol: string; kind: string; currency: string; name?: string; ticker?: string }): Promise<Instrument> =>
    api.post<Instrument>('/instruments', payload).then((r) => r.data),

  update: (symbol: string, payload: { kind: string; currency: string; name: string; ticker: string }): Promise<Instrument> =>
    api.patch<Instrument>(`/instruments/${symbol}`, payload).then((r) => r.data),

  delete: (symbol: string): Promise<void> =>
    api.delete(`/instruments/${symbol}`).then(() => undefined),
}
