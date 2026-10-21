import { type FormEvent, useState } from 'react'

import type { IncidentDetail } from '@/api/types'
import {
  AlertDialog,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
} from '@/components/ui/alert-dialog'
import { Button } from '@/components/ui/button'
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog'
import { Label } from '@/components/ui/label'
import { StatusBadge } from '@/components/StatusBadge'
import { Textarea } from '@/components/ui/textarea'
import { describeStatusChange, lastChange } from '@/features/incident/eventText'
import { formatAgo } from '@/lib/format'
import { STATUS_LABELS } from '@/lib/labels'
import { useNow } from '@/lib/useNow'

const NOTE_MIN = 10

export function InconclusiveDialog({
  open,
  saving,
  error,
  onConfirm,
  onCancel,
}: {
  open: boolean
  saving: boolean
  error: string | null
  onConfirm: (note: string) => void
  onCancel: () => void
}) {
  const [note, setNote] = useState('')
  const length = note.trim().length

  function submit(event: FormEvent) {
    event.preventDefault()
    if (length >= NOTE_MIN) onConfirm(note.trim())
  }

  return (
    <Dialog open={open} onOpenChange={(next) => !next && !saving && onCancel()}>
      <DialogContent>
        <form onSubmit={submit} className="grid gap-4">
          <DialogHeader>
            <DialogTitle>Marcar como inconclusivo</DialogTitle>
            <DialogDescription>
              Explique por que não foi possível concluir. O motivo fica registrado na linha do tempo.
            </DialogDescription>
          </DialogHeader>
          <div className="grid gap-1.5">
            <Label htmlFor="inconclusive-note">Motivo</Label>
            <Textarea
              id="inconclusive-note"
              value={note}
              onChange={(e) => setNote(e.target.value)}
              rows={4}
              autoFocus
              aria-invalid={error !== null || undefined}
              aria-describedby="inconclusive-help"
              placeholder="Ex.: motorista não atendeu e o rastreador está offline."
            />
            <p id="inconclusive-help" className="text-xs text-text-subtle tabular-nums">
              {length < NOTE_MIN
                ? `Mínimo de ${NOTE_MIN} caracteres (faltam ${NOTE_MIN - length}).`
                : `${length} caracteres`}
            </p>
            {error && (
              <p role="alert" className="text-xs text-danger">
                {error}
              </p>
            )}
          </div>
          <DialogFooter>
            <Button type="button" variant="ghost" onClick={onCancel} disabled={saving}>
              Cancelar
            </Button>
            <Button type="submit" disabled={saving || length < NOTE_MIN}>
              {saving ? 'Salvando…' : 'Marcar como inconclusivo'}
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  )
}

export function ArchiveDialog({
  open,
  saving,
  onConfirm,
  onCancel,
}: {
  open: boolean
  saving: boolean
  onConfirm: () => void
  onCancel: () => void
}) {
  return (
    <AlertDialog open={open} onOpenChange={(next) => !next && !saving && onCancel()}>
      <AlertDialogContent>
        <AlertDialogHeader>
          <AlertDialogTitle>Arquivar este incidente?</AlertDialogTitle>
          <AlertDialogDescription>
            Ele sai da fila e dos indicadores, mas nada é apagado: o incidente e todo o histórico
            continuam guardados, e fica registrado que você o arquivou.
          </AlertDialogDescription>
        </AlertDialogHeader>
        <AlertDialogFooter>
          <AlertDialogCancel disabled={saving}>Cancelar</AlertDialogCancel>
          {/* A plain button (not AlertDialogAction) so the dialog stays open until the API answers. */}
          <Button variant="destructive" onClick={onConfirm} disabled={saving}>
            {saving ? 'Arquivando…' : 'Arquivar'}
          </Button>
        </AlertDialogFooter>
      </AlertDialogContent>
    </AlertDialog>
  )
}

/** 409: someone changed the incident while you were looking. Never retried for you. */
export function ConflictDialog({
  current,
  onSeeCurrent,
}: {
  current: IncidentDetail | null
  onSeeCurrent: () => void
}) {
  const now = useNow()
  const change = current ? lastChange(current) : undefined
  const ago = change ? formatAgo(now - Date.parse(change.created_at)) : null
  const who = change?.analyst?.name ?? 'Alguém'
  const what =
    change?.event_type === 'status_changed'
      ? describeStatusChange(change.from_status, change.to_status).replace(' o incidente', ' este incidente')
      : change?.event_type === 'updated'
        ? 'editou este incidente'
        : 'alterou este incidente'

  return (
    <AlertDialog open={current !== null}>
      <AlertDialogContent>
        <AlertDialogHeader>
          <AlertDialogTitle>Este incidente mudou enquanto você olhava</AlertDialogTitle>
          <AlertDialogDescription>
            {who} {what}
            {ago ? ` ${ago}` : ''}. Sua ação não foi aplicada.
          </AlertDialogDescription>
        </AlertDialogHeader>
        {current && (
          <div className="flex flex-wrap items-center gap-x-3 gap-y-1 rounded-md border bg-surface-2 px-3 py-2 text-sm">
            <span className="text-text-muted">Agora:</span>
            <StatusBadge status={current.status} />
            {current.assignee && (
              <span className="text-text-muted">
                responsável <strong className="text-text">{current.assignee.name}</strong>
              </span>
            )}
            <span className="sr-only">Status atual: {STATUS_LABELS[current.status]}</span>
          </div>
        )}
        <AlertDialogFooter>
          <Button onClick={onSeeCurrent} autoFocus>
            Ver estado atual
          </Button>
        </AlertDialogFooter>
      </AlertDialogContent>
    </AlertDialog>
  )
}
