import { useState } from 'react'
import { useInstruments, useCreateInstrument, useUpdateInstrument, useDeleteInstrument } from '../hooks/usePortfolios'
import type { Instrument, InstrumentKind } from '../lib/portfoliosApi'

// ── Constantes ─────────────────────────────────────────────────────────────────

const KINDS: { key: InstrumentKind; label: string; color: string; desc: string }[] = [
  { key: 'ETF',    label: 'ETF',     color: 'bg-blue-50 text-blue-700',    desc: 'Exchange Traded Fund' },
  { key: 'STOCK',  label: 'Action',  color: 'bg-violet-50 text-violet-700', desc: 'Action en bourse' },
  { key: 'CRYPTO', label: 'Crypto',  color: 'bg-orange-50 text-orange-700', desc: 'Cryptomonnaie' },
  { key: 'OTHER',  label: 'Autre',   color: 'bg-gray-100 text-gray-600',    desc: 'Autre actif' },
]

const CURRENCIES = ['EUR', 'USD', 'BTC', 'ETH', 'USDT', 'GBP', 'CHF']
const KIND_ORDER: InstrumentKind[] = ['ETF', 'STOCK', 'CRYPTO', 'OTHER']

const inputClass =
  'w-full px-3.5 py-2.5 rounded-lg border border-gray-200 text-sm text-gray-900 focus:outline-none focus:ring-2 focus:ring-gray-900 focus:border-transparent transition bg-white'

// ── Ligne éditable ─────────────────────────────────────────────────────────────

function InstrumentRow({
  inst,
  onDelete,
}: {
  inst: Instrument
  onDelete: (sym: string) => void
}) {
  const updateInstrument = useUpdateInstrument()
  const [editing, setEditing] = useState(false)
  const [editName, setEditName] = useState(inst.name)
  const [editKind, setEditKind] = useState<InstrumentKind>(inst.kind as InstrumentKind)
  const [editTicker, setEditTicker] = useState(inst.ticker ?? '')

  const handleSave = async () => {
    await updateInstrument.mutateAsync({
      symbol: inst.symbol,
      payload: { kind: editKind, currency: inst.currency, name: editName.trim(), ticker: editTicker.trim() },
    })
    setEditing(false)
  }

  const handleCancel = () => {
    setEditName(inst.name)
    setEditKind(inst.kind as InstrumentKind)
    setEditTicker(inst.ticker ?? '')
    setEditing(false)
  }

  if (editing) {
    return (
      <div className="inline-flex items-center gap-2 pl-3 pr-2 py-2 bg-white border border-gray-300 rounded-lg shadow-sm">
        <input
          value={editName}
          onChange={(e) => setEditName(e.target.value)}
          onKeyDown={(e) => { if (e.key === 'Enter') handleSave(); if (e.key === 'Escape') handleCancel() }}
          placeholder="Nom d'affichage…"
          className="text-xs border border-gray-200 rounded px-2 py-1 w-48 focus:outline-none focus:ring-1 focus:ring-gray-900"
          autoFocus
        />
        <input
          value={editTicker}
          onChange={(e) => setEditTicker(e.target.value)}
          onKeyDown={(e) => { if (e.key === 'Enter') handleSave(); if (e.key === 'Escape') handleCancel() }}
          placeholder="Ticker Yahoo (ex: PAEEM.PA)"
          title="Ticker Yahoo Finance — ex: PAEEM.PA pour les ETF Euronext, BTC-EUR pour crypto"
          className="text-xs border border-gray-200 rounded px-2 py-1 w-36 focus:outline-none focus:ring-1 focus:ring-blue-500 font-mono"
        />
        <select
          value={editKind}
          onChange={(e) => setEditKind(e.target.value as InstrumentKind)}
          className="text-xs border border-gray-200 rounded px-2 py-1 focus:outline-none"
        >
          {KINDS.map((k) => <option key={k.key} value={k.key}>{k.label}</option>)}
        </select>
        <button
          onClick={handleSave}
          disabled={updateInstrument.isPending}
          className="text-xs text-emerald-600 hover:text-emerald-800 font-medium transition-colors"
        >
          {updateInstrument.isPending ? '…' : '✓'}
        </button>
        <button onClick={handleCancel} className="text-xs text-gray-400 hover:text-gray-600 transition-colors">✕</button>
      </div>
    )
  }

  return (
    <div className="group inline-flex items-center gap-2 pl-3 pr-2 py-1.5 bg-gray-50 border border-gray-100 rounded-lg hover:border-gray-200 transition-colors">
      <div>
        <div className="text-xs font-semibold text-gray-800 leading-tight">
          {inst.name || <span className="text-gray-400 italic">sans nom</span>}
        </div>
        <div className="flex items-center gap-1.5 mt-0.5">
          <span className="text-[10px] text-gray-400 font-mono leading-tight">{inst.symbol}</span>
          {inst.ticker && (
            <span className="text-[10px] font-mono text-blue-500 bg-blue-50 px-1 rounded leading-tight" title="Ticker Yahoo Finance">
              {inst.ticker}
            </span>
          )}
        </div>
      </div>
      <span className="text-[10px] text-gray-400 border-l border-gray-200 pl-2">{inst.currency}</span>
      <button
        onClick={() => setEditing(true)}
        className="text-gray-300 hover:text-gray-600 transition-colors text-xs opacity-0 group-hover:opacity-100"
        title="Modifier"
      >
        ✎
      </button>
      <button
        onClick={() => onDelete(inst.symbol)}
        className="text-gray-300 hover:text-red-500 transition-colors leading-none text-base ml-0.5"
        title={`Supprimer ${inst.symbol}`}
      >
        ×
      </button>
    </div>
  )
}

// ── Page ───────────────────────────────────────────────────────────────────────

export default function InstrumentsPage() {
  const { data: instruments = [], isLoading } = useInstruments()
  const createInstrument = useCreateInstrument()
  const deleteInstrument = useDeleteInstrument()

  const [symbol, setSymbol]     = useState('')
  const [name, setName]         = useState('')
  const [ticker, setTicker]     = useState('')
  const [kind, setKind]         = useState<InstrumentKind>('ETF')
  const [currency, setCurrency] = useState('EUR')
  const [formError, setFormError] = useState('')

  const [expanded, setExpanded] = useState<Set<InstrumentKind>>(new Set(['ETF', 'STOCK', 'CRYPTO']))
  const [confirmDelete, setConfirmDelete] = useState<string | null>(null)

  const toggle = (k: InstrumentKind) =>
    setExpanded((prev) => {
      const next = new Set(prev)
      next.has(k) ? next.delete(k) : next.add(k)
      return next
    })

  const handleAdd = async () => {
    const sym = symbol.trim().toUpperCase()
    if (!sym) { setFormError('Le symbole est requis'); return }
    if (instruments.some((i) => i.symbol === sym)) { setFormError(`"${sym}" existe déjà`); return }
    try {
      await createInstrument.mutateAsync({ symbol: sym, kind, currency, name: name.trim(), ticker: ticker.trim() })
      setSymbol(''); setName(''); setTicker(''); setFormError('')
    } catch {
      setFormError('Erreur lors de la création')
    }
  }

  const handleDelete = async (sym: string) => {
    await deleteInstrument.mutateAsync(sym)
    setConfirmDelete(null)
  }

  const byKind: Record<InstrumentKind, typeof instruments> = { ETF: [], STOCK: [], CRYPTO: [], OTHER: [] }
  for (const inst of instruments) {
    byKind[inst.kind as InstrumentKind]?.push(inst)
  }

  return (
    <div className="p-8">
      <div className="mb-8">
        <h1 className="text-2xl font-semibold text-gray-900">Actifs</h1>
        <p className="text-sm text-gray-400 mt-0.5">Gérez votre catalogue d'instruments financiers</p>
      </div>

      {/* Formulaire d'ajout */}
      <div className="bg-white rounded-xl border border-gray-100 shadow-sm p-5 mb-6">
        <p className="text-sm font-medium text-gray-800 mb-4">Ajouter un actif</p>
        <div className="flex flex-wrap gap-3 items-end">
          <div className="min-w-32">
            <label className="block text-xs font-medium text-gray-500 mb-1.5">Symbole / ISIN</label>
            <input
              value={symbol}
              onChange={(e) => { setSymbol(e.target.value); setFormError('') }}
              onKeyDown={(e) => e.key === 'Enter' && handleAdd()}
              placeholder="CW8, BTC, FR001…"
              className={inputClass}
              autoCapitalize="characters"
            />
          </div>
          <div className="flex-1 min-w-48">
            <label className="block text-xs font-medium text-gray-500 mb-1.5">Nom d'affichage</label>
            <input
              value={name}
              onChange={(e) => setName(e.target.value)}
              placeholder="Amundi PEA World, Bitcoin…"
              className={inputClass}
            />
          </div>
          <div className="min-w-36">
            <label className="block text-xs font-medium text-gray-500 mb-1.5">
              Ticker Yahoo Finance
              <span className="text-gray-400 font-normal ml-1">(optionnel)</span>
            </label>
            <input
              value={ticker}
              onChange={(e) => setTicker(e.target.value)}
              placeholder="PAEEM.PA, BTC-EUR…"
              className={inputClass + ' font-mono'}
              title="Ticker Yahoo Finance pour la récupération automatique des prix. Ex: PAEEM.PA, WPEA.PA, BTC-EUR"
            />
          </div>
          <div className="min-w-36">
            <label className="block text-xs font-medium text-gray-500 mb-1.5">Type</label>
            <select value={kind} onChange={(e) => setKind(e.target.value as InstrumentKind)} className={inputClass}>
              {KINDS.map((k) => <option key={k.key} value={k.key}>{k.label} — {k.desc}</option>)}
            </select>
          </div>
          <div className="min-w-24">
            <label className="block text-xs font-medium text-gray-500 mb-1.5">Devise</label>
            <select value={currency} onChange={(e) => setCurrency(e.target.value)} className={inputClass}>
              {CURRENCIES.map((c) => <option key={c} value={c}>{c}</option>)}
            </select>
          </div>
          <button
            onClick={handleAdd}
            disabled={!symbol.trim() || createInstrument.isPending}
            className="px-5 py-2.5 bg-gray-900 text-white text-sm font-medium rounded-lg hover:bg-gray-800 disabled:opacity-40 transition-colors whitespace-nowrap"
          >
            {createInstrument.isPending ? 'Ajout…' : 'Ajouter'}
          </button>
        </div>
        {formError && <p className="text-xs text-red-600 mt-2">{formError}</p>}
      </div>

      {/* Liste groupée */}
      {isLoading ? (
        <div className="flex justify-center py-16">
          <div className="w-6 h-6 border-2 border-gray-200 border-t-gray-700 rounded-full animate-spin" />
        </div>
      ) : (
        <div className="space-y-2">
          {KIND_ORDER.map((k) => {
            const meta = KINDS.find((m) => m.key === k)!
            const list = byKind[k]
            const isOpen = expanded.has(k)
            return (
              <div key={k} className="bg-white rounded-xl border border-gray-100 shadow-sm overflow-hidden">
                <button
                  className="w-full flex items-center justify-between px-5 py-3.5 hover:bg-gray-50 transition-colors text-left"
                  onClick={() => toggle(k)}
                >
                  <div className="flex items-center gap-3">
                    <span className={`text-[11px] font-semibold px-2 py-0.5 rounded-md ${meta.color}`}>{meta.label}</span>
                    <span className="text-xs text-gray-400">{list.length} actif{list.length !== 1 ? 's' : ''}</span>
                  </div>
                  <span className="text-gray-300 text-xs">{isOpen ? '▲' : '▼'}</span>
                </button>

                {isOpen && (
                  <div className="border-t border-gray-50 px-5 py-4">
                    {list.length === 0 ? (
                      <p className="text-xs text-gray-400">Aucun actif. Utilisez le formulaire ci-dessus pour en ajouter.</p>
                    ) : (
                      <div className="flex flex-wrap gap-2">
                        {list.map((inst) => (
                          <InstrumentRow key={inst.symbol} inst={inst} onDelete={setConfirmDelete} />
                        ))}
                      </div>
                    )}
                  </div>
                )}
              </div>
            )
          })}
        </div>
      )}

      {/* Confirm delete */}
      {confirmDelete && (
        <div className="fixed inset-0 bg-black/20 backdrop-blur-sm z-50 flex items-center justify-center p-4">
          <div className="bg-white rounded-2xl shadow-2xl w-full max-w-sm p-6">
            <p className="text-sm font-medium text-gray-900 mb-2">Supprimer « {confirmDelete} » ?</p>
            <p className="text-xs text-gray-500 mb-5">Cet actif sera retiré du catalogue. Les trades existants ne seront pas supprimés.</p>
            <div className="flex justify-end gap-2">
              <button onClick={() => setConfirmDelete(null)} className="px-4 py-2 text-sm text-gray-600 hover:text-gray-900 transition-colors">Annuler</button>
              <button
                onClick={() => handleDelete(confirmDelete)}
                disabled={deleteInstrument.isPending}
                className="px-4 py-2 bg-red-600 text-white text-sm font-medium rounded-lg hover:bg-red-700 disabled:opacity-60 transition-colors"
              >
                {deleteInstrument.isPending ? 'Suppression…' : 'Supprimer'}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
