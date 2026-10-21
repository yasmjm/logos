import { Headset, MessageCircle, type LucideIcon } from 'lucide-react'

import type { IncidentSource } from '@/api/types'
import { SOURCE_HINTS, SOURCE_LABELS } from '@/lib/labels'
import { cn } from '@/lib/utils'

const ICONS: Partial<Record<IncidentSource, LucideIcon>> = {
  whatsapp: MessageCircle,
  manual: Headset,
}

/** Origin of a report that did not come from an integration (WhatsApp, manual). */
export function SourceBadge({
  source,
  className,
  iconOnlyBelowSm = false,
}: {
  source: IncidentSource
  className?: string
  iconOnlyBelowSm?: boolean
}) {
  const Icon = ICONS[source]
  if (!Icon) return <span className="sr-only">{SOURCE_LABELS[source]}</span>
  return (
    <span
      title={SOURCE_HINTS[source]}
      className={cn(
        'inline-flex shrink-0 items-center gap-1 rounded-sm border border-border-strong px-1 py-px text-[11px] font-medium text-text-muted',
        className,
      )}
    >
      <Icon aria-hidden className="size-3" />
      <span className={iconOnlyBelowSm ? 'sr-only sm:not-sr-only' : undefined}>{SOURCE_LABELS[source]}</span>
    </span>
  )
}
