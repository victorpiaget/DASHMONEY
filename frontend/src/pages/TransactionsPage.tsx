import { useState, useMemo, useCallback } from 'react'
import { Link } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import { useAccounts } from '../hooks/useAccounts'
import { useCurrency } from '../context/CurrencyContext'
import { transactionsApi, type GlobalTransaction, type TransactionKind } from '../lib/transactionsApi'
import PeriodPicker, { type PeriodSelection, resolveDates } from '../components/PeriodPicker'

// ── Constantes ─────────────────────────────────────────────────────────────────

const KIND_LABELS: Record<TransactionKind, string> = {
  INCOME: 'Revenu', EXPENSE: 'Dépense', TRANSFER: 'Virement',
}
const KIND_COLORS: Record<TransactionKind, string> = {
  INCOME: 'text-emerald-600', EXPENSE: 'text-red-500', TRANSFER: 'text-blue-600',
}
const KIND_BG: Record<TransactionKind, string> = {
  INCOME: 'bg-emerald-50 text-emerald-700', EXPENSE: 'bg-red-50 text-red-600', TRANSFER: 'bg-blue-50 text-blue-700',
}

type SortField = 'date' | 'amount' | 'category' | 'account_name'
type SortDir = 'asc' | 'desc'

// ── Hook data ──────────────────────────────────────────────────────────────────

function useGlobalTransactions(filters: Parameters<typeof transactionsApi.listGlobal>[0]) {
  return useQuery({
    queryKey: ['transactions-global', filters],
    queryFn: () => transactionsApi.listGlobal(filters),
    staleTime: 30_000,
  })
}

// ── Page ──────────────────────────────────────────────────────────────────────

export default function TransactionsPage() {
  const { format } = useCurrency()
  const { data: accounts = [] } = useAccounts()

  // Filtres
  const [q, setQ] = useState('')
  const [selectedAccountIds, setSelectedAccountIds] = useState<Set<string>>(new Set())
  const [selectedKinds, setSelectedKinds] = useState<Set<TransactionKind>>(new Set())
  const [period, setPeriod] = useState<PeriodSelection>({ type: 'preset', preset: 'tout' })

  // Tri local
  const [sortField, setSortField] = useState<SortField>('date')
  const [sortDir, setSortDir] = useState<SortDir>('desc')

  const minMonth = `${new Date().getFullYear() - 10}-01`
  const dates = useMemo(() => resolveDates(period, `${minMonth}-01`), [period, minMonth])

  const apiFilters = useMemo(() => ({
    date_from: dates.from,
    date_to: dates.to,
    account_ids: selectedAccountIds.size > 0 ? [...selectedAccountIds].join(',') : undefined,
    kinds: selectedKinds.size > 0 ? [...selectedKinds] : undefined,
    q: q.trim() || undefined,
    sort_by: 'date' as const,
    sort_dir: 'desc' as const,
    limit: 5000,
  }), [dates, selectedAccountIds, selectedKinds, q])

  const { data: transactions = [], isLoading, isError, error } = useGlobalTransactions(apiFilters)

  // Tri local sur les résultats
  const sorted = useMemo(() => {
    const copy = [...transactions]
    const dir = sortDir === 'asc' ? 1 : -1
    copy.sort((a, b) => {
      switch (sortField) {
        case 'date': return dir * (a.date.localeCompare(b.date) || a.sequence - b.sequence)
        case 'amount': return dir * (parseFloat(a.amount) - parseFloat(b.amount))
        case 'category': return dir * a.category.localeCompare(b.category)
        case 'account_name': return dir * a.account_name.localeCompare(b.account_name)
        default: return 0
      }
    })
    return copy
  }, [transactions, sortField, sortDir])

  const handleSort = useCallback((col: SortField) => {
    if (sortField === col) setSortDir((d) => d === 'asc' ? 'desc' : 'asc')
    else { setSortField(col); setSortDir(col === 'amount' ? 'desc' : 'asc') }
  }, [sortField])

  const toggleAccount = (id: string) =>
    setSelectedAccountIds((prev) => { const next = new Set(prev); next.has(id) ? next.delete(id) : next.add(id); return next })

  const toggleKind = (k: TransactionKind) =>
    setSelectedKinds((prev) => { const next = new Set(prev); next.has(k) ? next.delete(k) : next.add(k); return next })

  // KPIs sur les résultats filtrés
  const kpis = useMemo(() => {
    let income = 0, expenses = 0
    for (const tx of sorted) {
      const amt = parseFloat(tx.amount)
      if (tx.kind === 'INCOME') income += amt
      else if (tx.kind === 'EXPENSE') expenses += Math.abs(amt)
    }
    return { income, expenses, net: income - expenses, count: sorted.length }
  }, [sorted])

  const sortIcon = (col: SortField) =>
    sortField === col ? (sortDir === 'asc' ? ' ↑' : ' ↓') : ''

  return (
    <div className="h-full flex flex-col p-6 gap-4 overflow-hidden">

      {/* Header */}
      <div className="flex-none flex items-center justify-between gap-4">
        <div>
          <h1 className="text-xl font-semibold text-gray-900">Transactions</h1>
          <p className="text-xs text-gray-400 mt-0.5">Tous les comptes</p>
        </div>
        <PeriodPicker selection={period} onChange={setPeriod} minMonth={minMonth} />
      </div>

      {/* KPI row */}
      <div className="flex-none grid grid-cols-4 gap-3">
        {[
          { label: 'Transactions', value: String(kpis.count), color: 'text-gray-900', raw: true },
          { label: 'Revenus', value: format(kpis.income.toFixed(2), 'EUR'), color: 'text-emerald-600', raw: false },
          { label: 'Dépenses', value: `−${format(kpis.expenses.toFixed(2), 'EUR')}`, color: 'text-red-600', raw: false },
          { label: 'Cash flow net', value: (kpis.net >= 0 ? '' : '−') + format(Math.abs(kpis.net).toFixed(2), 'EUR'), color: kpis.net >= 0 ? 'text-gray-900' : 'text-red-600', raw: false },
        ].map(({ label, value, color }) => (
          <div key={label} className="bg-white rounded-xl border border-gray-100 shadow-sm px-4 py-3">
            <p className="text-[10px] font-medium text-gray-400 uppercase tracking-wider">{label}</p>
            <p className={`text-lg font-semibold tabular-nums mt-1 ${color}`}>{isLoading ? '—' : value}</p>
          </div>
        ))}
      </div>

      {/* Filters row */}
      <div className="flex-none flex items-center gap-3 flex-wrap">
        {/* Search */}
        <div className="relative">
          <input
            type="text"
            value={q}
            onChange={(e) => setQ(e.target.value)}
            placeholder="Rechercher…"
            className="pl-8 pr-3 py-1.5 text-sm border border-gray-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-gray-900 w-48"
          />
          <span className="absolute left-2.5 top-1/2 -translate-y-1/2 text-gray-400 text-xs">⌕</span>
        </div>

        {/* Kind pills */}
        <div className="flex items-center gap-1">
          {(['INCOME', 'EXPENSE', 'TRANSFER'] as TransactionKind[]).map((k) => (
            <button
              key={k}
              onClick={() => toggleKind(k)}
              className={`px-2.5 py-1 text-xs font-medium rounded-full border transition-colors ${
                selectedKinds.has(k)
                  ? KIND_BG[k] + ' border-transparent'
                  : 'text-gray-500 border-gray-200 hover:border-gray-300'
              }`}
            >
              {KIND_LABELS[k]}
            </button>
          ))}
        </div>

        {/* Account filter */}
        <div className="flex items-center gap-1 flex-wrap">
          {accounts.map((a) => (
            <button
              key={a.id}
              onClick={() => toggleAccount(a.id)}
              className={`px-2.5 py-1 text-xs font-medium rounded-full border transition-colors ${
                selectedAccountIds.has(a.id)
                  ? 'bg-gray-900 text-white border-transparent'
                  : 'text-gray-500 border-gray-200 hover:border-gray-300'
              }`}
            >
              {a.name}
            </button>
          ))}
        </div>

        {/* Clear */}
        {(selectedAccountIds.size > 0 || selectedKinds.size > 0 || q) && (
          <button
            onClick={() => { setSelectedAccountIds(new Set()); setSelectedKinds(new Set()); setQ('') }}
            className="text-xs text-gray-400 hover:text-gray-700 transition-colors ml-auto"
          >
            Effacer les filtres ×
          </button>
        )}
      </div>

      {/* Table */}
      <div className="flex-1 min-h-0 bg-white rounded-2xl border border-gray-100 shadow-sm flex flex-col overflow-hidden">
        <table className="w-full text-xs">
          <thead className="sticky top-0 bg-white z-10 border-b border-gray-100">
            <tr>
              <th
                className="text-left text-gray-400 font-medium py-3 px-4 cursor-pointer hover:text-gray-700 select-none"
                onClick={() => handleSort('date')}
              >
                Date{sortIcon('date')}
              </th>
              <th
                className="text-left text-gray-400 font-medium py-3 px-3 cursor-pointer hover:text-gray-700 select-none"
                onClick={() => handleSort('account_name')}
              >
                Compte{sortIcon('account_name')}
              </th>
              <th className="text-left text-gray-400 font-medium py-3 px-3">Libellé</th>
              <th
                className="text-left text-gray-400 font-medium py-3 px-3 cursor-pointer hover:text-gray-700 select-none"
                onClick={() => handleSort('category')}
              >
                Catégorie{sortIcon('category')}
              </th>
              <th className="text-left text-gray-400 font-medium py-3 px-3">Type</th>
              <th
                className="text-right text-gray-400 font-medium py-3 px-4 cursor-pointer hover:text-gray-700 select-none"
                onClick={() => handleSort('amount')}
              >
                Montant{sortIcon('amount')}
              </th>
            </tr>
          </thead>
        </table>

        <div className="flex-1 overflow-y-auto">
          {isLoading ? (
            <div className="flex items-center justify-center h-full">
              <div className="w-5 h-5 border-2 border-gray-200 border-t-gray-700 rounded-full animate-spin" />
            </div>
          ) : isError ? (
            <div className="flex flex-col items-center justify-center h-full gap-2 text-red-400">
              <span className="text-4xl opacity-20">⚠</span>
              <p className="text-sm font-medium">Erreur de chargement</p>
              <p className="text-xs text-gray-400">{(error as Error)?.message ?? 'Erreur inconnue'}</p>
            </div>
          ) : sorted.length === 0 ? (
            <div className="flex flex-col items-center justify-center h-full gap-2 text-gray-400">
              <span className="text-4xl opacity-20">◎</span>
              <p className="text-sm">Aucune transaction sur cette période</p>
            </div>
          ) : (
            <table className="w-full text-xs">
              <tbody>
                {sorted.map((tx) => (
                  <TxRow key={tx.id} tx={tx} />
                ))}
              </tbody>
            </table>
          )}
        </div>
      </div>
    </div>
  )
}

// ── Row ────────────────────────────────────────────────────────────────────────

function TxRow({ tx }: { tx: GlobalTransaction }) {
  const { format } = useCurrency()
  const amount = parseFloat(tx.amount)
  const fmtDate = new Date(tx.date + 'T00:00:00').toLocaleDateString('fr-FR', { day: '2-digit', month: 'short', year: '2-digit' })

  return (
    <tr className="border-b border-gray-50 hover:bg-gray-50 transition-colors">
      <td className="py-2.5 px-4 text-gray-500 whitespace-nowrap tabular-nums">{fmtDate}</td>
      <td className="py-2.5 px-3">
        <Link
          to={`/accounts/${tx.account_id}`}
          className="text-gray-700 hover:text-gray-900 hover:underline"
        >
          {tx.account_name}
        </Link>
      </td>
      <td className="py-2.5 px-3 text-gray-600 max-w-[220px] truncate">
        {tx.label || <span className="text-gray-300 italic">—</span>}
      </td>
      <td className="py-2.5 px-3 text-gray-500">
        <span className="truncate block max-w-[140px]">
          {tx.category}{tx.subcategory ? <span className="text-gray-400"> · {tx.subcategory}</span> : null}
        </span>
      </td>
      <td className="py-2.5 px-3">
        <span className={`px-1.5 py-0.5 rounded-full text-[10px] font-medium ${KIND_BG[tx.kind]}`}>
          {KIND_LABELS[tx.kind]}
        </span>
      </td>
      <td className={`py-2.5 px-4 text-right font-medium tabular-nums ${KIND_COLORS[tx.kind]}`}>
        {tx.kind === 'INCOME' && '+'}
        {format(Math.abs(amount).toFixed(2), tx.account_currency)}
      </td>
    </tr>
  )
}
