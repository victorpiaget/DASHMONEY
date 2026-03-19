import { useState, useRef, useCallback } from 'react'
import { useAccounts, useImportBank } from '../hooks/useAccounts'
import type { BankImportResult } from '../lib/accountsApi'

const SUPPORTED_FORMATS = [
  'Boursorama (compte courant)',
  'BNP Paribas',
  'Crédit Agricole',
  'LCL',
  'CIC / Crédit Mutuel',
  'Société Générale',
  'Format générique (débit/crédit)',
]

export default function ImportPage() {
  const { data: accounts = [], isLoading: accountsLoading } = useAccounts()
  const [accountId, setAccountId] = useState('')
  const [dragOver, setDragOver] = useState(false)
  const [selectedFile, setSelectedFile] = useState<File | null>(null)
  const [result, setResult] = useState<BankImportResult | null>(null)
  const [error, setError] = useState<string | null>(null)
  const fileInputRef = useRef<HTMLInputElement>(null)

  const mutation = useImportBank(accountId)

  const handleFile = useCallback((file: File) => {
    if (!file.name.toLowerCase().endsWith('.csv')) {
      setError('Seuls les fichiers .csv sont acceptés.')
      return
    }
    setSelectedFile(file)
    setResult(null)
    setError(null)
  }, [])

  const onDrop = useCallback(
    (e: React.DragEvent) => {
      e.preventDefault()
      setDragOver(false)
      const file = e.dataTransfer.files[0]
      if (file) handleFile(file)
    },
    [handleFile],
  )

  const onFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0]
    if (file) handleFile(file)
  }

  const handleImport = async () => {
    if (!accountId || !selectedFile) return
    setError(null)
    setResult(null)
    try {
      const res = await mutation.mutateAsync(selectedFile)
      setResult(res)
    } catch (err: unknown) {
      const msg =
        (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail ??
        'Erreur lors de l\'import'
      setError(msg)
    }
  }

  const reset = () => {
    setSelectedFile(null)
    setResult(null)
    setError(null)
    if (fileInputRef.current) fileInputRef.current.value = ''
  }

  const selectedAccount = accounts.find((a) => a.id === accountId)

  return (
    <div className="max-w-2xl mx-auto py-8 px-4 space-y-6">
      <div>
        <h1 className="text-xl font-semibold text-gray-900">Import bancaire</h1>
        <p className="mt-1 text-sm text-gray-500">
          Importez un relevé CSV depuis votre banque. Le format est détecté automatiquement.
        </p>
      </div>

      {/* Formats supportés */}
      <div className="rounded-xl border border-gray-100 bg-white p-4">
        <p className="text-xs font-semibold text-gray-400 uppercase tracking-wider mb-2">Formats reconnus</p>
        <div className="flex flex-wrap gap-1.5">
          {SUPPORTED_FORMATS.map((f) => (
            <span
              key={f}
              className="px-2 py-0.5 rounded-full text-xs bg-gray-50 text-gray-600 border border-gray-100"
            >
              {f}
            </span>
          ))}
        </div>
      </div>

      {/* Sélection du compte */}
      <div className="rounded-xl border border-gray-100 bg-white p-5 space-y-4">
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">
            Compte de destination
          </label>
          {accountsLoading ? (
            <div className="h-9 bg-gray-100 rounded-lg animate-pulse" />
          ) : (
            <select
              value={accountId}
              onChange={(e) => { setAccountId(e.target.value); reset() }}
              className="w-full border border-gray-200 rounded-lg px-3 py-2 text-sm bg-white focus:outline-none focus:ring-2 focus:ring-gray-900"
            >
              <option value="">Sélectionner un compte…</option>
              {accounts.map((a) => (
                <option key={a.id} value={a.id}>
                  {a.name} ({a.currency})
                </option>
              ))}
            </select>
          )}
        </div>

        {/* Zone de dépôt */}
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">
            Fichier CSV
          </label>
          <div
            onDragOver={(e) => { e.preventDefault(); setDragOver(true) }}
            onDragLeave={() => setDragOver(false)}
            onDrop={onDrop}
            onClick={() => fileInputRef.current?.click()}
            className={`relative flex flex-col items-center justify-center gap-2 rounded-xl border-2 border-dashed cursor-pointer transition-colors p-8
              ${dragOver
                ? 'border-gray-900 bg-gray-50'
                : selectedFile
                  ? 'border-emerald-400 bg-emerald-50'
                  : 'border-gray-200 hover:border-gray-300 bg-gray-50'
              }`}
          >
            <input
              ref={fileInputRef}
              type="file"
              accept=".csv,.txt,.tsv"
              className="sr-only"
              onChange={onFileChange}
            />
            {selectedFile ? (
              <>
                <span className="text-2xl">✓</span>
                <p className="text-sm font-medium text-emerald-700">{selectedFile.name}</p>
                <p className="text-xs text-gray-400">
                  {(selectedFile.size / 1024).toFixed(1)} Ko — cliquez pour changer
                </p>
              </>
            ) : (
              <>
                <span className="text-2xl text-gray-300">↑</span>
                <p className="text-sm text-gray-500">
                  Glissez votre CSV ici ou <span className="text-gray-900 font-medium">parcourez</span>
                </p>
                <p className="text-xs text-gray-400">Formats .csv acceptés</p>
              </>
            )}
          </div>
        </div>

        {/* Bouton import */}
        <button
          onClick={handleImport}
          disabled={!accountId || !selectedFile || mutation.isPending}
          className="w-full py-2.5 rounded-lg text-sm font-medium bg-gray-900 text-white hover:bg-gray-700 disabled:opacity-40 disabled:cursor-not-allowed transition-colors"
        >
          {mutation.isPending ? 'Import en cours…' : 'Importer'}
        </button>
      </div>

      {/* Erreur */}
      {error && (
        <div className="rounded-xl border border-red-200 bg-red-50 p-4 text-sm text-red-700">
          {error}
        </div>
      )}

      {/* Résultat */}
      {result && (
        <div className="rounded-xl border border-gray-100 bg-white p-5 space-y-4">
          <div className="flex items-center justify-between">
            <h2 className="text-sm font-semibold text-gray-900">Résultat de l'import</h2>
            <button onClick={reset} className="text-xs text-gray-400 hover:text-gray-700 transition-colors">
              Nouvel import
            </button>
          </div>

          <div className="flex items-center gap-2 text-xs text-gray-500">
            <span className="px-2 py-0.5 rounded-full bg-gray-100 text-gray-600 font-medium">
              {result.format_label}
            </span>
            {selectedAccount && (
              <span>→ {selectedAccount.name}</span>
            )}
          </div>

          <div className="grid grid-cols-3 gap-3">
            <div className="rounded-lg bg-emerald-50 border border-emerald-100 p-3 text-center">
              <p className="text-2xl font-bold text-emerald-700">{result.imported}</p>
              <p className="text-xs text-emerald-600 mt-0.5">Importées</p>
            </div>
            <div className="rounded-lg bg-gray-50 border border-gray-100 p-3 text-center">
              <p className="text-2xl font-bold text-gray-500">{result.skipped_zero}</p>
              <p className="text-xs text-gray-400 mt-0.5">Ignorées (zéro)</p>
            </div>
            <div className={`rounded-lg border p-3 text-center ${result.errors_count > 0 ? 'bg-red-50 border-red-100' : 'bg-gray-50 border-gray-100'}`}>
              <p className={`text-2xl font-bold ${result.errors_count > 0 ? 'text-red-600' : 'text-gray-400'}`}>
                {result.errors_count}
              </p>
              <p className={`text-xs mt-0.5 ${result.errors_count > 0 ? 'text-red-500' : 'text-gray-400'}`}>
                Erreurs
              </p>
            </div>
          </div>

          {result.errors_preview.length > 0 && (
            <div className="rounded-lg bg-red-50 border border-red-100 p-3">
              <p className="text-xs font-semibold text-red-600 mb-2">Détail des erreurs</p>
              <ul className="space-y-1">
                {result.errors_preview.map((e, i) => (
                  <li key={i} className="text-xs text-red-600 font-mono">{e}</li>
                ))}
              </ul>
            </div>
          )}

          {result.imported > 0 && result.errors_count === 0 && (
            <p className="text-xs text-emerald-600 font-medium">
              Import réussi — les transactions sont maintenant visibles dans le compte.
            </p>
          )}
        </div>
      )}
    </div>
  )
}
