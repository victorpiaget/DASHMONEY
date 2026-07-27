import { useMemo, useState } from 'react'
import {
  ResponsiveContainer,
  Sankey,
  Tooltip,
  useChartWidth,
  type SankeyLinkProps,
  type SankeyNodeProps,
} from 'recharts'
import { useCurrency } from '../../context/CurrencyContext'
import { useTheme } from '../../context/ThemeContext'
import type {
  BudgetFlowExpenseCategory,
  BudgetFlowResponse,
  CategoryNature,
} from '../../lib/budgetApi'

type FlowNodeKind =
  | 'income'
  | 'deficit'
  | 'budget'
  | 'nature'
  | 'expense'
  | 'subcategory'
  | 'remaining'

interface FlowNodeDatum {
  name: string
  amount: number
  formattedAmount?: string
  color: string
  kind: FlowNodeKind
  category?: string
}

interface FlowLinkDatum {
  source: number
  target: number
  value: number
  color: string
  name: string
}

const NATURE_META: Record<
  CategoryNature | 'UNCATEGORIZED',
  { label: string; color: string; badge: string }
> = {
  NEED: {
    label: 'Besoins',
    color: '#3b82f6',
    badge: 'bg-blue-50 text-blue-700 dark:bg-blue-900/30 dark:text-blue-300',
  },
  WANT: {
    label: 'Envies',
    color: '#8b5cf6',
    badge: 'bg-violet-50 text-violet-700 dark:bg-violet-900/30 dark:text-violet-300',
  },
  SAVING: {
    label: 'Épargne',
    color: '#10b981',
    badge: 'bg-emerald-50 text-emerald-700 dark:bg-emerald-900/30 dark:text-emerald-300',
  },
  UNCATEGORIZED: {
    label: 'Non classé',
    color: '#eab308',
    badge: 'bg-yellow-50 text-yellow-700 dark:bg-yellow-900/30 dark:text-yellow-300',
  },
}

function natureKey(nature: CategoryNature | null): CategoryNature | 'UNCATEGORIZED' {
  return nature ?? 'UNCATEGORIZED'
}

function shortLabel(label: string): string {
  return label.length > 24 ? `${label.slice(0, 22)}…` : label
}

function FlowNode({ x, y, width, height, payload }: SankeyNodeProps) {
  const chartWidth = useChartWidth()
  const node = payload as typeof payload & FlowNodeDatum
  const labelOnRight = node.depth === 0
  const labelX = labelOnRight ? x + width + 8 : x - 8
  const textAnchor = labelOnRight ? 'start' : 'end'
  const safeHeight = Math.max(height, 5)

  if (chartWidth == null) return null

  return (
    <g className={node.kind === 'expense' ? 'cursor-pointer' : undefined}>
      <rect
        x={x}
        y={y + (height - safeHeight) / 2}
        width={width}
        height={safeHeight}
        rx={4}
        fill={node.color}
        stroke={node.color}
        strokeWidth={1}
      />
      <text
        x={labelX}
        y={y + height / 2 - 3}
        textAnchor={textAnchor}
        className="fill-gray-800 dark:fill-gray-100"
        fontSize={12}
        fontWeight={600}
        pointerEvents="none"
      >
        {shortLabel(node.name)}
      </text>
      <text
        x={labelX}
        y={y + height / 2 + 12}
        textAnchor={textAnchor}
        className="fill-gray-400 dark:fill-gray-500"
        fontSize={10}
        pointerEvents="none"
      >
        {node.formattedAmount}
      </text>
    </g>
  )
}

function FlowLink({
  sourceX,
  sourceY,
  sourceControlX,
  targetX,
  targetY,
  targetControlX,
  linkWidth,
  payload,
}: SankeyLinkProps) {
  const link = payload as typeof payload & { color?: string }
  return (
    <path
      d={`M${sourceX},${sourceY} C${sourceControlX},${sourceY} ${targetControlX},${targetY} ${targetX},${targetY}`}
      fill="none"
      stroke={link.color ?? '#94a3b8'}
      strokeWidth={Math.max(linkWidth, 1)}
      strokeOpacity={0.34}
      className="transition-opacity hover:opacity-80"
    />
  )
}

function buildSankeyData(
  data: BudgetFlowResponse,
  formatAmount: (amount: number) => string,
  expandedCategory: string | null,
): {
  nodes: FlowNodeDatum[]
  links: FlowLinkDatum[]
} {
  const nodes: FlowNodeDatum[] = []
  const links: FlowLinkDatum[] = []
  const sourceIndexes: { index: number; amount: number; color: string; name: string }[] = []

  for (const source of data.income_sources) {
    const amount = Number(source.amount)
    if (amount <= 0) continue
    const name = source.subcategory ?? source.category
    sourceIndexes.push({
      index: nodes.length,
      amount,
      color: '#4f6df5',
      name,
    })
    nodes.push({ name, amount, color: '#4f6df5', kind: 'income' })
  }

  const deficit = Number(data.summary.deficit)
  if (deficit > 0) {
    sourceIndexes.push({
      index: nodes.length,
      amount: deficit,
      color: '#ef4444',
      name: 'Financement du déficit',
    })
    nodes.push({
      name: 'Financement du déficit',
      amount: deficit,
      color: '#ef4444',
      kind: 'deficit',
    })
  }

  const budgetAmount = Math.max(
    Number(data.summary.total_income),
    Number(data.summary.total_outflows),
  )
  const budgetIndex = nodes.length
  nodes.push({
    name: 'Budget de la période',
    amount: budgetAmount,
    color: '#fb923c',
    kind: 'budget',
  })

  for (const source of sourceIndexes) {
    links.push({
      source: source.index,
      target: budgetIndex,
      value: source.amount,
      color: source.color,
      name: `${source.name} → Budget de la période`,
    })
  }

  const categoriesByNature = new Map<
    CategoryNature | 'UNCATEGORIZED',
    BudgetFlowExpenseCategory[]
  >()
  for (const category of data.expense_categories) {
    const key = natureKey(category.nature)
    const current = categoriesByNature.get(key) ?? []
    current.push(category)
    categoriesByNature.set(key, current)
  }

  for (const key of ['NEED', 'WANT', 'SAVING', 'UNCATEGORIZED'] as const) {
    const categories = categoriesByNature.get(key)
    if (!categories?.length) continue
    const meta = NATURE_META[key]
    const amount = categories.reduce((sum, category) => sum + Number(category.amount), 0)
    const natureIndex = nodes.length
    nodes.push({
      name: meta.label,
      amount,
      color: meta.color,
      kind: 'nature',
    })
    links.push({
      source: budgetIndex,
      target: natureIndex,
      value: amount,
      color: meta.color,
      name: `Budget de la période → ${meta.label}`,
    })

    for (const category of categories) {
      const categoryAmount = Number(category.amount)
      if (categoryAmount <= 0) continue
      const categoryIndex = nodes.length
      nodes.push({
        name: category.category,
        amount: categoryAmount,
        color: meta.color,
        kind: 'expense',
        category: category.category,
      })
      links.push({
        source: natureIndex,
        target: categoryIndex,
        value: categoryAmount,
        color: meta.color,
        name: `${meta.label} → ${category.category}`,
      })

      if (category.category === expandedCategory) {
        for (const subcategory of category.subcategories) {
          const subcategoryAmount = Number(subcategory.amount)
          if (subcategoryAmount <= 0) continue
          const subcategoryName = subcategory.subcategory ?? 'Sans sous-catégorie'
          const subcategoryIndex = nodes.length
          nodes.push({
            name: subcategoryName,
            amount: subcategoryAmount,
            color: meta.color,
            kind: 'subcategory',
            category: category.category,
          })
          links.push({
            source: categoryIndex,
            target: subcategoryIndex,
            value: subcategoryAmount,
            color: meta.color,
            name: `${category.category} → ${subcategoryName}`,
          })
        }
      }
    }
  }

  const remaining = Number(data.summary.remaining)
  if (remaining > 0) {
    const remainingIndex = nodes.length
    nodes.push({
      name: 'Reste disponible',
      amount: remaining,
      color: '#14b8a6',
      kind: 'remaining',
    })
    links.push({
      source: budgetIndex,
      target: remainingIndex,
      value: remaining,
      color: '#14b8a6',
      name: 'Budget de la période → Reste disponible',
    })
  }

  return {
    nodes: nodes.map((node) => ({
      ...node,
      formattedAmount: formatAmount(node.amount),
    })),
    links,
  }
}

function CategoryDetail({
  category,
  currency,
}: {
  category: BudgetFlowExpenseCategory
  currency: string
}) {
  const { format } = useCurrency()
  const meta = NATURE_META[natureKey(category.nature)]
  const total = Number(category.amount)

  return (
    <div className="border-t border-gray-100 dark:border-gray-700 px-5 py-4">
      <div className="flex items-center justify-between gap-3 mb-3">
        <div className="flex items-center gap-2 min-w-0">
          <p className="text-sm font-semibold text-gray-800 dark:text-gray-100 truncate">
            Détail · {category.category}
          </p>
          <span className={`text-[10px] font-medium rounded px-1.5 py-0.5 ${meta.badge}`}>
            {meta.label}
          </span>
        </div>
        <p className="text-sm font-semibold tabular-nums text-gray-700 dark:text-gray-200">
          {format(category.amount, currency)}
        </p>
      </div>
      <div className="grid grid-cols-1 md:grid-cols-2 gap-x-8 gap-y-2.5">
        {category.subcategories.map((subcategory) => {
          const amount = Number(subcategory.amount)
          const percentage = total > 0 ? amount / total * 100 : 0
          return (
            <div key={subcategory.subcategory ?? '__direct__'} className="space-y-1">
              <div className="flex items-center justify-between gap-3 text-xs">
                <span className="text-gray-600 dark:text-gray-300 truncate">
                  {subcategory.subcategory ?? 'Sans sous-catégorie'}
                </span>
                <span className="text-gray-500 dark:text-gray-400 tabular-nums">
                  {format(subcategory.amount, currency)}
                </span>
              </div>
              <div className="h-1.5 rounded-full bg-gray-100 dark:bg-gray-700 overflow-hidden">
                <div
                  className="h-full rounded-full"
                  style={{ width: `${Math.min(percentage, 100)}%`, backgroundColor: meta.color }}
                />
              </div>
            </div>
          )
        })}
      </div>
    </div>
  )
}

export default function BudgetFlowSankey({ data }: { data: BudgetFlowResponse }) {
  const { format } = useCurrency()
  const { theme } = useTheme()
  const [expandedCategory, setExpandedCategory] = useState<string | null>(null)
  const [selectedCategory, setSelectedCategory] = useState<string | null>(null)
  const sankeyData = useMemo(
    () => buildSankeyData(
      data,
      (amount) => format(amount, data.currency),
      expandedCategory,
    ),
    [data, expandedCategory, format],
  )

  const selected = data.expense_categories.find(
    (category) => category.category === selectedCategory,
  ) ?? data.expense_categories[0]
  const expanded = data.expense_categories.find(
    (category) => category.category === expandedCategory,
  )
  const hasFlow = Number(data.summary.total_income) > 0 || Number(data.summary.total_outflows) > 0
  const visibleTerminalCount = Math.max(
    data.expense_categories.length,
    data.income_sources.length,
    expanded?.subcategories.length ?? 0,
  )
  const chartHeight = Math.min(
    760,
    Math.max(480, visibleTerminalCount * 36 + 220),
  )

  if (!hasFlow) {
    return (
      <div className="bg-white dark:bg-gray-800 rounded-2xl border border-gray-100 dark:border-gray-700 min-h-80 flex flex-col items-center justify-center text-center px-6">
        <div className="w-12 h-12 rounded-2xl bg-gray-100 dark:bg-gray-700 flex items-center justify-center text-gray-400 text-xl mb-3">
          ≋
        </div>
        <p className="text-sm font-semibold text-gray-700 dark:text-gray-200">
          Aucun flux sur cette période
        </p>
        <p className="text-xs text-gray-400 dark:text-gray-500 mt-1 max-w-sm">
          Choisis une autre période ou importe des transactions pour afficher la circulation de ton budget.
        </p>
      </div>
    )
  }

  return (
    <div className="bg-white dark:bg-gray-800 rounded-2xl border border-gray-100 dark:border-gray-700 overflow-hidden">
      <div className="px-5 py-4 border-b border-gray-100 dark:border-gray-700 flex items-center justify-between gap-4 flex-wrap">
        <div>
          <p className="text-sm font-semibold text-gray-800 dark:text-gray-100">Circulation du budget</p>
          <p className="text-xs text-gray-400 dark:text-gray-500 mt-0.5">
            Clique sur une catégorie pour déployer ses sous-catégories · transferts internes exclus
          </p>
        </div>
        <div className="flex items-center gap-3 flex-wrap">
          {(['NEED', 'WANT', 'SAVING', 'UNCATEGORIZED'] as const).map((key) => (
            <div key={key} className="flex items-center gap-1.5 text-[11px] text-gray-500 dark:text-gray-400">
              <span
                className="w-2.5 h-2.5 rounded-full"
                style={{ backgroundColor: NATURE_META[key].color }}
              />
              {NATURE_META[key].label}
            </div>
          ))}
        </div>
      </div>

      <div className="overflow-x-auto">
        <div
          className="px-4 transition-[min-width] duration-200"
          style={{
            height: chartHeight,
            minWidth: expandedCategory ? 1280 : 980,
          }}
        >
          <ResponsiveContainer width="100%" height="100%">
            <Sankey
              data={sankeyData}
              node={FlowNode}
              link={FlowLink}
              nodeWidth={12}
              nodePadding={24}
              linkCurvature={0.56}
              margin={{ top: 44, right: 185, bottom: 36, left: 145 }}
              sort={false}
              onClick={(item, type) => {
                if (type !== 'node') return
                const node = item.payload as typeof item.payload & FlowNodeDatum
                if (node.kind === 'expense' && node.category) {
                  setSelectedCategory(node.category)
                  setExpandedCategory((current) => (
                    current === node.category ? null : node.category ?? null
                  ))
                }
              }}
            >
              <Tooltip
                formatter={(value, name) => [
                  format(Number(value ?? 0), data.currency),
                  String(name ?? 'Flux'),
                ]}
                contentStyle={{
                  fontSize: 12,
                  borderRadius: 12,
                  borderColor: theme === 'dark' ? '#475569' : '#e5e7eb',
                  backgroundColor: theme === 'dark' ? '#1e293b' : '#ffffff',
                  color: theme === 'dark' ? '#f1f5f9' : '#111827',
                }}
              />
            </Sankey>
          </ResponsiveContainer>
        </div>
      </div>

      {selected && <CategoryDetail category={selected} currency={data.currency} />}
    </div>
  )
}
