import { Flame, Gem, Snowflake, Star, type LucideIcon } from 'lucide-react'

import type { CargoType, Incident } from '@/api/types'
import { Tooltip, TooltipContent, TooltipTrigger } from '@/components/ui/tooltip'
import { CARGO_HINTS, CLIENT_TIER_LABELS } from '@/lib/labels'
import { cn } from '@/lib/utils'

const CARGO_ICONS: Partial<Record<CargoType, { icon: LucideIcon; className: string }>> = {
  hazardous: { icon: Flame, className: 'text-cargo-hazardous' },
  perishable: { icon: Snowflake, className: 'text-cargo-perishable' },
  high_value: { icon: Gem, className: 'text-cargo-high-value' },
}

function Marker({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <Tooltip>
      <TooltipTrigger asChild>
        <span className="inline-flex" tabIndex={-1}>
          {children}
          <span className="sr-only">{label}</span>
        </span>
      </TooltipTrigger>
      <TooltipContent side="top">{label}</TooltipContent>
    </Tooltip>
  )
}

/** Business impact at a glance: special cargo and strategic client (16 px icons). */
export function ImpactMarkers({ incident, className }: { incident: Incident; className?: string }) {
  const cargo = CARGO_ICONS[incident.cargo_type]
  const strategic = incident.client_tier === 'strategic'
  if (!cargo && !strategic) return null

  return (
    <span className={cn('inline-flex items-center gap-1', className)}>
      {cargo && (
        <Marker label={CARGO_HINTS[incident.cargo_type]}>
          <cargo.icon aria-hidden className={cn('size-4', cargo.className)} strokeWidth={2.25} />
        </Marker>
      )}
      {strategic && (
        <Marker label={`${CLIENT_TIER_LABELS.strategic}: ${incident.client_name ?? 'não identificado'}`}>
          <Star aria-hidden className="size-4 fill-current text-client-strategic" />
        </Marker>
      )}
    </span>
  )
}
