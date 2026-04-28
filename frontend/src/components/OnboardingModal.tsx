import { type FormEvent, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { useCreateAccount } from '../hooks/useAccounts'
import { useCurrency } from '../context/CurrencyContext'
import { CurrencyAmountInput } from './CurrencyAmountInput'

const ACCOUNT_TYPES = ['CHECKING', 'SAVINGS', 'INVESTMENT', 'OTHER'] as const
const ACCOUNT_TYPE_LABELS: Record<string, string> = {
  CHECKING: 'Courant',
  SAVINGS: 'Épargne',
  INVESTMENT: 'Investissement',
  OTHER: 'Autre',
}
const CURRENCIES = ['EUR', 'USD', 'CHF', 'GBP']

interface Props {
  onClose: () => void
}

type Step = 'welcome' | 'account' | 'next'

export default function OnboardingModal({ onClose }: Props) {
  const navigate = useNavigate()
  const [step, setStep] = useState<Step>('welcome')

  // Account form state
  const createAccount = useCreateAccount()
  const { displayCurrency, convertBetween } = useCurrency()
  const [name, setName] = useState('')
  const [currency, setCurrency] = useState('EUR')
  const [openingBalance, setOpeningBalance] = useState('0')
  const [inputCurrency, setInputCurrency] = useState(displayCurrency)
  const [openedOn, setOpenedOn] = useState(new Date().toISOString().split('T')[0])
  const [accountType, setAccountType] = useState('CHECKING')
  const [error, setError] = useState<string | null>(null)
  const [accountCreated, setAccountCreated] = useState(false)

  const handleCreateAccount = async (e: FormEvent) => {
    e.preventDefault()
    setError(null)
    const raw = parseFloat(openingBalance) || 0
    const native = convertBetween(raw, inputCurrency, currency)
    try {
      await createAccount.mutateAsync({
        id: crypto.randomUUID(),
        name: name.trim(),
        currency,
        opening_balance: native.toFixed(2),
        opened_on: openedOn,
        account_type: accountType,
      })
      setAccountCreated(true)
      setStep('next')
    } catch (err: unknown) {
      const detail = (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail
      setError(typeof detail === 'string' ? detail : 'Erreur lors de la création du compte.')
    }
  }

  const handleFinish = () => {
    localStorage.removeItem('dashmoney_onboarding')
    onClose()
  }

  const handleGoImport = () => {
    localStorage.removeItem('dashmoney_onboarding')
    onClose()
    navigate('/import')
  }

  const handleGoAccounts = () => {
    localStorage.removeItem('dashmoney_onboarding')
    onClose()
    navigate('/accounts')
  }

  const inputClass = 'w-full px-3.5 py-2.5 rounded-lg border border-gray-200 text-sm text-gray-900 focus:outline-none focus:ring-2 focus:ring-gray-900 focus:border-transparent transition bg-white'

  return (
    <div className="fixed inset-0 bg-black/30 backdrop-blur-sm flex items-center justify-center z-50">
      <div
        className="bg-white dark:bg-slate-800 rounded-2xl shadow-2xl w-full max-w-lg mx-4 overflow-hidden"
        onClick={(e) => e.stopPropagation()}
      >
        {/* Progress bar */}
        <div className="h-1 bg-gray-100 dark:bg-slate-700">
          <div
            className="h-full bg-gray-900 dark:bg-slate-200 transition-all duration-500 ease-out"
            style={{ width: step === 'welcome' ? '33%' : step === 'account' ? '66%' : '100%' }}
          />
        </div>

        <div className="p-8">
          {/* ── Step 1: Welcome ── */}
          {step === 'welcome' && (
            <div className="text-center">
              <div className="w-16 h-16 mx-auto mb-6 rounded-2xl bg-gray-900 dark:bg-slate-200 flex items-center justify-center">
                <svg width="32" height="32" viewBox="0 0 24 24" fill="none" stroke="white" className="dark:stroke-slate-800" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
                  <path d="M12 2L2 7l10 5 10-5-10-5z" />
                  <path d="M2 17l10 5 10-5" />
                  <path d="M2 12l10 5 10-5" />
                </svg>
              </div>
              <h2 className="text-xl font-semibold text-gray-900 dark:text-slate-100 mb-2">
                Bienvenue sur DashMoney
              </h2>
              <p className="text-sm text-gray-500 dark:text-slate-400 leading-relaxed max-w-sm mx-auto">
                Votre espace patrimonial est prêt. En quelques minutes, vous aurez une vue
                complète de vos finances.
              </p>

              <div className="mt-8 space-y-3 text-left max-w-xs mx-auto">
                <StepPreview number={1} label="Créez votre premier compte" active />
                <StepPreview number={2} label="Importez vos transactions" />
                <StepPreview number={3} label="Explorez votre dashboard" />
              </div>

              <button
                onClick={() => setStep('account')}
                className="mt-8 w-full py-3 px-4 bg-gray-900 dark:bg-slate-200 text-white dark:text-slate-900 text-sm font-medium rounded-xl hover:bg-gray-800 dark:hover:bg-slate-300 transition-colors"
              >
                C'est parti
              </button>
              <button
                onClick={handleFinish}
                className="mt-3 text-xs text-gray-400 hover:text-gray-600 dark:hover:text-slate-300 transition-colors"
              >
                Je connais déjà, passer
              </button>
            </div>
          )}

          {/* ── Step 2: Create Account ── */}
          {step === 'account' && (
            <div>
              <button
                onClick={() => setStep('welcome')}
                className="text-xs text-gray-400 hover:text-gray-600 dark:hover:text-slate-300 mb-4 flex items-center gap-1 transition-colors"
              >
                ← Retour
              </button>
              <h2 className="text-lg font-semibold text-gray-900 dark:text-slate-100 mb-1">
                Créez votre premier compte
              </h2>
              <p className="text-sm text-gray-500 dark:text-slate-400 mb-6">
                Compte courant, épargne, investissement… commencez par celui que vous utilisez le plus.
              </p>

              <form onSubmit={handleCreateAccount} className="space-y-4">
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
                  <p className="text-sm text-red-600 bg-red-50 dark:bg-red-900/20 rounded-lg px-3 py-2">{error}</p>
                )}

                <button
                  type="submit"
                  disabled={createAccount.isPending}
                  className="w-full py-3 px-4 bg-gray-900 dark:bg-slate-200 text-white dark:text-slate-900 text-sm font-medium rounded-xl hover:bg-gray-800 dark:hover:bg-slate-300 disabled:opacity-50 transition-colors"
                >
                  {createAccount.isPending ? 'Création…' : 'Créer le compte'}
                </button>

                <button
                  type="button"
                  onClick={() => setStep('next')}
                  className="w-full text-xs text-gray-400 hover:text-gray-600 dark:hover:text-slate-300 transition-colors py-1"
                >
                  Passer cette étape
                </button>
              </form>
            </div>
          )}

          {/* ── Step 3: Next Steps ── */}
          {step === 'next' && (
            <div className="text-center">
              {accountCreated ? (
                <>
                  <div className="w-16 h-16 mx-auto mb-6 rounded-full bg-emerald-50 dark:bg-emerald-900/30 flex items-center justify-center">
                    <svg width="32" height="32" viewBox="0 0 24 24" fill="none" stroke="#10b981" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                      <path d="M20 6L9 17l-5-5" />
                    </svg>
                  </div>
                  <h2 className="text-lg font-semibold text-gray-900 dark:text-slate-100 mb-2">
                    Compte créé avec succès !
                  </h2>
                </>
              ) : (
                <>
                  <div className="w-16 h-16 mx-auto mb-6 rounded-2xl bg-gray-100 dark:bg-slate-700 flex items-center justify-center">
                    <svg width="28" height="28" viewBox="0 0 24 24" fill="none" stroke="#6b7280" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
                      <path d="M13 2H6a2 2 0 00-2 2v16a2 2 0 002 2h12a2 2 0 002-2V9z" />
                      <polyline points="13 2 13 9 20 9" />
                    </svg>
                  </div>
                  <h2 className="text-lg font-semibold text-gray-900 dark:text-slate-100 mb-2">
                    Et maintenant ?
                  </h2>
                </>
              )}

              <p className="text-sm text-gray-500 dark:text-slate-400 leading-relaxed max-w-sm mx-auto mb-8">
                Pour alimenter votre dashboard, importez vos relevés bancaires ou ajoutez
                vos transactions manuellement.
              </p>

              <div className="space-y-3">
                <button
                  onClick={handleGoImport}
                  className="w-full py-3 px-4 bg-gray-900 dark:bg-slate-200 text-white dark:text-slate-900 text-sm font-medium rounded-xl hover:bg-gray-800 dark:hover:bg-slate-300 transition-colors flex items-center justify-center gap-2"
                >
                  <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                    <path d="M21 15v4a2 2 0 01-2 2H5a2 2 0 01-2-2v-4" />
                    <polyline points="7 10 12 15 17 10" />
                    <line x1="12" y1="15" x2="12" y2="3" />
                  </svg>
                  Importer un relevé CSV
                </button>

                {!accountCreated && (
                  <button
                    onClick={handleGoAccounts}
                    className="w-full py-3 px-4 border border-gray-200 dark:border-slate-600 text-gray-700 dark:text-slate-300 text-sm font-medium rounded-xl hover:bg-gray-50 dark:hover:bg-slate-700 transition-colors"
                  >
                    Créer un compte manuellement
                  </button>
                )}

                <button
                  onClick={handleFinish}
                  className="w-full py-2 text-xs text-gray-400 hover:text-gray-600 dark:hover:text-slate-300 transition-colors"
                >
                  Explorer le dashboard
                </button>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  )
}

// ── Helpers ────────────────────────────────────────────────────────────────────

function StepPreview({ number, label, active }: { number: number; label: string; active?: boolean }) {
  return (
    <div className="flex items-center gap-3">
      <div className={`w-7 h-7 rounded-full flex items-center justify-center text-xs font-semibold flex-shrink-0 ${
        active
          ? 'bg-gray-900 dark:bg-slate-200 text-white dark:text-slate-900'
          : 'bg-gray-100 dark:bg-slate-700 text-gray-400 dark:text-slate-500'
      }`}>
        {number}
      </div>
      <span className={`text-sm ${active ? 'text-gray-900 dark:text-slate-100 font-medium' : 'text-gray-400 dark:text-slate-500'}`}>
        {label}
      </span>
    </div>
  )
}

function Field({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div>
      <label className="block text-sm font-medium text-gray-700 dark:text-slate-300 mb-1.5">{label}</label>
      {children}
    </div>
  )
}
