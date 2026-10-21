import { Biohazard, Snowflake, Star } from 'lucide-react'

import type { Incident } from '@/api/types'
import { CARGO_HINTS, CLIENT_TIER_LABELS } from '@/lib/labels'
import { cn } from '@/lib/utils'

/** Discreet queue markers: hazardous or perishable cargo, and strategic clients. */
export function CargoBadges({ incident, className }: { incident: Incident; className?: string }) {
  const CargoIcon =
    incident.cargo_type === 'hazardous' ? Biohazard : incident.cargo_type === 'perishable' ? Snowflake : null
  const strategic = incident.client_tier === 'strategic' && incident.client_name
  if (!CargoIcon && !strategic) return null

  return (
    <span className={cn('inline-flex shrink-0 items-center gap-1.5', className)}>
      {CargoIcon && (
        <span className="inline-flex text-text-muted" title={CARGO_HINTS[incident.cargo_type]}>
          <CargoIcon aria-hidden className="size-3.5" />
          <span className="sr-only">{CARGO_HINTS[incident.cargo_type]}</span>
        </span>
      )}
      {strategic && (
        <span
          className="inline-flex max-w-[11rem] items-center gap-1 rounded-sm border border-border-strong px-1 py-px text-[11px] text-text-muted"
          title={`${CLIENT_TIER_LABELS.strategic}: ${incident.client_name}`}
        >
          <Star aria-hidden className="size-3 shrink-0" />
          <span className="truncate">{incident.client_name}</span>
          <span className="sr-only"> ({CLIENT_TIER_LABELS.strategic})</span>
        </span>
      )}
    </span>
  )
}
