import { useState, useEffect, useRef } from 'react'

const MONTH_LABELS = ['Jan', 'Fév', 'Mar', 'Avr', 'Mai', 'Jun', 'Jul', 'Aoû', 'Sep', 'Oct', 'Nov', 'Déc']

interface MonthRangePickerProps {
  /** Plage sélectionnée, format "YYYY-MM" */
  from: string | null
  to: string | null
  /** Mois le plus ancien sélectionnable, ex : "2020-06" */
  minMonth?: string
  /** Mois le plus récent sélectionnable, ex : "2026-03" */
  maxMonth?: string
  onChange: (from: string, to: string) => void
}

function cmpMonth(a: string, b: string): number {
  return a < b ? -1 : a > b ? 1 : 0
}

function toMonthKey(year: number, month: number): string {
  return `${year}-${String(month).padStart(2, '0')}`
}

export default function MonthRangePicker({
  from,
  to,
  minMonth,
  maxMonth,
  onChange,
}: MonthRangePickerProps) {
  const today = new Date()
  const currentYear = today.getFullYear()
  const defaultMax = toMonthKey(currentYear, today.getMonth() + 1)
  const effectiveMax = maxMonth ?? defaultMax

  const [open, setOpen] = useState(false)
  const [navYear, setNavYear] = useState(currentYear)

  // État interne de la sélection en cours (format "YYYY-MM")
  const [pickStart, setPickStart] = useState<string | null>(from)
  const [pickEnd, setPickEnd] = useState<string | null>(to)
  const [pickingEnd, setPickingEnd] = useState(false)
  const [hoverMonth, setHoverMonth] = useState<string | null>(null)

  const popoverRef = useRef<HTMLDivElement>(null)

  // Sync si le parent change from/to (ex : clic sur un preset)
  useEffect(() => {
    setPickStart(from)
    setPickEnd(to)
    setPickingEnd(false)
  }, [from, to])

  // Fermer au clic extérieur
  useEffect(() => {
    if (!open) return
    const handler = (e: MouseEvent) => {
      if (popoverRef.current && !popoverRef.current.contains(e.target as Node)) {
        setOpen(false)
        setPickingEnd(false)
      }
    }
    document.addEventListener('mousedown', handler)
    return () => document.removeEventListener('mousedown', handler)
  }, [open])

  // Naviguer vers l'année contenant `from` quand on ouvre
  useEffect(() => {
    if (open && from) {
      setNavYear(parseInt(from.slice(0, 4)))
    }
  }, [open])

  const handleMonthClick = (key: string) => {
    if (!pickingEnd) {
      // Premier clic : début de sélection
      setPickStart(key)
      setPickEnd(null)
      setPickingEnd(true)
    } else {
      // Deuxième clic : fin de sélection
      const start = pickStart!
      const [finalFrom, finalTo] = cmpMonth(start, key) <= 0 ? [start, key] : [key, start]
      setPickStart(finalFrom)
      setPickEnd(finalTo)
      setPickingEnd(false)
      setHoverMonth(null)
      onChange(finalFrom, finalTo)
      setOpen(false)
    }
  }

  const getMonthState = (key: string): 'disabled' | 'start' | 'end' | 'in-range' | 'single' | 'hover-start' | 'hover-end' | 'hover-range' | 'default' => {
    if (minMonth && cmpMonth(key, minMonth) < 0) return 'disabled'
    if (cmpMonth(key, effectiveMax) > 0) return 'disabled'

    // Pendant le picking, afficher l'aperçu avec le hover
    if (pickingEnd && pickStart) {
      const hovered = hoverMonth ?? pickStart
      const [previewFrom, previewTo] =
        cmpMonth(pickStart, hovered) <= 0 ? [pickStart, hovered] : [hovered, pickStart]

      if (key === previewFrom && key === previewTo) return 'single'
      if (key === previewFrom) return 'hover-start'
      if (key === previewTo) return 'hover-end'
      if (cmpMonth(key, previewFrom) > 0 && cmpMonth(key, previewTo) < 0) return 'hover-range'
    }

    if (!pickStart || !pickEnd) {
      if (key === pickStart) return 'single'
      return 'default'
    }

    if (key === pickStart && key === pickEnd) return 'single'
    if (key === pickStart) return 'start'
    if (key === pickEnd) return 'end'
    if (cmpMonth(key, pickStart) > 0 && cmpMonth(key, pickEnd) < 0) return 'in-range'
    return 'default'
  }

  const stateToStyle = (state: ReturnType<typeof getMonthState>) => {
    switch (state) {
      case 'disabled': return 'text-gray-300 cursor-not-allowed'
      case 'start':
      case 'hover-start': return 'bg-gray-900 text-white rounded-l-full font-medium'
      case 'end':
      case 'hover-end': return 'bg-gray-900 text-white rounded-r-full font-medium'
      case 'single': return 'bg-gray-900 text-white rounded-full font-medium'
      case 'in-range':
      case 'hover-range': return 'bg-gray-100 text-gray-700'
      default: return 'text-gray-700 hover:bg-gray-100 rounded-full'
    }
  }

  // Label affiché sur le bouton toggle
  const label = (() => {
    if (!from || !to) return 'Personnalisé'
    if (from === to) {
      const [y, m] = from.split('-')
      return `${MONTH_LABELS[parseInt(m) - 1]} ${y}`
    }
    const [fy, fm] = from.split('-')
    const [ty, tm] = to.split('-')
    const fromLabel = `${MONTH_LABELS[parseInt(fm) - 1]} ${fy}`
    const toLabel = `${MONTH_LABELS[parseInt(tm) - 1]} ${ty}`
    return `${fromLabel} → ${toLabel}`
  })()

  const minYear = minMonth ? parseInt(minMonth.slice(0, 4)) : currentYear - 10
  const maxYear = parseInt(effectiveMax.slice(0, 4))

  return (
    <div className="relative" ref={popoverRef}>
      <button
        onClick={() => setOpen((v) => !v)}
        className={`flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium rounded-lg border transition-colors ${
          open
            ? 'border-gray-900 bg-gray-900 text-white'
            : 'border-gray-200 bg-white text-gray-700 hover:border-gray-300'
        }`}
      >
        <svg className="w-3.5 h-3.5 flex-shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 7V3m8 4V3m-9 8h10M5 21h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v12a2 2 0 002 2z" />
        </svg>
        {label}
      </button>

      {open && (
        <div className="absolute right-0 top-full mt-2 z-50 bg-white rounded-xl border border-gray-200 shadow-xl p-4 w-64">
          {/* Navigation année */}
          <div className="flex items-center justify-between mb-3">
            <button
              onClick={() => setNavYear((y) => Math.max(y - 1, minYear))}
              disabled={navYear <= minYear}
              className="p-1 rounded-lg hover:bg-gray-100 disabled:opacity-30 disabled:cursor-not-allowed text-gray-600"
            >
              ‹
            </button>
            <span className="text-sm font-semibold text-gray-900">{navYear}</span>
            <button
              onClick={() => setNavYear((y) => Math.min(y + 1, maxYear))}
              disabled={navYear >= maxYear}
              className="p-1 rounded-lg hover:bg-gray-100 disabled:opacity-30 disabled:cursor-not-allowed text-gray-600"
            >
              ›
            </button>
          </div>

          {/* Hint */}
          <p className="text-[10px] text-gray-400 text-center mb-2">
            {pickingEnd ? 'Cliquez sur le mois de fin' : 'Cliquez sur le mois de début'}
          </p>

          {/* Grille 4×3 */}
          <div className="grid grid-cols-4 gap-0.5">
            {Array.from({ length: 12 }, (_, idx) => {
              const key = toMonthKey(navYear, idx + 1)
              const state = getMonthState(key)
              return (
                <button
                  key={key}
                  disabled={state === 'disabled'}
                  onClick={() => state !== 'disabled' && handleMonthClick(key)}
                  onMouseEnter={() => pickingEnd && setHoverMonth(key)}
                  onMouseLeave={() => setHoverMonth(null)}
                  className={`text-xs py-2 text-center transition-colors select-none ${stateToStyle(state)}`}
                >
                  {MONTH_LABELS[idx]}
                </button>
              )
            })}
          </div>

          {/* Réinitialiser */}
          {(pickStart || pickEnd) && !pickingEnd && (
            <button
              onClick={() => {
                setPickStart(null)
                setPickEnd(null)
                setPickingEnd(false)
              }}
              className="mt-3 w-full text-[10px] text-gray-400 hover:text-gray-600 text-center transition-colors"
            >
              Effacer la sélection
            </button>
          )}
        </div>
      )}
    </div>
  )
}
