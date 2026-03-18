import { api } from './api'

export const exchangeRatesApi = {
  getLatest: (): Promise<Record<string, number>> =>
    api.get<Record<string, number>>('/exchange-rates/latest').then((r) => r.data),

  triggerUpdate: (): Promise<{ stored: number; failed: string[] }> =>
    api.post('/exchange-rates/update').then((r) => r.data),
}
