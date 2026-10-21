import { Activity, UserRound } from 'lucide-react'
import type { ReactNode } from 'react'

import type { IncidentCategory, IncidentSummary, Severity } from '@/api/types'
import { SeverityBadge } from '@/components/SeverityBadge'
import { type QueueFilters, toggle } from '@/features/queue/useQueueFilters'
import { CATEGORY_ICONS } from '@/lib/categoryIcons'
import { CATEGORY_LABELS, SEVERITY_LABELS } from '@/lib/labels'
import { cn } from '@/lib/utils'

const SEVERITIES: Severity[] = ['high', 'medium', 'low']
const CATEGORIES = Object.keys(CATEGORY_LABELS) as IncidentCategory[]

function Kpi({
  pressed,
  onClick,
  label,
  value,
  children,
  className,
}: {
  pressed: boolean
  onClick: () => void
  label: string
  value: number | undefined
  children: ReactNode
  className?: string
}) {
  return (
    <button
      type="button"
      aria-pressed={pressed}
      aria-label={`${label}: ${value ?? '…'}${pressed ? ' (filtro ativo)' : ''}`}
      onClick={onClick}
      className={cn(
        'flex min-w-0 items-center justify-between gap-3 rounded-md border bg-surface-1 px-3 py-2 text-left transition-colors hover:bg-surface-2',
        pressed && 'border-primary bg-surface-2 ring-1 ring-primary',
        className,
      )}
    >
      <span className="flex min-w-0 items-center gap-2 text-xs text-text-muted">{children}</span>
      <span className="text-lg font-semibold tabular-nums text-text">{value ?? '–'}</span>
    </button>
  )
}

/** Active incidents at a glance. Every KPI is also a filter (click again to remove). */
export function KpiBar({
  summary,
  myCount,
  filters,
  isDefault,
  update,
  clear,
}: {
  summary: IncidentSummary | undefined
  myCount: number | undefined
  filters: QueueFilters
  isDefault: boolean
  update: (change: (current: QueueFilters) => Partial<QueueFilters>) => void
  clear: () => void
}) {
  return (
    <section aria-label="Indicadores dos incidentes ativos" className="grid gap-2">
      <div className="grid grid-cols-2 gap-2 sm:grid-cols-3 lg:grid-cols-5">
        <Kpi
          label="Total ativo"
          value={summary?.total_active}
          pressed={isDefault}
          onClick={clear}
          className="col-span-2 sm:col-span-1"
        >
          <Activity aria-hidden className="size-4" />
          Total ativo
        </Kpi>
        {SEVERITIES.map((severity) => (
          <Kpi
            key={severity}
            label={`Criticidade ${SEVERITY_LABELS[severity]}`}
            value={summary?.by_severity[severity]}
            pressed={filters.severity.includes(severity)}
            onClick={() => update((f) => ({ severity: toggle(f.severity, severity) }))}
          >
            <SeverityBadge severity={severity} />
          </Kpi>
        ))}
        <Kpi
          label="Meus incidentes"
          value={myCount}
          pressed={filters.mine}
          onClick={() => update((f) => ({ mine: !f.mine }))}
        >
          <UserRound aria-hidden className="size-4" />
          Meus incidentes
        </Kpi>
      </div>
      <div className="flex flex-wrap gap-1.5" role="group" aria-label="Ativos por categoria">
        {CATEGORIES.map((category) => {
          const Icon = CATEGORY_ICONS[category]
          const pressed = filters.category.includes(category)
          const count = summary?.by_category[category]
          return (
            <button
              key={category}
              type="button"
              aria-pressed={pressed}
              onClick={() => update((f) => ({ category: toggle(f.category, category) }))}
              className={cn(
                'inline-flex items-center gap-1.5 rounded-md border bg-surface-1 px-2 py-1 text-xs text-text-muted transition-colors hover:bg-surface-2',
                pressed && 'border-primary bg-surface-2 text-text ring-1 ring-primary',
              )}
            >
              <Icon aria-hidden className="size-3.5" />
              {CATEGORY_LABELS[category]}
              <span className="font-semibold tabular-nums text-text">{count ?? '–'}</span>
            </button>
          )
        })}
      </div>
    </section>
  )
}
