import { Archive, CircleAlert, Lock, Pencil, RotateCw } from 'lucide-react'
import type { ReactNode } from 'react'

import type { IncidentDetail } from '@/api/types'
import { Alert, AlertDescription } from '@/components/ui/alert'
import { Button } from '@/components/ui/button'
import { type ActionFailure, type ActionKind, PENDING_LABEL } from '@/features/incident/useIncidentActions'
import { formatClock } from '@/lib/format'

/** When the current owner took the incident (last move to investigating). */
function investigatingSince(incident: IncidentDetail): string | null {
  const taken = [...incident.events]
    .reverse()
    .find((e) => e.event_type === 'status_changed' && e.to_status === 'investigating')
  const at = taken?.created_at ?? incident.acknowledged_at
  return at ? formatClock(at) : null
}

export function ActionPanel({
  incident,
  myId,
  pending,
  failure,
  onAction,
  onEdit,
  onInconclusive,
  onArchive,
}: {
  incident: IncidentDetail
  myId: string
  pending: ActionKind | null
  failure: ActionFailure | null
  onAction: (kind: ActionKind) => void
  onEdit: () => void
  onInconclusive: () => void
  onArchive: () => void
}) {
  const busy = pending !== null
  const mine = incident.assignee?.id === myId
  const editable = incident.status === 'open' || incident.status === 'investigating'

  const action = (kind: ActionKind, label: string, variant: 'default' | 'outline' = 'outline', onClick?: () => void): ReactNode => (
    <Button key={kind} variant={variant} disabled={busy} onClick={onClick ?? (() => onAction(kind))}>
      {pending === kind ? PENDING_LABEL[kind] : label}
    </Button>
  )

  let main: ReactNode
  if (incident.status === 'open') {
    main = action('assume', 'Assumir', 'default')
  } else if (incident.status === 'investigating' && mine) {
    main = (
      <>
        {action('close', 'Fechar', 'default')}
        {action('inconclusive', 'Marcar como inconclusivo', 'outline', onInconclusive)}
        {action('release', 'Liberar')}
      </>
    )
  } else if (incident.status === 'investigating') {
    const since = investigatingSince(incident)
    main = (
      <p className="flex items-center gap-2 rounded-md border bg-surface-2 px-3 py-2 text-sm text-text-muted">
        <Lock aria-hidden className="size-4 shrink-0" />
        <span>
          Em investigação por <strong className="text-text">{incident.assignee?.name}</strong>
          {since ? ` desde ${since}` : ''}. Só o responsável pode mudar o status.
        </span>
      </p>
    )
  } else {
    main = action('reopen', 'Reabrir', 'default')
  }

  return (
    <section aria-label="Ações" className="grid gap-2">
      <div className="flex flex-wrap gap-2">{main}</div>
      <div className="flex flex-wrap gap-2">
        {editable && (
          <Button variant="ghost" size="sm" disabled={busy} onClick={onEdit}>
            <Pencil aria-hidden />
            Editar
          </Button>
        )}
        <Button variant="ghost" size="sm" disabled={busy} onClick={onArchive}>
          <Archive aria-hidden />
          Arquivar
        </Button>
      </div>
      {failure && (
        <Alert variant="destructive" role="alert">
          <CircleAlert aria-hidden />
          <AlertDescription className="flex flex-wrap items-center gap-2">
            <span>{failure.message}</span>
            {failure.retry && (
              <Button variant="outline" size="xs" onClick={failure.retry} disabled={busy}>
                <RotateCw aria-hidden />
                Tentar de novo
              </Button>
            )}
          </AlertDescription>
        </Alert>
      )}
    </section>
  )
}
