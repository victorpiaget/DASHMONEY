export type Preset = '1M' | '3M' | '6M' | '1A' | '2A' | 'tout'

export type PeriodSelection =
  | { type: 'preset'; preset: Preset }
  | { type: 'custom'; from: string; to: string }

export function compareMonths(a: string, b: string): number {
  return a < b ? -1 : a > b ? 1 : 0
}

export function toYearMonth(year: number, month: number): string {
  return `${year}-${String(month).padStart(2, '0')}`
}

function lastDayOfMonth(yearMonth: string): string {
  const [year, month] = yearMonth.split('-').map(Number)
  const lastDay = new Date(year, month, 0).getDate()
  return `${yearMonth}-${String(lastDay).padStart(2, '0')}`
}

export function resolveToMonthRange(
  selection: PeriodSelection,
  minMonth: string,
  exactPresetCount = false,
): { from: string; to: string } {
  const now = new Date()
  const maxMonth = toYearMonth(now.getFullYear(), now.getMonth() + 1)
  if (selection.type === 'custom') return { from: selection.from, to: selection.to }
  if (selection.preset === 'tout') return { from: minMonth, to: maxMonth }

  const offsets = exactPresetCount
    ? { '1M': 0, '3M': 2, '6M': 5, '1A': 11, '2A': 23 }
    : { '1M': 1, '3M': 3, '6M': 6, '1A': 12, '2A': 24 }
  const start = new Date()
  start.setMonth(start.getMonth() - offsets[selection.preset])
  const resolvedFrom = toYearMonth(start.getFullYear(), start.getMonth() + 1)

  return {
    from: compareMonths(resolvedFrom, minMonth) < 0 ? minMonth : resolvedFrom,
    to: maxMonth,
  }
}

export function resolveDates(
  selection: PeriodSelection,
  openedOn: string,
  exactPresetCount = false,
): { from: string; to: string } {
  const minMonth = openedOn.slice(0, 7)
  const { from, to } = resolveToMonthRange(selection, minMonth, exactPresetCount)
  return { from: `${from}-01`, to: lastDayOfMonth(to) }
}
