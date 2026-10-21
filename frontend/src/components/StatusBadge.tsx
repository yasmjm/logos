import { CircleCheck, CircleDot, CircleHelp, Search, type LucideIcon } from 'lucide-react'

import type { IncidentStatus } from '@/api/types'
import { STATUS_LABELS } from '@/lib/labels'
import { cn } from '@/lib/utils'

const STYLES: Record<IncidentStatus, { icon: LucideIcon; className: string }> = {
  open: { icon: CircleDot, className: 'text-status-open' },
  investigating: { icon: Search, className: 'text-status-investigating' },
  closed: { icon: CircleCheck, className: 'text-status-closed' },
  inconclusive: { icon: CircleHelp, className: 'text-status-inconclusive' },
}

export function StatusBadge({ status, className }: { status: IncidentStatus; className?: string }) {
  const { icon: Icon, className: tone } = STYLES[status]
  return (
    <span className={cn('inline-flex items-center gap-1 text-xs font-medium', tone, className)}>
      <Icon aria-hidden className="size-3.5" />
      {STATUS_LABELS[status]}
    </span>
  )
}
