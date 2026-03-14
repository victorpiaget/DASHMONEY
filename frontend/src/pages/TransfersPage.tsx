import { useCallback, useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { useAccounts } from '../hooks/useAccounts'
import { usePortfolios, usePositions } from '../hooks/usePortfolios'
import {
  useTransfers,
  useCreateTransfer,
  useUpdateTransfer,
  useDeleteTransfer,
  useLinkAsTransfer,
  usePromoteToTransfer,
} from '../hooks/useTransfers'
import { transactionsApi, type Transaction } from '../lib/transactionsApi'
import type { Account } from '../lib/accountsApi'
import type { Transfer, AssetTransferRecord } from '../lib/transfersApi'
import { assetTransfersApi } from '../lib/transfersApi'
import type { Portfolio as PortfolioObj, Position } from '../lib/portfoliosApi'

// ── Helpers ────────────────────────────────────────────────────────────────────

const inputClass =
  'w-full px-3.5 py-2.5 rounded-lg border border-gray-200 text-sm text-gray-900 focus:outline-none focus:ring-2 focus:ring-gray-900 focus:border-transparent transition bg-white'

function today() { return new Date().toISOString().slice(0, 10) }

function fmt(amount: string, currency: string) {
  return new Intl.NumberFormat('fr-FR', { style: 'currency', currency, minimumFractionDigits: 2, maximumFractionDigits: 2 }).format(Math.abs(parseFloat(amount)))
}
function fmtDate(d: string) {
  return new Date(d + 'T00:00:00').toLocaleDateString('fr-FR', { day: 'numeric', month: 'short', year: 'numeric' })
}
function absAmt(amount: string) { return String(Math.abs(parseFloat(amount))) }

// ── Hook : dismissed persisté en localStorage ──────────────────────────────────

function useDismissed(storageKey: string) {
  const [dismissed, setDismissed] = useState<Set<string>>(() => {
    try {
      const saved = localStorage.getItem(storageKey)
      return saved ? new Set<string>(JSON.parse(saved)) : new Set<string>()
    } catch {
      return new Set<string>()
    }
  })

  const dismiss = useCallback(
    (key: string) => {
      setDismissed((prev) => {
        const next = new Set([...prev, key])
        try { localStorage.setItem(storageKey, JSON.stringify([...next])) } catch { /* noop */ }
        return next
      })
    },
    [storageKey],
  )

  return { dismissed, dismiss }
}

// ── Types pour la détection ────────────────────────────────────────────────────

interface TxWithAccount { tx: Transaction; account: Account }

interface DetectedPair {
  expense: TxWithAccount
  income: TxWithAccount
}

interface DetectedSingle extends TxWithAccount {}

// ── Algorithme de pair matching ────────────────────────────────────────────────

function detectTransfers(allTxs: TxWithAccount[]): { pairs: DetectedPair[]; singles: DetectedSingle[] } {
  const candidates = allTxs.filter((x) => x.tx.transfer_id === null && x.tx.kind !== 'TRANSFER')

  const byKey = new Map<string, TxWithAccount[]>()
  for (const item of candidates) {
    const cents = Math.round(Math.abs(parseFloat(item.tx.amount)) * 100)
    const key = `${cents}_${item.tx.date}`
    const group = byKey.get(key) ?? []
    group.push(item)
    byKey.set(key, group)
  }

  const pairs: DetectedPair[] = []
  const pairedTxIds = new Set<string>()

  for (const group of byKey.values()) {
    const expenses = group.filter((x) => parseFloat(x.tx.amount) < 0)
    const incomes = group.filter((x) => parseFloat(x.tx.amount) > 0)

    for (const expense of expenses) {
      for (const income of incomes) {
        if (
          expense.account.id !== income.account.id &&
          !pairedTxIds.has(expense.tx.id) &&
          !pairedTxIds.has(income.tx.id)
        ) {
          pairs.push({ expense, income })
          pairedTxIds.add(expense.tx.id)
          pairedTxIds.add(income.tx.id)
          break
        }
      }
    }
  }

  const SINGLE_CATEGORIES = new Set(['VIREMENT', 'EPARGNE', 'LIVRET', 'PLACEMENT', 'TRANSFER'])
  const SINGLE_KEYWORDS = ['virement', 'transfert', 'livret', 'epargn', 'pea ', 'cto ']

  const singles: DetectedSingle[] = candidates.filter((x) => {
    if (pairedTxIds.has(x.tx.id)) return false
    if (x.account.account_type === 'INVESTMENT') return false
    const cat = x.tx.category.toUpperCase()
    if (SINGLE_CATEGORIES.has(cat)) return true
    const label = (x.tx.label ?? '').toLowerCase()
    return SINGLE_KEYWORDS.some((kw) => label.includes(kw))
  })

  return { pairs, singles }
}

// ── Hook : charger toutes les transactions ─────────────────────────────────────

function useAllCandidates(accounts: Account[]) {
  return useQuery({
    queryKey: ['all-tx-for-detection', accounts.map((a) => a.id).sort().join(',')],
    queryFn: async () => {
      const results = await Promise.all(accounts.map((a) => transactionsApi.list(a.id)))
      return accounts.flatMap((acc, i) => results[i].map((tx) => ({ tx, account: acc })))
    },
    enabled: accounts.length > 0,
    staleTime: 10_000,
  })
}

// ── Ligne paire détectée ───────────────────────────────────────────────────────

function PairRow({ pair, onLinked, onDismiss }: { pair: DetectedPair; onLinked: () => void; onDismiss: () => void }) {
  const link = useLinkAsTransfer()
  const [error, setError] = useState('')

  const handleLink = async () => {
    setError('')
    try {
      await link.mutateAsync({ fromTxId: pair.expense.tx.id, toTxId: pair.income.tx.id })
      onLinked()
    } catch (e: unknown) {
      const msg = (e as { response?: { data?: { detail?: string } } })?.response?.data?.detail
      setError(msg ?? 'Erreur')
    }
  }

  return (
    <div className="flex items-center gap-3 py-2.5 px-4 hover:bg-amber-50/60 rounded-lg transition-colors group">
      <div className="flex-1 min-w-0">
        <div className="flex items-center gap-2 flex-wrap">
          <span className="text-xs text-gray-400 shrink-0">{fmtDate(pair.expense.tx.date)}</span>
          <span className="text-sm font-semibold text-gray-900">{fmt(pair.expense.tx.amount, pair.expense.account.currency)}</span>
        </div>
        <div className="flex items-center gap-1.5 mt-0.5 text-xs text-gray-600">
          <span className="font-medium">{pair.expense.account.name}</span>
          <span className="text-gray-300">→</span>
          <span className="font-medium">{pair.income.account.name}</span>
          {pair.expense.tx.label && <span className="text-gray-400 truncate max-w-40">· {pair.expense.tx.label}</span>}
        </div>
      </div>
      <div className="flex items-center gap-2 shrink-0">
        <span className="text-[10px] text-emerald-600 bg-emerald-50 px-2 py-0.5 rounded-full">2 côtés trouvés</span>
        <button
          onClick={handleLink}
          disabled={link.isPending}
          className="px-3 py-1.5 bg-emerald-600 text-white text-xs font-medium rounded-lg hover:bg-emerald-700 disabled:opacity-40 transition-colors"
        >
          {link.isPending ? '…' : 'Lier'}
        </button>
        <button
          onClick={onDismiss}
          title="Ignorer cette suggestion"
          className="text-gray-300 hover:text-gray-500 text-base leading-none px-1 opacity-0 group-hover:opacity-100 transition-opacity"
        >
          ×
        </button>
        {error && <p className="text-xs text-red-500">{error}</p>}
      </div>
    </div>
  )
}

// ── Ligne candidat simple ──────────────────────────────────────────────────────

function SingleRow({ item, accounts, onPromoted, onDismiss }: { item: DetectedSingle; accounts: Account[]; onPromoted: () => void; onDismiss: () => void }) {
  const promote = usePromoteToTransfer()
  const [destId, setDestId] = useState('')
  const [error, setError] = useState('')
  const eligible = accounts.filter((a) => a.id !== item.account.id && a.currency === item.account.currency)

  const handlePromote = async () => {
    if (!destId) { setError('Choisissez un compte destination'); return }
    setError('')
    try {
      await promote.mutateAsync({
        fromAccountId: item.account.id,
        txId: item.tx.id,
        toAccountId: destId,
        date: item.tx.date,
        amount: absAmt(item.tx.amount),
        label: item.tx.label ?? undefined,
      })
      onPromoted()
    } catch (e: unknown) {
      const msg = (e as { response?: { data?: { detail?: string } } })?.response?.data?.detail
      setError(msg ?? 'Erreur')
    }
  }

  return (
    <div className="flex items-center gap-3 py-2.5 px-4 hover:bg-amber-50/60 rounded-lg transition-colors group">
      <div className="flex-1 min-w-0">
        <div className="flex items-center gap-2">
          <span className="text-xs text-gray-400 shrink-0">{fmtDate(item.tx.date)}</span>
          <span className="text-sm font-semibold text-gray-900">{fmt(item.tx.amount, item.account.currency)}</span>
          <span className="text-xs font-medium text-gray-700">{item.account.name}</span>
          {item.tx.label && <span className="text-xs text-gray-400 truncate max-w-40">{item.tx.label}</span>}
          <span className="text-[10px] px-1.5 py-0.5 bg-amber-100 text-amber-600 rounded shrink-0">{item.tx.category}</span>
        </div>
      </div>
      <div className="flex items-center gap-2 shrink-0">
        <span className="text-gray-300 text-xs">→</span>
        <select value={destId} onChange={(e) => { setDestId(e.target.value); setError('') }}
          className="text-xs border border-gray-200 rounded-lg px-2 py-1.5 focus:outline-none bg-white">
          <option value="">Compte…</option>
          {eligible.map((a) => <option key={a.id} value={a.id}>{a.name}</option>)}
        </select>
        <button onClick={handlePromote} disabled={!destId || promote.isPending}
          className="px-3 py-1.5 bg-gray-900 text-white text-xs font-medium rounded-lg hover:bg-gray-800 disabled:opacity-40 transition-colors">
          {promote.isPending ? '…' : 'Créer'}
        </button>
        <button
          onClick={onDismiss}
          title="Ignorer cette suggestion"
          className="text-gray-300 hover:text-gray-500 text-base leading-none px-1 opacity-0 group-hover:opacity-100 transition-opacity"
        >
          ×
        </button>
        {error && <p className="text-xs text-red-500">{error}</p>}
      </div>
    </div>
  )
}

// ── Ligne virement existant ────────────────────────────────────────────────────

function TransferRow({ transfer, onDelete }: { transfer: Transfer; onDelete: (t: Transfer) => void }) {
  const updateTransfer = useUpdateTransfer()
  const [editing, setEditing] = useState(false)
  const [editDate, setEditDate] = useState(transfer.date)
  const [editAmount, setEditAmount] = useState(transfer.amount)
  const [editLabel, setEditLabel] = useState(transfer.label ?? '')

  const handleSave = async () => {
    await updateTransfer.mutateAsync({
      fromAccountId: transfer.from_account_id,
      transferId: transfer.transfer_id,
      payload: {
        date: editDate !== transfer.date ? editDate : undefined,
        amount: editAmount !== transfer.amount ? editAmount : undefined,
        label: editLabel || undefined,
      },
    })
    setEditing(false)
  }

  const cancelEdit = () => {
    setEditing(false); setEditDate(transfer.date); setEditAmount(transfer.amount); setEditLabel(transfer.label ?? '')
  }

  if (editing) {
    return (
      <div className="flex items-center gap-2 py-2.5 px-4 bg-gray-50 rounded-lg">
        <input type="date" value={editDate} onChange={(e) => setEditDate(e.target.value)}
          className="text-xs border border-gray-200 rounded px-2 py-1.5 focus:outline-none" />
        <input type="text" value={editAmount} onChange={(e) => setEditAmount(e.target.value)}
          className="w-24 text-xs border border-gray-200 rounded px-2 py-1.5 focus:outline-none" placeholder="Montant" />
        <input type="text" value={editLabel} onChange={(e) => setEditLabel(e.target.value)}
          className="flex-1 text-xs border border-gray-200 rounded px-2 py-1.5 focus:outline-none" placeholder="Libellé" />
        <button onClick={handleSave} disabled={updateTransfer.isPending} className="text-xs text-emerald-600 font-medium hover:text-emerald-800">
          {updateTransfer.isPending ? '…' : '✓'}
        </button>
        <button onClick={cancelEdit} className="text-xs text-gray-400 hover:text-gray-600">✕</button>
      </div>
    )
  }

  return (
    <div className="group flex items-center gap-3 py-2.5 px-4 hover:bg-gray-50 rounded-lg transition-colors">
      <span className="text-xs text-gray-400 w-28 shrink-0">{fmtDate(transfer.date)}</span>
      <div className="flex items-center gap-1.5 flex-1 min-w-0">
        <span className="text-sm font-medium text-gray-800 truncate">{transfer.from_account_name}</span>
        <span className="text-gray-300 text-xs shrink-0">→</span>
        <span className="text-sm font-medium text-gray-800 truncate">{transfer.to_account_name}</span>
      </div>
      <span className="text-sm font-semibold text-gray-900 shrink-0">{fmt(transfer.amount, transfer.currency)}</span>
      {transfer.label && <span className="text-xs text-gray-400 truncate max-w-36 hidden sm:block">{transfer.label}</span>}
      <div className="flex items-center gap-1 opacity-0 group-hover:opacity-100 transition-opacity shrink-0">
        <button onClick={() => setEditing(true)} className="text-xs text-gray-400 hover:text-gray-700 px-1.5 py-1" title="Modifier">✎</button>
        <button onClick={() => onDelete(transfer)} className="text-xs text-gray-300 hover:text-red-500 px-1.5 py-1" title="Supprimer">×</button>
      </div>
    </div>
  )
}

// ── Row historique transfert d'actifs ──────────────────────────────────────────

function AssetTransferHistoryRow({
  record,
  onDelete,
}: {
  record: AssetTransferRecord
  onDelete: (id: string) => void
}) {
  const [confirm, setConfirm] = useState(false)
  const qty = parseFloat(record.quantity)
  const fees = parseFloat(record.fees)

  return (
    <div className="group flex items-center gap-3 py-2.5 px-4 hover:bg-gray-50 rounded-lg transition-colors">
      <span className="text-xs text-gray-400 w-28 shrink-0">{fmtDate(record.date)}</span>
      <div className="flex items-center gap-1.5 flex-1 min-w-0">
        <span className="text-sm font-medium text-gray-800 truncate">{record.from_portfolio_name}</span>
        <span className="text-gray-300 text-xs shrink-0">→</span>
        <span className="text-sm font-medium text-gray-800 truncate">{record.to_portfolio_name}</span>
      </div>
      <span className="text-xs font-medium text-gray-700 shrink-0">{record.instrument_symbol}</span>
      <span className="text-sm font-semibold text-gray-900 shrink-0 tabular-nums">
        {qty.toFixed(8).replace(/\.?0+$/, '')}
      </span>
      {fees > 0 && (
        <span className="text-xs text-gray-400 shrink-0">
          frais {fees.toFixed(8).replace(/\.?0+$/, '')}
        </span>
      )}
      <div className="flex items-center gap-1 opacity-0 group-hover:opacity-100 transition-opacity shrink-0">
        {confirm ? (
          <>
            <button
              onClick={() => { onDelete(record.sell_trade_id); setConfirm(false) }}
              className="text-xs text-red-600 font-medium hover:text-red-700 px-1.5"
            >
              Confirmer
            </button>
            <button onClick={() => setConfirm(false)} className="text-xs text-gray-400 hover:text-gray-600 px-1">✕</button>
          </>
        ) : (
          <button
            onClick={() => setConfirm(true)}
            className="text-xs text-gray-300 hover:text-red-500 px-1.5 py-1"
            title="Supprimer"
          >
            ×
          </button>
        )}
      </div>
    </div>
  )
}

// ── Section transfert d'actifs ─────────────────────────────────────────────────

function AssetTransferSection({ portfolios }: { portfolios: PortfolioObj[] }) {
  const queryClient = useQueryClient()

  const { data: history = [], isLoading: historyLoading } = useQuery({
    queryKey: ['asset-transfers'],
    queryFn: assetTransfersApi.list,
  })

  const deleteMutation = useMutation({
    mutationFn: (sellTradeId: string) => assetTransfersApi.delete(sellTradeId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['asset-transfers'] })
      queryClient.invalidateQueries({ queryKey: ['trades'] })
      queryClient.invalidateQueries({ queryKey: ['positions'] })
    },
  })
  const [fromId, setFromId] = useState('')
  const [toId, setToId] = useState('')
  const [symbol, setSymbol] = useState('')
  const [quantity, setQuantity] = useState('')
  const [fees, setFees] = useState('')
  const [date, setDate] = useState(today())
  const [error, setError] = useState('')

  const { data: positions = [] } = usePositions(fromId)
  const availablePositions = positions.filter((p: Position) => parseFloat(p.quantity) > 0)

  const mutation = useMutation({
    mutationFn: () => assetTransfersApi.create({
      from_portfolio_id: fromId,
      to_portfolio_id: toId,
      instrument_symbol: symbol,
      quantity,
      fees: fees || undefined,
      date,
    }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['trades'] })
      queryClient.invalidateQueries({ queryKey: ['positions'] })
      queryClient.invalidateQueries({ queryKey: ['asset-transfers'] })
      setFromId(''); setToId(''); setSymbol(''); setQuantity(''); setFees(''); setDate(today()); setError('')
    },
    onError: (e: unknown) => {
      const msg = (e as { response?: { data?: { detail?: string } } })?.response?.data?.detail
      setError(msg ?? 'Erreur lors du transfert')
    },
  })

  const handleSubmit = () => {
    if (!fromId || !toId || !symbol || !quantity || !date) {
      setError('Tous les champs sont requis')
      return
    }
    if (fromId === toId) { setError('Les deux portefeuilles doivent être différents'); return }
    setError('')
    mutation.mutate()
  }

  return (
    <>
    <div className="bg-white rounded-xl border border-gray-100 shadow-sm p-5 mb-6">
      <p className="text-sm font-medium text-gray-800 mb-1">Transfert d'actifs entre portefeuilles</p>
      <p className="text-xs text-gray-400 mb-4">Déplace des actifs d'un portefeuille vers un autre sans impact sur le résultat (SELL + BUY au même prix).</p>
      <div className="flex flex-wrap gap-3 items-end">
        <div className="min-w-40">
          <label className="block text-xs font-medium text-gray-500 mb-1.5">Source</label>
          <select value={fromId} onChange={(e) => { setFromId(e.target.value); setSymbol('') }} className={inputClass}>
            <option value="">Portefeuille source…</option>
            {portfolios.map((p) => <option key={p.id} value={p.id}>{p.name}</option>)}
          </select>
        </div>
        <div className="min-w-40">
          <label className="block text-xs font-medium text-gray-500 mb-1.5">Destination</label>
          <select value={toId} onChange={(e) => setToId(e.target.value)} className={inputClass} disabled={!fromId}>
            <option value="">Portefeuille destination…</option>
            {portfolios.filter((p) => p.id !== fromId).map((p) => <option key={p.id} value={p.id}>{p.name}</option>)}
          </select>
        </div>
        <div className="min-w-36">
          <label className="block text-xs font-medium text-gray-500 mb-1.5">Actif</label>
          <select value={symbol} onChange={(e) => setSymbol(e.target.value)} className={inputClass} disabled={!fromId}>
            <option value="">Actif…</option>
            {availablePositions.map((p: Position) => (
              <option key={p.instrument_symbol} value={p.instrument_symbol}>
                {p.instrument_symbol} ({parseFloat(p.quantity).toFixed(8).replace(/\.?0+$/, '')})
              </option>
            ))}
          </select>
        </div>
        <div className="w-32">
          <label className="block text-xs font-medium text-gray-500 mb-1.5">Quantité</label>
          <input type="number" min="0.00000001" step="any" value={quantity} onChange={(e) => setQuantity(e.target.value)}
            placeholder="0.5" className={inputClass} />
        </div>
        <div className="w-36">
          <label className="block text-xs font-medium text-gray-500 mb-1.5">
            Frais réseau <span className="font-normal text-gray-400">(optionnel)</span>
          </label>
          <input type="number" min="0" step="any" value={fees} onChange={(e) => setFees(e.target.value)}
            placeholder="0.0001" className={inputClass} />
        </div>
        <div className="w-36">
          <label className="block text-xs font-medium text-gray-500 mb-1.5">Date</label>
          <input type="date" value={date} onChange={(e) => setDate(e.target.value)} className={inputClass} />
        </div>
        <button onClick={handleSubmit} disabled={mutation.isPending}
          className="px-5 py-2.5 bg-gray-900 text-white text-sm font-medium rounded-lg hover:bg-gray-800 disabled:opacity-40 transition-colors whitespace-nowrap">
          {mutation.isPending ? 'Transfert…' : 'Transférer'}
        </button>
      </div>
      {error && <p className="text-xs text-red-600 mt-2">{error}</p>}
    </div>

    {/* Historique */}
    <div className="bg-white rounded-xl border border-gray-100 shadow-sm overflow-hidden">
      <div className="px-5 py-3 border-b border-gray-50">
        <h2 className="text-sm font-medium text-gray-900">
          Transferts d'actifs enregistrés
          {history.length > 0 && <span className="ml-2 text-xs font-normal text-gray-400">{history.length}</span>}
        </h2>
      </div>
      {historyLoading ? (
        <div className="flex justify-center py-10">
          <div className="w-5 h-5 border-2 border-gray-200 border-t-gray-700 rounded-full animate-spin" />
        </div>
      ) : history.length === 0 ? (
        <div className="px-5 py-10 text-center">
          <p className="text-sm text-gray-400">Aucun transfert d'actifs enregistré</p>
        </div>
      ) : (
        <div className="px-3 py-2 divide-y divide-gray-50">
          {history.map((r) => (
            <AssetTransferHistoryRow
              key={r.sell_trade_id}
              record={r}
              onDelete={(id) => deleteMutation.mutate(id)}
            />
          ))}
        </div>
      )}
    </div>
    </>
  )
}

// ── Tri des virements ──────────────────────────────────────────────────────────

type TransferSortField = 'date' | 'amount' | 'from' | 'to'
type SortDir = 'asc' | 'desc'

const TRANSFER_SORT_COLS: { key: TransferSortField; label: string }[] = [
  { key: 'date', label: 'Date' },
  { key: 'from', label: 'De' },
  { key: 'to', label: 'Vers' },
  { key: 'amount', label: 'Montant' },
]

function sortTransfers(transfers: Transfer[], field: TransferSortField, dir: SortDir): Transfer[] {
  return [...transfers].sort((a, b) => {
    let cmp = 0
    if (field === 'date') cmp = a.date.localeCompare(b.date)
    else if (field === 'amount') cmp = parseFloat(a.amount) - parseFloat(b.amount)
    else if (field === 'from') cmp = a.from_account_name.localeCompare(b.from_account_name)
    else if (field === 'to') cmp = a.to_account_name.localeCompare(b.to_account_name)
    return dir === 'asc' ? cmp : -cmp
  })
}

// ── Page principale ────────────────────────────────────────────────────────────

type ActiveTab = 'cash' | 'assets'

export default function TransfersPage() {
  const { data: accounts = [] } = useAccounts()
  const { data: portfolios = [] } = usePortfolios()
  const { data: transfers = [], isLoading: transfersLoading } = useTransfers()
  const { data: allTxs = [], refetch: refetchCandidates, isLoading: candidatesLoading } = useAllCandidates(accounts)

  const createTransfer = useCreateTransfer()
  const deleteTransfer = useDeleteTransfer()

  const [activeTab, setActiveTab] = useState<ActiveTab>('cash')
  const [showForm, setShowForm] = useState(false)
  const [fromId, setFromId] = useState('')
  const [toId, setToId] = useState('')
  const [amount, setAmount] = useState('')
  const [date, setDate] = useState(today())
  const [label, setLabel] = useState('')
  const [formError, setFormError] = useState('')
  const [confirmDelete, setConfirmDelete] = useState<Transfer | null>(null)
  const [detectOpen, setDetectOpen] = useState(true)

  // Tri
  const [sortField, setSortField] = useState<TransferSortField>('date')
  const [sortDir, setSortDir] = useState<SortDir>('desc')

  const handleSort = (col: TransferSortField) => {
    if (sortField === col) setSortDir((d) => (d === 'asc' ? 'desc' : 'asc'))
    else { setSortField(col); setSortDir(col === 'amount' ? 'desc' : 'asc') }
  }

  const sortedTransfers = sortTransfers(transfers, sortField, sortDir)

  // Suggestions ignorées — persistées en localStorage
  const { dismissed, dismiss } = useDismissed('dashmoney-dismissed-transfers')

  const { pairs: rawPairs, singles: rawSingles } = detectTransfers(allTxs)
  const pairs = rawPairs.filter((p) => !dismissed.has(`${p.expense.tx.id}-${p.income.tx.id}`))
  const singles = rawSingles.filter((s) => !dismissed.has(s.tx.id))
  const totalDetected = pairs.length + singles.length

  const eligibleTo = accounts.filter(
    (a) => a.id !== fromId && (fromId ? a.currency === accounts.find((x) => x.id === fromId)?.currency : true)
  )

  const handleCreate = async () => {
    if (!fromId || !toId || !amount || !date) { setFormError('Tous les champs sont requis'); return }
    const parsed = parseFloat(amount)
    if (isNaN(parsed) || parsed <= 0) { setFormError('Montant invalide'); return }
    setFormError('')
    try {
      await createTransfer.mutateAsync({
        fromAccountId: fromId,
        payload: { to_account_id: toId, date, amount: parsed.toFixed(2), category: 'VIREMENT', label: label || undefined },
      })
      setFromId(''); setToId(''); setAmount(''); setLabel(''); setDate(today()); setShowForm(false)
    } catch (e: unknown) {
      const msg = (e as { response?: { data?: { detail?: string } } })?.response?.data?.detail
      setFormError(msg ?? 'Erreur lors de la création')
    }
  }

  const handleDelete = async (t: Transfer) => {
    await deleteTransfer.mutateAsync({ fromAccountId: t.from_account_id, transferId: t.transfer_id })
    setConfirmDelete(null)
  }

  return (
    <div className="p-8 max-w-3xl">
      {/* Header */}
      <div className="flex items-start justify-between mb-6">
        <div>
          <h1 className="text-2xl font-semibold text-gray-900">Virements</h1>
          <p className="text-sm text-gray-400 mt-0.5">Transferts internes entre vos comptes et portefeuilles</p>
        </div>
        {activeTab === 'cash' && (
          <button
            onClick={() => setShowForm((v) => !v)}
            className="px-4 py-2 bg-gray-900 text-white text-sm font-medium rounded-lg hover:bg-gray-800 transition-colors"
          >
            {showForm ? 'Annuler' : '+ Nouveau virement'}
          </button>
        )}
      </div>

      {/* Tabs */}
      <div className="flex gap-1 p-1 bg-gray-100 rounded-lg mb-6 w-fit">
        {(['cash', 'assets'] as ActiveTab[]).map((tab) => (
          <button
            key={tab}
            onClick={() => setActiveTab(tab)}
            className={`px-4 py-1.5 rounded-md text-sm font-medium transition-colors ${
              activeTab === tab ? 'bg-white text-gray-900 shadow-sm' : 'text-gray-500 hover:text-gray-700'
            }`}
          >
            {tab === 'cash' ? 'Espèces' : 'Actifs (Ledger / Exchange)'}
          </button>
        ))}
      </div>

      {/* ── Onglet Espèces ── */}
      {activeTab === 'cash' && (
        <>
          {/* Formulaire */}
          {showForm && (
            <div className="bg-white rounded-xl border border-gray-100 shadow-sm p-5 mb-6">
              <p className="text-sm font-medium text-gray-800 mb-4">Nouveau virement</p>
              <div className="flex flex-wrap gap-3 items-end">
                <div className="min-w-40">
                  <label className="block text-xs font-medium text-gray-500 mb-1.5">De</label>
                  <select value={fromId} onChange={(e) => { setFromId(e.target.value); setToId('') }} className={inputClass}>
                    <option value="">Compte source…</option>
                    {accounts.map((a) => <option key={a.id} value={a.id}>{a.name}</option>)}
                  </select>
                </div>
                <div className="min-w-40">
                  <label className="block text-xs font-medium text-gray-500 mb-1.5">Vers</label>
                  <select value={toId} onChange={(e) => setToId(e.target.value)} className={inputClass} disabled={!fromId}>
                    <option value="">Compte destination…</option>
                    {eligibleTo.map((a) => <option key={a.id} value={a.id}>{a.name}</option>)}
                  </select>
                </div>
                <div className="w-32">
                  <label className="block text-xs font-medium text-gray-500 mb-1.5">Montant</label>
                  <input type="number" min="0.01" step="0.01" value={amount} onChange={(e) => setAmount(e.target.value)} placeholder="500.00" className={inputClass} />
                </div>
                <div className="w-36">
                  <label className="block text-xs font-medium text-gray-500 mb-1.5">Date</label>
                  <input type="date" value={date} onChange={(e) => setDate(e.target.value)} className={inputClass} />
                </div>
                <div className="flex-1 min-w-40">
                  <label className="block text-xs font-medium text-gray-500 mb-1.5">Libellé (optionnel)</label>
                  <input type="text" value={label} onChange={(e) => setLabel(e.target.value)} placeholder="Alimentation PEA janvier" className={inputClass} />
                </div>
                <button onClick={handleCreate} disabled={createTransfer.isPending}
                  className="px-5 py-2.5 bg-gray-900 text-white text-sm font-medium rounded-lg hover:bg-gray-800 disabled:opacity-40 transition-colors whitespace-nowrap">
                  {createTransfer.isPending ? 'Création…' : 'Créer'}
                </button>
              </div>
              {formError && <p className="text-xs text-red-600 mt-2">{formError}</p>}
            </div>
          )}

          {/* Section détection */}
          {(candidatesLoading || totalDetected > 0) && (
            <div className="bg-amber-50 border border-amber-100 rounded-xl mb-6 overflow-hidden">
              <button
                className="w-full flex items-center justify-between px-5 py-3.5 text-left hover:bg-amber-100/50 transition-colors"
                onClick={() => setDetectOpen((v) => !v)}
              >
                <div className="flex items-center gap-2">
                  {candidatesLoading ? (
                    <span className="text-sm text-amber-700">Analyse en cours…</span>
                  ) : (
                    <>
                      <span className="text-sm font-medium text-amber-900">
                        {pairs.length > 0 && `${pairs.length} paire${pairs.length > 1 ? 's' : ''} à lier`}
                        {pairs.length > 0 && singles.length > 0 && ' · '}
                        {singles.length > 0 && `${singles.length} virement${singles.length > 1 ? 's' : ''} incomplet${singles.length > 1 ? 's' : ''}`}
                      </span>
                      <span className="text-xs text-amber-600 bg-amber-100 px-2 py-0.5 rounded-full">non liés</span>
                    </>
                  )}
                </div>
                <span className="text-amber-400 text-xs">{detectOpen ? '▲' : '▼'}</span>
              </button>

              {detectOpen && !candidatesLoading && (
                <div className="border-t border-amber-100">
                  {pairs.length > 0 && (
                    <>
                      <div className="px-5 py-2.5 bg-emerald-50/50 border-b border-amber-100">
                        <p className="text-xs font-medium text-emerald-700">
                          Paires détectées — les deux côtés existent déjà, il suffit de les lier
                        </p>
                      </div>
                      <div className="space-y-0.5 px-2 py-2">
                        {pairs.map((pair) => (
                          <PairRow
                            key={`${pair.expense.tx.id}-${pair.income.tx.id}`}
                            pair={pair}
                            onLinked={() => refetchCandidates()}
                            onDismiss={() => dismiss(`${pair.expense.tx.id}-${pair.income.tx.id}`)}
                          />
                        ))}
                      </div>
                    </>
                  )}
                  {singles.length > 0 && (
                    <>
                      <div className={`px-5 py-2.5 border-b border-amber-100 ${pairs.length > 0 ? 'bg-amber-50/80' : ''}`}>
                        <p className="text-xs font-medium text-amber-700">
                          Virements incomplets — sélectionnez le compte de destination pour créer la contrepartie manquante
                        </p>
                      </div>
                      <div className="space-y-0.5 px-2 py-2">
                        {singles.map((item) => (
                          <SingleRow
                            key={item.tx.id}
                            item={item}
                            accounts={accounts}
                            onPromoted={() => refetchCandidates()}
                            onDismiss={() => dismiss(item.tx.id)}
                          />
                        ))}
                      </div>
                    </>
                  )}
                </div>
              )}
            </div>
          )}

          {/* Liste virements existants */}
          <div className="bg-white rounded-xl border border-gray-100 shadow-sm overflow-hidden">
            <div className="px-5 py-3 border-b border-gray-50">
              <div className="flex items-center justify-between">
                <h2 className="text-sm font-medium text-gray-900">
                  Virements enregistrés
                  {transfers.length > 0 && <span className="ml-2 text-xs font-normal text-gray-400">{transfers.length}</span>}
                </h2>
                {/* Sort controls */}
                {transfers.length > 1 && (
                  <div className="flex items-center gap-1">
                    {TRANSFER_SORT_COLS.map(({ key, label }) => (
                      <button
                        key={key}
                        onClick={() => handleSort(key)}
                        className={`px-2 py-1 text-xs rounded transition-colors ${
                          sortField === key
                            ? 'text-gray-900 font-medium'
                            : 'text-gray-400 hover:text-gray-600'
                        }`}
                      >
                        {label}
                        {sortField === key && (
                          <span className="ml-0.5">{sortDir === 'asc' ? '↑' : '↓'}</span>
                        )}
                      </button>
                    ))}
                  </div>
                )}
              </div>
            </div>
            {transfersLoading ? (
              <div className="flex justify-center py-12">
                <div className="w-5 h-5 border-2 border-gray-200 border-t-gray-700 rounded-full animate-spin" />
              </div>
            ) : sortedTransfers.length === 0 ? (
              <div className="px-5 py-12 text-center">
                <p className="text-sm text-gray-400">Aucun virement enregistré</p>
                <p className="text-xs text-gray-300 mt-1">Liez les paires détectées ou créez un nouveau virement</p>
              </div>
            ) : (
              <div className="px-3 py-2 divide-y divide-gray-50">
                {sortedTransfers.map((t) => (
                  <TransferRow key={t.transfer_id} transfer={t} onDelete={setConfirmDelete} />
                ))}
              </div>
            )}
          </div>
        </>
      )}

      {/* ── Onglet Actifs ── */}
      {activeTab === 'assets' && (
        <AssetTransferSection portfolios={portfolios} />
      )}

      {/* Confirm delete */}
      {confirmDelete && (
        <div className="fixed inset-0 bg-black/20 backdrop-blur-sm z-50 flex items-center justify-center p-4">
          <div className="bg-white rounded-2xl shadow-2xl w-full max-w-sm p-6">
            <p className="text-sm font-medium text-gray-900 mb-2">Supprimer ce virement ?</p>
            <p className="text-xs text-gray-500 mb-1">{confirmDelete.from_account_name} → {confirmDelete.to_account_name}</p>
            <p className="text-xs text-gray-500 mb-4">{fmt(confirmDelete.amount, confirmDelete.currency)} · {fmtDate(confirmDelete.date)}</p>
            <p className="text-xs text-amber-600 bg-amber-50 rounded-lg px-3 py-2 mb-5">
              Les deux transactions liées seront dissociées et remises en état indépendant.
            </p>
            <div className="flex justify-end gap-2">
              <button onClick={() => setConfirmDelete(null)} className="px-4 py-2 text-sm text-gray-600 hover:text-gray-900 transition-colors">Annuler</button>
              <button onClick={() => handleDelete(confirmDelete)} disabled={deleteTransfer.isPending}
                className="px-4 py-2 bg-red-600 text-white text-sm font-medium rounded-lg hover:bg-red-700 disabled:opacity-60 transition-colors">
                {deleteTransfer.isPending ? 'Suppression…' : 'Supprimer'}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
