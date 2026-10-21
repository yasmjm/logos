import type { AnalystRef } from '@/api/types'
import { initials } from '@/lib/initials'
import { cn } from '@/lib/utils'

/** Owner of an incident: initials chip plus a name ("Você" when it is the viewer).
 *  Pair with the `.incident-assigned` row style (index.css) in the queue. */
export function AssigneeBadge({
  analyst,
  isMe = false,
  compact = false,
  className,
  nameClassName,
}: {
  analyst: AnalystRef
  isMe?: boolean
  compact?: boolean
  className?: string
  nameClassName?: string
}) {
  const label = isMe ? 'Você' : analyst.name
  return (
    <span
      className={cn('inline-flex min-w-0 items-center gap-1.5 text-xs', className)}
      title={`Responsável: ${isMe ? `você (${analyst.name})` : analyst.name}`}
    >
      <span
        aria-hidden
        className={cn(
          'inline-flex size-5 shrink-0 items-center justify-center rounded-full border text-[10px] font-semibold',
          isMe
            ? 'border-primary bg-primary text-primary-foreground'
            : 'border-assignee-border bg-assignee text-assignee-foreground',
        )}
      >
        {initials(analyst.name)}
      </span>
      {compact ? (
        <span className="sr-only">Responsável: {label}</span>
      ) : (
        <span className={cn('truncate', isMe && 'font-semibold text-text', nameClassName)}>
          {label}
        </span>
      )}
    </span>
  )
}
