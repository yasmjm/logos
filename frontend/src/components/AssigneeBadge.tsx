import type { AnalystRef } from '@/api/types'
import { initials } from '@/lib/initials'
import { cn } from '@/lib/utils'

/** Owner of an incident: initials chip, plus the name unless compact.
 *  Pair with the `.incident-assigned` row style (index.css) in the queue. */
export function AssigneeBadge({
  analyst,
  compact = false,
  className,
}: {
  analyst: AnalystRef
  compact?: boolean
  className?: string
}) {
  return (
    <span
      className={cn('inline-flex items-center gap-1.5 text-xs text-text-muted', className)}
      title={compact ? `Responsável: ${analyst.name}` : undefined}
    >
      <span
        aria-hidden
        className="inline-flex size-5 items-center justify-center rounded-full border border-assignee-border bg-assignee text-[10px] font-semibold text-assignee-foreground"
      >
        {initials(analyst.name)}
      </span>
      {compact ? <span className="sr-only">Responsável: {analyst.name}</span> : analyst.name}
    </span>
  )
}
