import { useState, useEffect, useRef } from 'react'
import { createPortal } from 'react-dom'
import {
  compareMonths,
  resolveToMonthRange,
  toYearMonth,
  type PeriodSelection,
  type Preset,
} from '../lib/period'

// ── Types exportés ─────────────────────────────────────────────────────────────

// ── Constantes ─────────────────────────────────────────────────────────────────

const MONTH_LABELS = ['Jan', 'Fév', 'Mar', 'Avr', 'Mai', 'Jun', 'Jul', 'Aoû', 'Sep', 'Oct', 'Nov', 'Déc']

const PRESETS: { key: Preset; label: string }[] = [
  { key: '1M', label: '1 mois' },
  { key: '3M', label: '3 mois' },
  { key: '6M', label: '6 mois' },
  { key: '1A', label: '1 an' },
  { key: '2A', label: '2 ans' },
  { key: 'tout', label: 'Tout' },
]

// ── Utilitaires ────────────────────────────────────────────────────────────────

// ── Composant ──────────────────────────────────────────────────────────────────

interface PeriodPickerProps {
  selection: PeriodSelection
  onChange: (s: PeriodSelection) => void
  minMonth: string // "YYYY-MM"
  exactPresetCount?: boolean
}

export default function PeriodPicker({
  selection,
  onChange,
  minMonth,
  exactPresetCount = false,
}: PeriodPickerProps) {
  const now = new Date()
  const maxMonth = toYearMonth(now.getFullYear(), now.getMonth() + 1)
  const maxYear = now.getFullYear()
  const minYear = parseInt(minMonth.slice(0, 4))

  const resolved = resolveToMonthRange(selection, minMonth, exactPresetCount)

  const [open, setOpen] = useState(false)
  const [viewYear, setViewYear] = useState(() => parseInt(resolved.to.slice(0, 4)))
  const [pickStart, setPickStart] = useState<string | null>(null)
  const [hover, setHover] = useState<string | null>(null)

  // Refs pour positionner le popover et détecter le clic extérieur
  const triggerRef = useRef<HTMLButtonElement>(null)
  const popoverRef = useRef<HTMLDivElement>(null)
  const [pos, setPos] = useState({ top: 0, right: 0 })

  // Fermer au clic extérieur (les deux refs)
  useEffect(() => {
    if (!open) return
    const h = (e: MouseEvent) => {
      const target = e.target as Node
      if (
        !triggerRef.current?.contains(target) &&
        !popoverRef.current?.contains(target)
      ) {
        setOpen(false)
        setPickStart(null)
        setHover(null)
      }
    }
    document.addEventListener('mousedown', h)
    return () => document.removeEventListener('mousedown', h)
  }, [open])

  const openPopover = () => {
    if (triggerRef.current) {
      const r = triggerRef.current.getBoundingClientRect()
      setPos({ top: r.bottom + 8, right: window.innerWidth - r.right })
    }
    if (!open) setViewYear(parseInt(resolved.to.slice(0, 4)))
    setOpen(!open)
    setPickStart(null)
    setHover(null)
  }

  // ── État d'un mois ─────────────────────────────────────────────────────────

  type CellState = 'disabled' | 'start' | 'end' | 'in-range' | 'single'
    | 'p-start' | 'p-end' | 'p-range' | 'p-single' | 'default'

  const getState = (ym: string): CellState => {
    if (compareMonths(ym, minMonth) < 0 || compareMonths(ym, maxMonth) > 0) return 'disabled'

    if (pickStart !== null) {
      const endYM =
        hover && compareMonths(hover, minMonth) >= 0 && compareMonths(hover, maxMonth) <= 0 ? hover : pickStart
      const [f, t] = compareMonths(pickStart, endYM) <= 0 ? [pickStart, endYM] : [endYM, pickStart]
      if (ym === f && ym === t) return 'p-single'
      if (ym === f) return 'p-start'
      if (ym === t) return 'p-end'
      if (compareMonths(ym, f) > 0 && compareMonths(ym, t) < 0) return 'p-range'
      return 'default'
    }

    const { from, to } = resolved
    if (ym === from && ym === to) return 'single'
    if (ym === from) return 'start'
    if (ym === to) return 'end'
    if (compareMonths(ym, from) > 0 && compareMonths(ym, to) < 0) return 'in-range'
    return 'default'
  }

  const cellClass = (state: CellState, idx: number): string => {
    const col = idx % 4
    const roundL = col === 0 ? 'rounded-l-lg' : ''
    const roundR = col === 3 ? 'rounded-r-lg' : ''
    switch (state) {
      case 'start':
      case 'p-start':
        return `bg-gray-900 text-white font-semibold rounded-l-lg ${col === 3 ? 'rounded-r-lg' : ''}`
      case 'end':
      case 'p-end':
        return `bg-gray-900 text-white font-semibold rounded-r-lg ${col === 0 ? 'rounded-l-lg' : ''}`
      case 'single':
      case 'p-single':
        return 'bg-gray-900 text-white font-semibold rounded-lg'
      case 'in-range':
      case 'p-range':
        return `bg-gray-200 text-gray-800 ${roundL} ${roundR}`
      case 'disabled':
        return 'text-gray-300 cursor-not-allowed'
      default:
        return 'text-gray-600 hover:bg-gray-100 rounded-lg'
    }
  }

  const handleMonthClick = (ym: string) => {
    if (!pickStart) {
      setPickStart(ym)
    } else {
      const [from, to] = compareMonths(pickStart, ym) <= 0 ? [pickStart, ym] : [ym, pickStart]
      onChange({ type: 'custom', from, to })
      setPickStart(null)
      setHover(null)
      setOpen(false)
    }
  }

  // ── Label du trigger ───────────────────────────────────────────────────────

  const fmtYM = (ym: string) => {
    const [y, m] = ym.split('-')
    return new Date(parseInt(y), parseInt(m) - 1, 1).toLocaleDateString('fr-FR', {
      month: 'short', year: 'numeric',
    })
  }
  const triggerLabel =
    resolved.from === resolved.to
      ? fmtYM(resolved.from)
      : `${fmtYM(resolved.from)} → ${fmtYM(resolved.to)}`

  const canPrev = viewYear > minYear
  const canNext = viewYear < maxYear

  // ── Popover (rendu via portal pour bypasser overflow:auto du layout) ────────

  const popover = open ? createPortal(
    <div
      ref={popoverRef}
      style={{ position: 'fixed', top: pos.top, right: pos.right, width: 360, zIndex: 9999 }}
      className="bg-white rounded-2xl border border-gray-100 shadow-2xl"
    >
      {/* Presets */}
      <div className="px-4 pt-4 pb-3.5 flex flex-wrap gap-1.5 border-b border-gray-100">
        {PRESETS.map((p) => (
          <button
            key={p.key}
            type="button"
            onClick={() => {
              onChange({ type: 'preset', preset: p.key })
              setPickStart(null)
              setHover(null)
              setOpen(false)
            }}
            className={`px-3 py-1.5 text-xs font-medium rounded-lg transition-colors ${
              selection.type === 'preset' && selection.preset === p.key
                ? 'bg-gray-900 text-white'
                : 'bg-gray-100 text-gray-600 hover:bg-gray-200'
            }`}
          >
            {p.label}
          </button>
        ))}
      </div>

      {/* Navigation année — pas de disabled HTML, CSS seulement */}
      <div className="flex items-center justify-between px-5 py-3 border-b border-gray-100">
        <button
          type="button"
          onClick={() => { if (canPrev) setViewYear((y) => y - 1) }}
          className={`w-8 h-8 flex items-center justify-center rounded-lg text-lg transition-colors ${
            canPrev ? 'text-gray-500 hover:bg-gray-100 cursor-pointer' : 'text-gray-200 cursor-default'
          }`}
        >
          ‹
        </button>
        <span className="text-sm font-semibold text-gray-800">{viewYear}</span>
        <button
          type="button"
          onClick={() => { if (canNext) setViewYear((y) => y + 1) }}
          className={`w-8 h-8 flex items-center justify-center rounded-lg text-lg transition-colors ${
            canNext ? 'text-gray-500 hover:bg-gray-100 cursor-pointer' : 'text-gray-200 cursor-default'
          }`}
        >
          ›
        </button>
      </div>

      {/* Indicateur sélection en cours */}
      {pickStart && (
        <div className="px-4 py-2 bg-gray-50 border-b border-gray-100">
          <p className="text-[11px] text-gray-500 font-medium text-center">
            Début :{' '}
            <span className="text-gray-800">
              {MONTH_LABELS[parseInt(pickStart.split('-')[1]) - 1]} {pickStart.split('-')[0]}
            </span>
            {' '}— cliquez sur le mois de fin
          </p>
        </div>
      )}

      {/* Grille 4×3 — pas de disabled HTML, CSS + JS seulement */}
      <div className="px-3 py-3">
        <div className="grid grid-cols-4 gap-y-1">
          {Array.from({ length: 12 }, (_, i) => {
            const ym = toYearMonth(viewYear, i + 1)
            const state = getState(ym)
            const isDisabled = state === 'disabled'
            return (
              <button
                key={ym}
                type="button"
                onClick={() => { if (!isDisabled) handleMonthClick(ym) }}
                onMouseEnter={() => { if (pickStart && !isDisabled) setHover(ym) }}
                onMouseLeave={() => setHover(null)}
                className={`text-xs py-2.5 text-center transition-colors select-none ${cellClass(state, i)}`}
              >
                {MONTH_LABELS[i]}
              </button>
            )
          })}
        </div>
      </div>

      {/* Footer */}
      <div className="px-4 py-2.5 border-t border-gray-100 flex items-center justify-between">
        <p className="text-[10px] text-gray-400">
          {pickStart ? 'Sélectionnez le mois de fin' : 'Cliquez un mois pour une plage libre'}
        </p>
        <button
          type="button"
          onClick={() => { setOpen(false); setPickStart(null); setHover(null) }}
          className="text-[11px] text-gray-400 hover:text-gray-600 transition-colors cursor-pointer"
        >
          Fermer
        </button>
      </div>
    </div>,
    document.body,
  ) : null

  return (
    <div className="relative">
      <button
        ref={triggerRef}
        onClick={openPopover}
        className={`flex items-center gap-2 px-3.5 py-2 rounded-xl text-sm font-medium transition-all border ${
          open
            ? 'bg-gray-900 text-white border-gray-900 shadow-md'
            : 'bg-white text-gray-700 border-gray-200 hover:border-gray-300 shadow-sm'
        }`}
      >
        <svg className={`w-4 h-4 flex-shrink-0 ${open ? 'text-gray-300' : 'text-gray-400'}`} fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M8 7V3m8 4V3m-9 8h10M5 21h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v12a2 2 0 002 2z" />
        </svg>
        <span className="whitespace-nowrap">{triggerLabel}</span>
        <svg className={`w-3.5 h-3.5 flex-shrink-0 transition-transform ${open ? 'rotate-180 text-gray-300' : 'text-gray-400'}`} fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
        </svg>
      </button>

      {popover}
    </div>
  )
}
