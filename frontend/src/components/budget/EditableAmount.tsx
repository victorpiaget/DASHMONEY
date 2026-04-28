import { useState } from 'react'

function parseAmount(s: string): number {
  return parseFloat(s) || 0
}

export default function EditableAmount({
  value,
  onSave,
  onDelete,
}: {
  value: string | null
  onSave: (amount: string) => void
  onDelete?: () => void
}) {
  const [editing, setEditing] = useState(false)
  const [input, setInput] = useState(value ?? '')

  function commit() {
    const trimmed = input.trim()
    if (trimmed && parseFloat(trimmed) > 0) {
      onSave(parseFloat(trimmed).toFixed(2))
    }
    setEditing(false)
  }

  if (editing) {
    return (
      <input
        autoFocus
        type="number"
        min="0"
        step="0.01"
        value={input}
        onChange={e => setInput(e.target.value)}
        onBlur={commit}
        onKeyDown={e => { if (e.key === 'Enter') commit(); if (e.key === 'Escape') setEditing(false) }}
        className="w-24 text-right border border-blue-400 rounded px-1 py-0.5 text-sm focus:outline-none"
      />
    )
  }

  return (
    <span className="group relative inline-flex items-center gap-1">
      {value != null ? (
        <button
          onClick={() => { setInput(value); setEditing(true) }}
          className="text-sm font-medium tabular-nums hover:text-blue-600 dark:hover:text-blue-400 transition-colors"
          title="Cliquer pour modifier"
        >
          {parseAmount(value).toLocaleString('fr-FR', { minimumFractionDigits: 0, maximumFractionDigits: 0 })}
        </button>
      ) : (
        <button
          onClick={() => { setInput(''); setEditing(true) }}
          className="text-xs text-gray-400 hover:text-blue-500 border border-dashed border-gray-300 dark:border-gray-600 rounded px-2 py-0.5 transition-colors"
          title="Définir un budget"
        >
          Définir
        </button>
      )}
      {value != null && onDelete && (
        <button
          onClick={onDelete}
          className="opacity-0 group-hover:opacity-100 transition-opacity text-gray-400 hover:text-red-500 text-xs ml-1"
          title="Supprimer"
        >
          ✕
        </button>
      )}
    </span>
  )
}
