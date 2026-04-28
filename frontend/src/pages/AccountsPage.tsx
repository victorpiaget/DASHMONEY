import { type FormEvent, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { useAccountBalance, useAccounts, useCreateAccount, useDeleteAccount } from '../hooks/useAccounts'
import { useCurrency } from '../context/CurrencyContext'
import { CurrencyAmountInput } from '../components/CurrencyAmountInput'
import type { Account } from '../lib/accountsApi'

const ACCOUNT_TYPE_LABELS: Record<string, string> = {
  CHECKING: 'Courant',
  SAVINGS: 'Épargne',
  INVESTMENT: 'Investissement',
  OTHER: 'Autre',
}

const ACCOUNT_TYPE_COLORS: Record<string, string> = {
  CHECKING: 'bg-blue-50 text-blue-700',
  SAVINGS: 'bg-emerald-50 text-emerald-700',
  INVESTMENT: 'bg-violet-50 text-violet-700',
  OTHER: 'bg-gray-100 text-gray-600',
}

const CURRENCIES = ['EUR', 'USD', 'CHF', 'GBP']
const ACCOUNT_TYPES = ['CHECKING', 'SAVINGS', 'INVESTMENT', 'OTHER']

export default function AccountsPage() {
  const { data: accounts = [], isLoading } = useAccounts()
  const createAccount = useCreateAccount()
  const deleteAccount = useDeleteAccount()
  const [showForm, setShowForm] = useState(false)

  return (
    <div className="p-8">
      {/* En-tête */}
      <div className="flex items-center justify-between mb-8">
        <div>
          <h1 className="text-xl font-semibold text-gray-900">Comptes</h1>
          <p className="text-xs text-gray-400 mt-1">{accounts.length} compte{accounts.length !== 1 ? 's' : ''}</p>
        </div>
        <button
          onClick={() => setShowForm(true)}
          className="flex items-center gap-2 px-4 py-2.5 bg-gray-900 text-white text-sm font-medium rounded-xl hover:bg-gray-800 active:scale-[0.98] transition-all"
        >
          <span className="text-base leading-none">+</span>
          Nouveau compte
        </button>
      </div>

      {/* Liste */}
      {isLoading ? (
        <div className="flex justify-center py-16">
          <div className="w-6 h-6 border-2 border-gray-200 border-t-gray-700 rounded-full animate-spin" />
        </div>
      ) : accounts.length === 0 ? (
        <EmptyState onAdd={() => setShowForm(true)} />
      ) : (
        <div className="bg-white rounded-xl border border-gray-100 overflow-hidden">
          <table className="w-full">
            <thead>
              <tr className="border-b border-gray-50 bg-gray-50/50">
                <th className="text-left text-[10px] font-medium text-gray-400 uppercase tracking-wider px-6 py-4">Nom</th>
                <th className="text-left text-[10px] font-medium text-gray-400 uppercase tracking-wider px-6 py-4">Type</th>
                <th className="text-right text-[10px] font-medium text-gray-400 uppercase tracking-wider px-6 py-4">Solde actuel</th>
                <th className="px-4 py-4" />
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-50">
              {accounts.map((account) => (
                <AccountRow
                  key={account.id}
                  account={account}
                  onDelete={() => deleteAccount.mutate(account.id)}
                />
              ))}
            </tbody>
          </table>
        </div>
      )}

      {/* Modal création */}
      {showForm && (
        <CreateAccountModal
          onClose={() => setShowForm(false)}
          onSubmit={async (data) => {
            await createAccount.mutateAsync(data)
            setShowForm(false)
          }}
          isLoading={createAccount.isPending}
          error={createAccount.error?.message ?? null}
        />
      )}
    </div>
  )
}

function AccountRow({ account, onDelete }: { account: Account; onDelete: () => void }) {
  const [confirmDelete, setConfirmDelete] = useState(false)
  const { data: balanceData } = useAccountBalance(account.id)
  const { format } = useCurrency()
  const navigate = useNavigate()

  return (
    <tr
      className="hover:bg-gray-50 group cursor-pointer transition-colors"
      onClick={() => navigate(`/accounts/${account.id}`)}
    >
      <td className="px-6 py-4">
        <span className="text-sm font-medium text-gray-900">{account.name}</span>
      </td>
      <td className="px-6 py-4">
        <span className={`inline-flex items-center px-2.5 py-1 rounded-lg text-xs font-medium ${ACCOUNT_TYPE_COLORS[account.account_type] ?? 'bg-gray-100 text-gray-600'}`}>
          {ACCOUNT_TYPE_LABELS[account.account_type] ?? account.account_type}
        </span>
      </td>
      <td className="px-6 py-4 text-right">
        <span className={`text-sm font-medium tabular-nums ${balanceData && parseFloat(balanceData.balance) < 0 ? 'text-red-600' : 'text-gray-900'}`}>
          {balanceData ? format(balanceData.balance, balanceData.currency) : '—'}
        </span>
      </td>
      <td className="px-4 py-4 text-right" onClick={(e) => e.stopPropagation()}>
        <span className="flex items-center justify-end gap-3 opacity-0 group-hover:opacity-100 transition-opacity">
          {confirmDelete ? (
            <span className="flex items-center gap-2">
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
              className="text-xs text-gray-400 hover:text-red-500 transition-colors"
            >
              Supprimer
            </button>
          )}
        </span>
      </td>
    </tr>
  )
}

function EmptyState({ onAdd }: { onAdd: () => void }) {
  return (
    <div className="bg-white rounded-xl border border-dashed border-gray-200 p-16 text-center">
      <p className="text-gray-400 text-sm mb-4">Aucun compte pour l'instant</p>
      <button
        onClick={onAdd}
        className="text-sm text-gray-900 font-medium hover:text-gray-700 transition-colors"
      >
        Créer votre premier compte
      </button>
    </div>
  )
}

interface ModalProps {
  onClose: () => void
  onSubmit: (data: {
    id: string
    name: string
    currency: string
    opening_balance: string
    opened_on: string
    account_type: string
  }) => Promise<void>
  isLoading: boolean
  error: string | null
}

function CreateAccountModal({ onClose, onSubmit, isLoading, error }: ModalProps) {
  const { displayCurrency, convertBetween } = useCurrency()
  const [name, setName] = useState('')
  const [currency, setCurrency] = useState('EUR')
  const [openingBalance, setOpeningBalance] = useState('0')
  const [inputCurrency, setInputCurrency] = useState(displayCurrency)
  const [openedOn, setOpenedOn] = useState(new Date().toISOString().split('T')[0])
  const [accountType, setAccountType] = useState('CHECKING')

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault()
    const raw = parseFloat(openingBalance) || 0
    const native = convertBetween(raw, inputCurrency, currency)
    await onSubmit({
      id: crypto.randomUUID(),
      name: name.trim(),
      currency,
      opening_balance: native.toFixed(2),
      opened_on: openedOn,
      account_type: accountType,
    })
  }

  return (
    <div className="fixed inset-0 bg-black/20 backdrop-blur-sm flex items-center justify-center z-50" onClick={onClose}>
      <div className="bg-white rounded-2xl shadow-xl p-8 w-full max-w-md mx-4" onClick={(e) => e.stopPropagation()}>
        <div className="flex items-center justify-between mb-8">
          <h2 className="text-lg font-semibold text-gray-900">Nouveau compte</h2>
          <button onClick={onClose} className="text-gray-300 hover:text-gray-500 text-xl leading-none transition-colors">×</button>
        </div>

        <form onSubmit={handleSubmit} className="space-y-5">
          <Field label="Nom du compte">
            <input
              type="text"
              required
              value={name}
              onChange={(e) => setName(e.target.value)}
              placeholder="Ex : Compte courant BNP"
              className={inputClass}
              autoFocus
            />
          </Field>

          <div className="grid grid-cols-2 gap-3">
            <Field label="Type">
              <select value={accountType} onChange={(e) => setAccountType(e.target.value)} className={inputClass}>
                {ACCOUNT_TYPES.map((t) => (
                  <option key={t} value={t}>{ACCOUNT_TYPE_LABELS[t]}</option>
                ))}
              </select>
            </Field>
            <Field label="Devise">
              <select value={currency} onChange={(e) => setCurrency(e.target.value)} className={inputClass}>
                {CURRENCIES.map((c) => <option key={c} value={c}>{c}</option>)}
              </select>
            </Field>
          </div>

          <Field label="Solde d'ouverture">
            <CurrencyAmountInput
              value={openingBalance}
              onChange={setOpeningBalance}
              inputCurrency={inputCurrency}
              onCurrencyChange={setInputCurrency}
              nativeCurrency={currency}
              step="0.01"
              placeholder="0"
            />
          </Field>

          <Field label="Date d'ouverture">
            <input
              type="date"
              required
              value={openedOn}
              onChange={(e) => setOpenedOn(e.target.value)}
              className={inputClass}
            />
          </Field>

          {error && (
            <p className="text-sm text-red-600 bg-red-50 rounded-xl px-3 py-2.5">{error}</p>
          )}

          <div className="flex gap-3 pt-3">
            <button
              type="button"
              onClick={onClose}
              className="flex-1 py-2.5 px-4 border border-gray-200 text-gray-700 text-sm font-medium rounded-xl hover:bg-gray-50 active:scale-[0.98] transition-all"
            >
              Annuler
            </button>
            <button
              type="submit"
              disabled={isLoading}
              className="flex-1 py-2.5 px-4 bg-gray-900 text-white text-sm font-medium rounded-xl hover:bg-gray-800 active:scale-[0.98] disabled:opacity-50 transition-all"
            >
              {isLoading ? 'Création…' : 'Créer'}
            </button>
          </div>
        </form>
      </div>
    </div>
  )
}

const inputClass = 'w-full px-3.5 py-2.5 rounded-xl border border-gray-200 text-sm text-gray-900 focus:outline-none focus:ring-2 focus:ring-gray-900 focus:border-transparent transition bg-white'

function Field({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div>
      <label className="block text-sm font-medium text-gray-700 mb-2">{label}</label>
      {children}
    </div>
  )
}
