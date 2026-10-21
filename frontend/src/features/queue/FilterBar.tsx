import { Check, X } from 'lucide-react'

import type { IncidentStatus } from '@/api/types'
import { Button } from '@/components/ui/button'
import {
  DEFAULT_STATUSES,
  type QueueFilters,
  toggle,
} from '@/features/queue/useQueueFilters'
import { CATEGORY_LABELS, SEVERITY_LABELS, STATUS_LABELS } from '@/lib/labels'
import { cn } from '@/lib/utils'

const STATUSES = Object.keys(STATUS_LABELS) as IncidentStatus[]

function Chip({ label, onRemove }: { label: string; onRemove: () => void }) {
  return (
    <span className="inline-flex items-center gap-1 rounded-md border border-border-strong bg-surface-2 py-0.5 pr-0.5 pl-2 text-xs">
      {label}
      <button
        type="button"
        onClick={onRemove}
        aria-label={`Remover filtro: ${label}`}
        className="inline-flex size-5 items-center justify-center rounded-sm text-text-muted hover:bg-surface-3 hover:text-text"
      >
        <X aria-hidden className="size-3" />
      </button>
    </span>
  )
}

export function FilterBar({
  filters,
  isDefault,
  update,
  clear,
  shown,
  total,
}: {
  filters: QueueFilters
  isDefault: boolean
  update: (change: (current: QueueFilters) => Partial<QueueFilters>) => void
  clear: () => void
  shown: number | undefined
  total: number | undefined
}) {
  const statusIsDefault =
    filters.status.length === DEFAULT_STATUSES.length &&
    filters.status.every((s) => DEFAULT_STATUSES.includes(s))

  return (
    <div className="flex flex-wrap items-center gap-2">
      <div role="group" aria-label="Status" className="inline-flex flex-wrap gap-0.5 rounded-md border bg-surface-1 p-0.5">
        {STATUSES.map((status) => {
          const pressed = filters.status.includes(status)
          return (
            <button
              key={status}
              type="button"
              aria-pressed={pressed}
              onClick={() => update((f) => ({ status: toggle(f.status, status) }))}
              className={cn(
                'inline-flex items-center gap-1 rounded-sm border border-transparent px-2 py-1 text-xs text-text-muted transition-colors hover:text-text',
                pressed && 'border-border-strong bg-surface-3 font-medium text-text',
              )}
            >
              {pressed && <Check aria-hidden className="size-3" />}
              {STATUS_LABELS[status]}
            </button>
          )
        })}
      </div>

      {filters.severity.map((severity) => (
        <Chip
          key={severity}
          label={`Criticidade: ${SEVERITY_LABELS[severity]}`}
          onRemove={() => update((f) => ({ severity: toggle(f.severity, severity) }))}
        />
      ))}
      {filters.category.map((category) => (
        <Chip
          key={category}
          label={CATEGORY_LABELS[category]}
          onRemove={() => update((f) => ({ category: toggle(f.category, category) }))}
        />
      ))}
      {filters.mine && <Chip label="Meus incidentes" onRemove={() => update(() => ({ mine: false }))} />}
      {!statusIsDefault && (
        <Chip
          label={`Status: ${filters.status.map((s) => STATUS_LABELS[s]).join(', ')}`}
          onRemove={() => update(() => ({ status: DEFAULT_STATUSES }))}
        />
      )}
      {!isDefault && (
        <Button variant="ghost" size="sm" onClick={clear}>
          Limpar filtros
        </Button>
      )}

      {shown !== undefined && total !== undefined && (
        <span className="ml-auto text-xs text-text-subtle tabular-nums">
          {shown < total ? `Mostrando ${shown} de ${total}` : `${total} incidente${total === 1 ? '' : 's'}`}
        </span>
      )}
    </div>
  )
}
