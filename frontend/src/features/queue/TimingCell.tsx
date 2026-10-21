import { CircleCheck, Clock, TriangleAlert, UserCheck } from 'lucide-react'

import type { Incident } from '@/api/types'
import { SLA_MINUTES, timing } from '@/features/queue/sla'
import { formatDuration } from '@/lib/format'
import { cn } from '@/lib/utils'

/** Time open with the SLA: neutral within it, amber near it, red past it.
 *  Owned incidents show how long they took to be assumed, without alerts. */
export function TimingCell({ incident, now }: { incident: Incident; now: number }) {
  const state = timing(incident, now)
  const duration = formatDuration(state.elapsedMs)

  if (state.kind === 'resolved') {
    return (
      <span className="inline-flex items-center gap-1 text-text-subtle" title={`Resolvido em ${duration}`}>
        <CircleCheck aria-hidden className="size-3.5" />
        {duration}
        <span className="sr-only"> até a resolução</span>
      </span>
    )
  }
  if (state.kind === 'assumed') {
    return (
      <span className="inline-flex items-center gap-1 text-text-subtle" title={`Assumido em ${duration}`}>
        <UserCheck aria-hidden className="size-3.5" />
        {duration}
        <span className="sr-only"> até ser assumido</span>
      </span>
    )
  }

  const sla = SLA_MINUTES[incident.severity]
  const label = {
    ok: `Em aberto há ${duration} (prazo: ${sla} min)`,
    near: `Perto do prazo de ${sla} min: em aberto há ${duration}`,
    breached: `Prazo de ${sla} min estourado: em aberto há ${duration}`,
  }[state.level]
  return (
    <span
      title={label}
      className={cn(
        'inline-flex items-center gap-1 font-medium',
        state.level === 'ok' && 'text-text-muted',
        state.level === 'near' && 'text-sev-medium',
        state.level === 'breached' && 'text-sev-high',
      )}
    >
      {state.level === 'breached' ? (
        <TriangleAlert aria-hidden className="size-3.5" />
      ) : (
        <Clock aria-hidden className="size-3.5" />
      )}
      {duration}
      <span className="sr-only">{` — ${label}`}</span>
    </span>
  )
}
