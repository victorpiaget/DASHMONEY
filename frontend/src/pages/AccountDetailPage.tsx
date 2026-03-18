import { type FormEvent, useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import { useAccounts, useAccountBalance } from '../hooks/useAccounts'
import { useTransactions, useCreateTransaction, useUpdateTransaction, useDeleteTransaction } from '../hooks/useTransactions'
import { useCreateTransfer } from '../hooks/useTransfers'
import { useCategories } from '../hooks/useCategories'
import { formatDate } from '../lib/formatters'
import { useCurrency } from '../context/CurrencyContext'
import { CurrencyAmountInput } from '../components/CurrencyAmountInput'
import type { Transaction, TransactionKind, CreateTransactionPayload, TransactionFilters, SortField, SortDir } from '../lib/transactionsApi'

const TYPE_LABELS: Record<string, string> = {
  CHECKING: 'Courant',
  SAVINGS: 'Épargne',
  INVESTMENT: 'Investissement',
  OTHER: 'Autre',
}

const KIND_LABELS: Record<string, string> = {
  INCOME: 'Revenu',
  EXPENSE: 'Dépense',
  TRANSFER: 'Virement',
}

const KIND_COLORS: Record<string, string> = {
  INCOME: 'bg-emerald-50 text-emerald-700',
  EXPENSE: 'bg-red-50 text-red-600',
  TRANSFER: 'bg-blue-50 text-blue-700',
}

type ModalMode = { type: 'create' } | { type: 'edit'; tx: Transaction }

const SORTABLE_COLUMNS: { key: SortField; label: string }[] = [
  { key: 'date', label: 'Date' },
  { key: 'category', label: 'Catégorie' },
  { key: 'subcategory', label: 'Sous-catégorie' },
  { key: 'label', label: 'Libellé' },
  { key: 'kind', label: 'Type' },
  { key: 'amount', label: 'Montant' },
]

export default function AccountDetailPage() {
  const { id } = useParams<{ id: string }>()
  const { data: accounts = [] } = useAccounts()
  const account = accounts.find((a) => a.id === id)

  const { data: balanceData } = useAccountBalance(id ?? '')
  const { format } = useCurrency()
  const createTransaction = useCreateTransaction(id ?? '')
  const updateTransaction = useUpdateTransaction(id ?? '')
  const deleteTransaction = useDeleteTransaction(id ?? '')
  const { data: categoriesData = [] } = useCategories()
  const categories = categoriesData.map((c) => ({
    name: c.name,
    subcategories: c.subcategories.map((s) => s.name),
  }))

  // Filtres & tri
  const [q, setQ] = useState('')
  const [dateFrom, setDateFrom] = useState('')
  const [dateTo, setDateTo] = useState('')
  const [selectedKinds, setSelectedKinds] = useState<TransactionKind[]>([])
  const [selectedCategory, setSelectedCategory] = useState('')
  const [selectedSubcategory, setSelectedSubcategory] = useState('')
  const [sortBy, setSortBy] = useState<SortField>('date')
  const [sortDir, setSortDir] = useState<SortDir>('desc')

  const [modal, setModal] = useState<ModalMode | null>(null)
  const [transferModal, setTransferModal] = useState(false)
  const createTransfer = useCreateTransfer()

  const filters: TransactionFilters = {
    q: q || undefined,
    date_from: dateFrom || undefined,
    date_to: dateTo || undefined,
    kinds: selectedKinds.length > 0 ? selectedKinds : undefined,
    categories: selectedCategory ? [selectedCategory] : undefined,
    subcategories: selectedSubcategory ? [selectedSubcategory] : undefined,
    sort_by: sortBy,
    sort_dir: sortDir,
  }

  const { data: transactions = [], isLoading } = useTransactions(id ?? '', filters)

  const handleSort = (col: SortField) => {
    if (sortBy === col) {
      setSortDir((d) => (d === 'asc' ? 'desc' : 'asc'))
    } else {
      setSortBy(col)
      setSortDir(col === 'amount' ? 'desc' : 'asc')
    }
  }

  const toggleKind = (kind: TransactionKind) => {
    setSelectedKinds((prev) =>
      prev.includes(kind) ? prev.filter((k) => k !== kind) : [...prev, kind]
    )
  }

  const hasActiveFilters = q || dateFrom || dateTo || selectedKinds.length > 0 || selectedCategory || selectedSubcategory

  const resetFilters = () => {
    setQ('')
    setDateFrom('')
    setDateTo('')
    setSelectedKinds([])
    setSelectedCategory('')
    setSelectedSubcategory('')
  }

  const availableSubcategories = categories.find((c) => c.name === selectedCategory)?.subcategories ?? []

  if (!account && accounts.length > 0) {
    return (
      <div className="p-8">
        <p className="text-sm text-gray-400">Compte introuvable.</p>
        <Link to="/accounts" className="text-sm text-gray-900 font-medium hover:underline mt-2 inline-block">
          ← Retour aux comptes
        </Link>
      </div>
    )
  }

  const balance = balanceData?.balance ?? null
  const balanceNegative = balance !== null && parseFloat(balance) < 0

  return (
    <div className="p-8">
      {/* En-tête */}
      <div className="mb-6">
        <Link to="/accounts" className="text-xs text-gray-400 hover:text-gray-700 transition-colors mb-4 inline-block">
          ← Comptes
        </Link>

        <div className="flex items-start justify-between">
          <div>
            <h1 className="text-2xl font-semibold text-gray-900">{account?.name ?? '…'}</h1>
            <p className="text-sm text-gray-400 mt-0.5">
              {account ? (TYPE_LABELS[account.account_type] ?? account.account_type) : ''}
              {account && ` · ${account.currency}`}
            </p>
            {id && (
              <Link
                to={`/accounts/${id}/analyse`}
                className="inline-flex items-center gap-1 mt-2 text-xs text-gray-400 hover:text-gray-700 transition-colors"
              >
                Voir l'analyse →
              </Link>
            )}
          </div>

          <div className="text-right">
            <p className="text-xs text-gray-400 uppercase tracking-wider mb-1">Solde actuel</p>
            {balance !== null ? (
              <p className={`text-3xl font-semibold tabular-nums ${balanceNegative ? 'text-red-600' : 'text-gray-900'}`}>
                {format(balance, balanceData!.currency)}
              </p>
            ) : (
              <div className="h-9 w-32 bg-gray-100 rounded-lg animate-pulse" />
            )}
          </div>
        </div>
      </div>

      {/* Transactions */}
      <div>
        {/* Titre + bouton */}
        <div className="flex items-center justify-between mb-3">
          <h2 className="text-sm font-medium text-gray-900">
            Transactions
            {transactions.length > 0 && (
              <span className="ml-2 text-xs font-normal text-gray-400">{transactions.length}</span>
            )}
          </h2>
          <div className="flex items-center gap-2">
            <button
              onClick={() => setTransferModal(true)}
              className="flex items-center gap-1.5 px-3 py-1.5 border border-gray-200 text-gray-700 text-xs font-medium rounded-lg hover:bg-gray-50 transition-colors"
            >
              ⇄ Virement
            </button>
            <button
              onClick={() => setModal({ type: 'create' })}
              className="flex items-center gap-1.5 px-3 py-1.5 bg-gray-900 text-white text-xs font-medium rounded-lg hover:bg-gray-800 transition-colors"
            >
              <span className="text-sm leading-none">+</span>
              Nouvelle transaction
            </button>
          </div>
        </div>

        {/* Barre de filtres */}
        <div className="bg-white rounded-xl border border-gray-100 shadow-sm px-4 py-3 mb-3 flex flex-wrap items-center gap-3">
          {/* Recherche */}
          <input
            type="text"
            placeholder="Rechercher…"
            value={q}
            onChange={(e) => setQ(e.target.value)}
            className="px-3 py-1.5 rounded-lg border border-gray-200 text-sm text-gray-900 focus:outline-none focus:ring-2 focus:ring-gray-900 focus:border-transparent transition bg-white w-44"
          />

          {/* Type (toggles) */}
          <div className="flex gap-1">
            {(['EXPENSE', 'INCOME', 'TRANSFER'] as TransactionKind[]).map((k) => {
              const active = selectedKinds.includes(k)
              return (
                <button
                  key={k}
                  onClick={() => toggleKind(k)}
                  className={`px-2.5 py-1 rounded-full text-xs font-medium border transition-colors ${
                    active
                      ? k === 'EXPENSE'
                        ? 'bg-red-50 border-red-200 text-red-700'
                        : k === 'INCOME'
                        ? 'bg-emerald-50 border-emerald-200 text-emerald-700'
                        : 'bg-blue-50 border-blue-200 text-blue-700'
                      : 'border-gray-200 text-gray-400 hover:border-gray-300'
                  }`}
                >
                  {KIND_LABELS[k]}
                </button>
              )
            })}
          </div>

          {/* Catégorie */}
          <select
            value={selectedCategory}
            onChange={(e) => { setSelectedCategory(e.target.value); setSelectedSubcategory('') }}
            className="px-3 py-1.5 rounded-lg border border-gray-200 text-sm text-gray-700 focus:outline-none focus:ring-2 focus:ring-gray-900 focus:border-transparent transition bg-white"
          >
            <option value="">Toutes catégories</option>
            {categories.map((c) => (
              <option key={c.name} value={c.name}>{c.name}</option>
            ))}
          </select>

          {/* Sous-catégorie — visible uniquement si une catégorie est sélectionnée et qu'elle a des sous-catégories */}
          {selectedCategory && availableSubcategories.length > 0 && (
            <select
              value={selectedSubcategory}
              onChange={(e) => setSelectedSubcategory(e.target.value)}
              className="px-3 py-1.5 rounded-lg border border-gray-200 text-sm text-gray-700 focus:outline-none focus:ring-2 focus:ring-gray-900 focus:border-transparent transition bg-white"
            >
              <option value="">Toutes sous-catégories</option>
              {availableSubcategories.map((s) => (
                <option key={s} value={s}>{s}</option>
              ))}
            </select>
          )}

          {/* Dates */}
          <div className="flex items-center gap-1.5 text-sm text-gray-400">
            <span className="text-xs">Du</span>
            <input
              type="date"
              value={dateFrom}
              onChange={(e) => setDateFrom(e.target.value)}
              className="px-2 py-1 rounded-lg border border-gray-200 text-xs text-gray-700 focus:outline-none focus:ring-2 focus:ring-gray-900 focus:border-transparent transition bg-white"
            />
            <span className="text-xs">au</span>
            <input
              type="date"
              value={dateTo}
              onChange={(e) => setDateTo(e.target.value)}
              className="px-2 py-1 rounded-lg border border-gray-200 text-xs text-gray-700 focus:outline-none focus:ring-2 focus:ring-gray-900 focus:border-transparent transition bg-white"
            />
          </div>

          {/* Reset */}
          {hasActiveFilters && (
            <button
              onClick={resetFilters}
              className="ml-auto text-xs text-gray-400 hover:text-gray-700 transition-colors"
            >
              Réinitialiser
            </button>
          )}
        </div>

        {/* Table */}
        {isLoading ? (
          <div className="flex justify-center py-16">
            <div className="w-6 h-6 border-2 border-gray-200 border-t-gray-700 rounded-full animate-spin" />
          </div>
        ) : transactions.length === 0 ? (
          <div className="bg-white rounded-2xl border border-dashed border-gray-200 p-12 text-center">
            <p className="text-sm text-gray-400">
              {hasActiveFilters ? 'Aucun résultat pour ces filtres.' : 'Aucune transaction pour ce compte.'}
            </p>
          </div>
        ) : (
          <div className="bg-white rounded-2xl border border-gray-100 shadow-sm overflow-hidden">
            <table className="w-full">
              <thead>
                <tr className="border-b border-gray-50">
                  {SORTABLE_COLUMNS.map(({ key, label }) => (
                    <th
                      key={key}
                      onClick={() => handleSort(key)}
                      className={`text-xs font-medium text-gray-400 uppercase tracking-wider px-6 py-3 cursor-pointer select-none hover:text-gray-700 transition-colors ${key === 'amount' ? 'text-right' : 'text-left'}`}
                    >
                      {label}
                      {sortBy === key && (
                        <span className="ml-1 text-gray-500">{sortDir === 'asc' ? '↑' : '↓'}</span>
                      )}
                    </th>
                  ))}
                  <th className="px-4 py-3" />
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-50">
                {transactions.map((tx) => (
                  <TransactionRow
                    key={tx.id}
                    tx={tx}
                    onEdit={() => setModal({ type: 'edit', tx })}
                    onDelete={() => deleteTransaction.mutate(tx.id)}
                  />
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {/* Modal transaction */}
      {modal && (
        <TransactionModal
          mode={modal}
          currency={account?.currency ?? 'EUR'}
          categories={categories}
          onClose={() => setModal(null)}
          onSubmit={async (payload) => {
            if (modal.type === 'create') {
              await createTransaction.mutateAsync(payload as CreateTransactionPayload)
            } else {
              await updateTransaction.mutateAsync({ txId: modal.tx.id, payload })
            }
            setModal(null)
          }}
          isLoading={modal.type === 'create' ? createTransaction.isPending : updateTransaction.isPending}
          error={
            modal.type === 'create'
              ? (createTransaction.error?.message ?? null)
              : (updateTransaction.error?.message ?? null)
          }
        />
      )}

      {/* Modal virement */}
      {transferModal && id && (
        <TransferModal
          fromAccountId={id}
          fromCurrency={account?.currency ?? 'EUR'}
          accounts={accounts.filter((a) => a.id !== id)}
          onClose={() => setTransferModal(false)}
          onSubmit={async (payload) => {
            await createTransfer.mutateAsync({ fromAccountId: id, payload })
            setTransferModal(false)
          }}
          isLoading={createTransfer.isPending}
          error={createTransfer.error?.message ?? null}
        />
      )}
    </div>
  )
}

function TransactionRow({
  tx,
  onEdit,
  onDelete,
}: {
  tx: Transaction
  onEdit: () => void
  onDelete: () => void
}) {
  const { format } = useCurrency()
  const [confirmDelete, setConfirmDelete] = useState(false)
  const amount = parseFloat(tx.amount)
  const isNegative = amount < 0

  return (
    <tr className="hover:bg-gray-50/50 group">
      <td className="px-6 py-3.5 text-sm text-gray-500 tabular-nums whitespace-nowrap">
        {formatDate(tx.date)}
      </td>
      <td className="px-6 py-3.5">
        <span className="text-sm text-gray-900">{tx.category}</span>
        {tx.subcategory && (
          <span className="text-xs text-gray-400 ml-1.5">{tx.subcategory}</span>
        )}
      </td>
      <td className="px-6 py-3.5 text-sm text-gray-400 max-w-xs truncate">
        {tx.label ?? '—'}
      </td>
      <td className="px-6 py-3.5">
        <span className={`inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium ${KIND_COLORS[tx.kind] ?? 'bg-gray-100 text-gray-600'}`}>
          {KIND_LABELS[tx.kind] ?? tx.kind}
        </span>
      </td>
      <td className="px-6 py-3.5 text-right">
        <span className={`text-sm font-medium tabular-nums ${isNegative ? 'text-red-600' : 'text-emerald-600'}`}>
          {format(tx.amount, tx.currency)}
        </span>
      </td>
      <td className="px-4 py-3.5 text-right">
        <span className="flex items-center justify-end gap-3 opacity-0 group-hover:opacity-100 transition-opacity">
          <button
            onClick={onEdit}
            className="text-xs text-gray-400 hover:text-gray-700 transition-colors"
          >
            Modifier
          </button>
          {confirmDelete ? (
            <span className="flex items-center gap-1.5">
              <button
                onClick={() => { onDelete(); setConfirmDelete(false) }}
                className="text-xs text-red-600 hover:text-red-700 font-medium"
              >
                Confirmer
              </button>
              <button
                onClick={() => setConfirmDelete(false)}
                className="text-xs text-gray-400 hover:text-gray-600"
              >
                ×
              </button>
            </span>
          ) : (
            <button
              onClick={() => setConfirmDelete(true)}
              className="text-xs text-gray-300 hover:text-red-500 transition-colors"
            >
              Supprimer
            </button>
          )}
        </span>
      </td>
    </tr>
  )
}

interface TransactionModalProps {
  mode: ModalMode
  currency: string
  categories: { name: string; subcategories: string[] }[]
  onClose: () => void
  onSubmit: (payload: Partial<CreateTransactionPayload>) => Promise<void>
  isLoading: boolean
  error: string | null
}

function TransactionModal({ mode, currency, categories, onClose, onSubmit, isLoading, error }: TransactionModalProps) {
  const existing = mode.type === 'edit' ? mode.tx : null
  const { displayCurrency, convertBetween } = useCurrency()

  const [date, setDate] = useState(existing?.date ?? new Date().toISOString().split('T')[0])
  const [kind, setKind] = useState<TransactionKind>(existing?.kind ?? 'EXPENSE')
  const [amount, setAmount] = useState(existing ? Math.abs(parseFloat(existing.amount)).toFixed(2) : '')
  const [inputCurrency, setInputCurrency] = useState(displayCurrency)
  const [category, setCategory] = useState(existing?.category ?? '')
  const [subcategory, setSubcategory] = useState(existing?.subcategory ?? '')
  const [label, setLabel] = useState(existing?.label ?? '')

  const subcategories = categories.find((c) => c.name === category)?.subcategories ?? []

  const handleCategoryChange = (val: string) => {
    setCategory(val)
    setSubcategory('')
  }

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault()
    if (mode.type === 'create') {
      const absAmount = Math.abs(parseFloat(amount))
      if (isNaN(absAmount) || absAmount === 0) return
      const converted = convertBetween(absAmount, inputCurrency, currency)
      const signedAmount = kind === 'EXPENSE' ? `-${converted.toFixed(2)}` : converted.toFixed(2)
      await onSubmit({
        date,
        amount: signedAmount,
        kind,
        category: category.trim(),
        subcategory: subcategory.trim() || undefined,
        label: label.trim() || undefined,
      })
    } else {
      await onSubmit({
        date,
        kind,
        category: category.trim(),
        subcategory: subcategory.trim() || undefined,
        label: label.trim() || undefined,
      })
    }
  }

  const title = mode.type === 'create' ? 'Nouvelle transaction' : 'Modifier la transaction'
  const submitLabel = mode.type === 'create' ? 'Ajouter' : 'Enregistrer'
  const submittingLabel = mode.type === 'create' ? 'Ajout…' : 'Enregistrement…'

  return (
    <div className="fixed inset-0 bg-black/20 backdrop-blur-sm flex items-center justify-center z-50" onClick={onClose}>
      <div className="bg-white rounded-2xl shadow-xl p-8 w-full max-w-md mx-4" onClick={(e) => e.stopPropagation()}>
        <div className="flex items-center justify-between mb-6">
          <h2 className="text-lg font-semibold text-gray-900">{title}</h2>
          <button onClick={onClose} className="text-gray-300 hover:text-gray-500 text-xl leading-none">×</button>
        </div>

        <form onSubmit={handleSubmit} className="space-y-4">
          {/* Type */}
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1.5">Type</label>
            <div className="grid grid-cols-3 gap-2">
              {(['EXPENSE', 'INCOME', 'TRANSFER'] as TransactionKind[]).map((k) => (
                <button
                  key={k}
                  type="button"
                  onClick={() => setKind(k)}
                  className={`py-2 rounded-lg text-xs font-medium border transition-colors ${
                    kind === k
                      ? k === 'EXPENSE'
                        ? 'bg-red-50 border-red-200 text-red-700'
                        : k === 'INCOME'
                        ? 'bg-emerald-50 border-emerald-200 text-emerald-700'
                        : 'bg-blue-50 border-blue-200 text-blue-700'
                      : 'border-gray-200 text-gray-500 hover:border-gray-300'
                  }`}
                >
                  {KIND_LABELS[k]}
                </button>
              ))}
            </div>
          </div>

          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1.5">Date</label>
              <input
                type="date"
                required
                value={date}
                onChange={(e) => setDate(e.target.value)}
                className={inputClass}
              />
            </div>

            {mode.type === 'create' && (
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1.5">Montant</label>
                <CurrencyAmountInput
                  value={amount}
                  onChange={setAmount}
                  inputCurrency={inputCurrency}
                  onCurrencyChange={setInputCurrency}
                  nativeCurrency={currency}
                  required
                  min="0.01"
                  step="0.01"
                  placeholder="0,00"
                  autoFocus
                />
              </div>
            )}
          </div>

          {/* Catégorie */}
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1.5">Catégorie</label>
            <select
              required
              value={category}
              onChange={(e) => handleCategoryChange(e.target.value)}
              className={inputClass}
            >
              <option value="">— Sélectionner —</option>
              {categories.map((c) => (
                <option key={c.name} value={c.name}>{c.name}</option>
              ))}
            </select>
          </div>

          {/* Sous-catégorie */}
          {category && (
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1.5">
                Sous-catégorie <span className="text-gray-400 font-normal">(optionnel)</span>
              </label>
              <select
                value={subcategory}
                onChange={(e) => setSubcategory(e.target.value)}
                className={inputClass}
              >
                <option value="">— Aucune —</option>
                {subcategories.map((s) => (
                  <option key={s} value={s}>{s}</option>
                ))}
              </select>
            </div>
          )}

          {/* Libellé */}
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1.5">
              Libellé <span className="text-gray-400 font-normal">(optionnel)</span>
            </label>
            <input
              type="text"
              placeholder="Ex : Courses du samedi"
              value={label}
              onChange={(e) => setLabel(e.target.value)}
              className={inputClass}
            />
          </div>

          {error && (
            <p className="text-sm text-red-600 bg-red-50 rounded-lg px-3 py-2">{error}</p>
          )}

          <div className="flex gap-3 pt-2">
            <button
              type="button"
              onClick={onClose}
              className="flex-1 py-2.5 px-4 border border-gray-200 text-gray-700 text-sm font-medium rounded-lg hover:bg-gray-50 transition-colors"
            >
              Annuler
            </button>
            <button
              type="submit"
              disabled={isLoading}
              className="flex-1 py-2.5 px-4 bg-gray-900 text-white text-sm font-medium rounded-lg hover:bg-gray-800 disabled:opacity-50 transition-colors"
            >
              {isLoading ? submittingLabel : submitLabel}
            </button>
          </div>
        </form>
      </div>
    </div>
  )
}

const inputClass = 'w-full px-3.5 py-2.5 rounded-lg border border-gray-200 text-sm text-gray-900 focus:outline-none focus:ring-2 focus:ring-gray-900 focus:border-transparent transition bg-white'

interface TransferModalProps {
  fromAccountId: string
  fromCurrency: string
  accounts: { id: string; name: string; currency: string }[]
  onClose: () => void
  onSubmit: (payload: { to_account_id: string; date: string; amount: string; category: string; label?: string }) => Promise<void>
  isLoading: boolean
  error: string | null
}

function TransferModal({ fromCurrency, accounts, onClose, onSubmit, isLoading, error }: TransferModalProps) {
  const sameCurrency = accounts.filter((a) => a.currency === fromCurrency)
  const otherCurrency = accounts.filter((a) => a.currency !== fromCurrency)
  const { displayCurrency, convertBetween } = useCurrency()

  const [toAccountId, setToAccountId] = useState(sameCurrency[0]?.id ?? accounts[0]?.id ?? '')
  const [date, setDate] = useState(new Date().toISOString().split('T')[0])
  const [amount, setAmount] = useState('')
  const [inputCurrency, setInputCurrency] = useState(displayCurrency)
  const [label, setLabel] = useState('')

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault()
    const abs = parseFloat(amount)
    if (isNaN(abs) || abs <= 0) return
    const converted = convertBetween(abs, inputCurrency, fromCurrency)
    await onSubmit({
      to_account_id: toAccountId,
      date,
      amount: converted.toFixed(2),
      category: 'Virement',
      label: label.trim() || undefined,
    })
  }

  return (
    <div className="fixed inset-0 bg-black/20 backdrop-blur-sm flex items-center justify-center z-50" onClick={onClose}>
      <div className="bg-white rounded-2xl shadow-xl p-8 w-full max-w-md mx-4" onClick={(e) => e.stopPropagation()}>
        <div className="flex items-center justify-between mb-6">
          <h2 className="text-lg font-semibold text-gray-900">Nouveau virement</h2>
          <button onClick={onClose} className="text-gray-300 hover:text-gray-500 text-xl leading-none">×</button>
        </div>

        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1.5">Compte destination</label>
            <select
              required
              value={toAccountId}
              onChange={(e) => setToAccountId(e.target.value)}
              className={inputClass}
            >
              {sameCurrency.length > 0 && (
                <optgroup label={`Même devise (${fromCurrency})`}>
                  {sameCurrency.map((a) => (
                    <option key={a.id} value={a.id}>{a.name}</option>
                  ))}
                </optgroup>
              )}
              {otherCurrency.length > 0 && (
                <optgroup label="Autre devise">
                  {otherCurrency.map((a) => (
                    <option key={a.id} value={a.id}>{a.name} ({a.currency})</option>
                  ))}
                </optgroup>
              )}
            </select>
          </div>

          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1.5">Date</label>
              <input
                type="date"
                required
                value={date}
                onChange={(e) => setDate(e.target.value)}
                className={inputClass}
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1.5">Montant</label>
              <CurrencyAmountInput
                value={amount}
                onChange={setAmount}
                inputCurrency={inputCurrency}
                onCurrencyChange={setInputCurrency}
                nativeCurrency={fromCurrency}
                required
                min="0.01"
                step="0.01"
                placeholder="0,00"
                autoFocus
              />
            </div>
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1.5">
              Libellé <span className="text-gray-400 font-normal">(optionnel)</span>
            </label>
            <input
              type="text"
              placeholder="Ex : Alimentation PEA mars"
              value={label}
              onChange={(e) => setLabel(e.target.value)}
              className={inputClass}
            />
          </div>

          {error && (
            <p className="text-sm text-red-600 bg-red-50 rounded-lg px-3 py-2">{error}</p>
          )}

          <div className="flex gap-3 pt-2">
            <button
              type="button"
              onClick={onClose}
              className="flex-1 py-2.5 px-4 border border-gray-200 text-gray-700 text-sm font-medium rounded-lg hover:bg-gray-50 transition-colors"
            >
              Annuler
            </button>
            <button
              type="submit"
              disabled={isLoading}
              className="flex-1 py-2.5 px-4 bg-gray-900 text-white text-sm font-medium rounded-lg hover:bg-gray-800 disabled:opacity-50 transition-colors"
            >
              {isLoading ? 'Enregistrement…' : 'Créer le virement'}
            </button>
          </div>
        </form>
      </div>
    </div>
  )
}
