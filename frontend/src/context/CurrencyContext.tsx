import { createContext, useContext, useState, useEffect, type ReactNode } from 'react'
import { useQuery } from '@tanstack/react-query'
import { exchangeRatesApi } from '../lib/exchangeRatesApi'

// ── Devises supportées ────────────────────────────────────────────────────────

export interface CurrencyMeta {
  code: string
  label: string
  symbol: string
  decimals: number
}

export const SUPPORTED_CURRENCIES: CurrencyMeta[] = [
  { code: 'EUR', label: 'Euro',           symbol: '€',  decimals: 2 },
  { code: 'USD', label: 'Dollar US',      symbol: '$',  decimals: 2 },
  { code: 'GBP', label: 'Livre sterling', symbol: '£',  decimals: 2 },
  { code: 'CHF', label: 'Franc suisse',   symbol: 'Fr', decimals: 2 },
  { code: 'JPY', label: 'Yen',            symbol: '¥',  decimals: 0 },
  { code: 'CAD', label: 'Dollar canadien',symbol: 'CA$',decimals: 2 },
  { code: 'AUD', label: 'Dollar australien',symbol:'A$',decimals: 2 },
  { code: 'SGD', label: 'Dollar singapourien',symbol:'S$',decimals: 2 },
  { code: 'BTC', label: 'Bitcoin',        symbol: '₿',  decimals: 8 },
  { code: 'ETH', label: 'Ethereum',       symbol: 'Ξ',  decimals: 6 },
  { code: 'USDT',label: 'Tether',         symbol: '₮',  decimals: 2 },
]

const FIAT_CODES = new Set(['EUR','USD','GBP','CHF','JPY','CAD','AUD','SGD','USDT'])

const LS_KEY = 'dm_display_currency'

// ── Formatage ─────────────────────────────────────────────────────────────────

function formatWithMeta(amount: number, meta: CurrencyMeta): string {
  if (!FIAT_CODES.has(meta.code)) {
    // Crypto : formatage manuel
    const formatted = amount.toFixed(meta.decimals)
    return `${formatted} ${meta.symbol}`
  }
  try {
    return new Intl.NumberFormat('fr-FR', {
      style: 'currency',
      currency: meta.code,
      minimumFractionDigits: meta.decimals,
      maximumFractionDigits: meta.decimals,
    }).format(amount)
  } catch {
    return `${amount.toFixed(meta.decimals)} ${meta.symbol}`
  }
}

// ── Contexte ──────────────────────────────────────────────────────────────────

interface CurrencyContextValue {
  displayCurrency: string
  setDisplayCurrency: (currency: string) => void
  rates: Record<string, number>
  isLoading: boolean
  isError: boolean
  /** Convertit un montant de sa devise native vers la devise d'affichage. */
  convert: (amount: number | string, fromCurrency: string) => number
  /** Convertit entre deux devises quelconques (sans passer par displayCurrency). */
  convertBetween: (amount: number | string, from: string, to: string) => number
  /** Convertit + formate (ex: "1 234,56 $") */
  format: (amount: number | string, fromCurrency: string) => string
}

const CurrencyContext = createContext<CurrencyContextValue | null>(null)

// ── Provider ──────────────────────────────────────────────────────────────────

export function CurrencyProvider({ children }: { children: ReactNode }) {
  const [displayCurrency, setDisplayCurrencyState] = useState<string>(() => {
    return localStorage.getItem(LS_KEY) ?? 'EUR'
  })

  const { data: rates = { EUR: 1.0 }, isLoading, isError } = useQuery({
    queryKey: ['exchange-rates'],
    queryFn: exchangeRatesApi.getLatest,
    staleTime: 1000 * 60 * 60, // 1 heure
    retry: 2,
  })

  const setDisplayCurrency = (currency: string) => {
    localStorage.setItem(LS_KEY, currency)
    setDisplayCurrencyState(currency)
  }

  // Vérifie que la devise sauvegardée est toujours supportée
  useEffect(() => {
    const supported = SUPPORTED_CURRENCIES.some((c) => c.code === displayCurrency)
    if (!supported) setDisplayCurrency('EUR')
  }, [displayCurrency])

  const convert = (amount: number | string, fromCurrency: string): number => {
    const num = typeof amount === 'string' ? parseFloat(amount) : amount
    if (isNaN(num)) return 0
    if (fromCurrency === displayCurrency) return num

    const rateFrom = rates[fromCurrency] ?? 1
    const rateTo = rates[displayCurrency] ?? 1

    // fromCurrency → EUR → displayCurrency
    // amount * (rateTo / rateFrom)
    return num * (rateTo / rateFrom)
  }

  const convertBetween = (amount: number | string, from: string, to: string): number => {
    const num = typeof amount === 'string' ? parseFloat(amount) : amount
    if (isNaN(num)) return 0
    if (from === to) return num
    const rateFrom = rates[from] ?? 1
    const rateTo = rates[to] ?? 1
    return num * (rateTo / rateFrom)
  }

  const format = (amount: number | string, fromCurrency: string): string => {
    const converted = convert(amount, fromCurrency)
    const meta = SUPPORTED_CURRENCIES.find((c) => c.code === displayCurrency)
    if (!meta) return `${converted.toFixed(2)} ${displayCurrency}`
    return formatWithMeta(converted, meta)
  }

  return (
    <CurrencyContext.Provider value={{ displayCurrency, setDisplayCurrency, rates, isLoading, isError, convert, convertBetween, format }}>
      {children}
    </CurrencyContext.Provider>
  )
}

// ── Hook ──────────────────────────────────────────────────────────────────────

export function useCurrency(): CurrencyContextValue {
  const ctx = useContext(CurrencyContext)
  if (!ctx) throw new Error('useCurrency must be used within CurrencyProvider')
  return ctx
}
