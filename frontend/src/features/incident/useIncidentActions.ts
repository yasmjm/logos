import { useMutation, useQueryClient } from '@tanstack/react-query'
import { useState } from 'react'
import { toast } from 'sonner'

import { archiveIncident, changeStatus, updateIncident } from '@/api/incidents'
import { ApiError, isRetryable } from '@/api/errors'
import type { IncidentDetail, IncidentStatus, IncidentUpdate } from '@/api/types'
import { lastChange } from '@/features/incident/eventText'
import { detailKey } from '@/features/incident/useIncidentDetail'

export type ActionKind = 'assume' | 'close' | 'inconclusive' | 'release' | 'reopen' | 'edit' | 'archive'

export interface ActionRequest {
  kind: ActionKind
  /** The version the analyst is looking at (or the one frozen when editing began). */
  version: number
  note?: string
  changes?: Omit<IncidentUpdate, 'version'>
}

const TARGET_STATUS: Partial<Record<ActionKind, IncidentStatus>> = {
  assume: 'investigating',
  close: 'closed',
  inconclusive: 'inconclusive',
  release: 'open',
  reopen: 'open',
}

export const PENDING_LABEL: Record<ActionKind, string> = {
  assume: 'Assumindo…',
  close: 'Fechando…',
  inconclusive: 'Salvando…',
  release: 'Liberando…',
  reopen: 'Reabrindo…',
  edit: 'Salvando…',
  archive: 'Arquivando…',
}

const SUCCESS_TOAST: Record<ActionKind, string> = {
  assume: 'Incidente assumido',
  close: 'Incidente fechado',
  inconclusive: 'Incidente marcado como inconclusivo',
  release: 'Incidente liberado',
  reopen: 'Incidente reaberto',
  edit: 'Alterações salvas',
  archive: 'Incidente arquivado',
}

export interface ActionFailure {
  message: string
  /** Only for failures where nothing could have been applied twice (see below). */
  retry?: () => void
}

/**
 * Status changes, edits and archiving. No optimistic update and no automatic retry:
 * these are the actions most likely to conflict, and "assumed ✓" turning back into
 * "open" would confuse the analyst. The API's answer is the confirmation.
 */
export function useIncidentActions(
  incidentId: string,
  myId: string,
  callbacks: { onArchived: () => void; onDone: () => void },
) {
  const queryClient = useQueryClient()
  const [failure, setFailure] = useState<ActionFailure | null>(null)
  const [conflict, setConflict] = useState<IncidentDetail | null>(null)

  const refresh = (detail?: IncidentDetail) => {
    if (detail) queryClient.setQueryData(detailKey(incidentId), detail)
    // List, KPIs, "my incidents" and the detail itself.
    void queryClient.invalidateQueries({ queryKey: ['incidents'] })
  }

  const mutation = useMutation<IncidentDetail | void, unknown, ActionRequest>({
    retry: false, // the analyst decides; a repeat after a lost answer gets 409, never a duplicate
    mutationFn: ({ kind, version, note, changes }) => {
      if (kind === 'archive') return archiveIncident(incidentId)
      if (kind === 'edit') return updateIncident(incidentId, { version, ...changes })
      return changeStatus(incidentId, { status: TARGET_STATUS[kind]!, version, note })
    },
    onMutate: () => {
      setFailure(null)
      setConflict(null)
    },
    onSuccess: (result, request) => {
      toast.success(SUCCESS_TOAST[request.kind])
      if (request.kind === 'archive') {
        void queryClient.invalidateQueries({ queryKey: ['incidents'] })
        callbacks.onArchived()
        return
      }
      refresh(result || undefined)
      callbacks.onDone()
    },
    onError: (error, request) => {
      if (error instanceof ApiError && error.status === 409) {
        const current = error.current
        if (current && lastChange(current)?.analyst?.id === myId) {
          // Our previous attempt did reach the API (its answer was lost): already done.
          toast.info('Sua ação anterior já tinha sido aplicada')
          refresh(current)
          callbacks.onDone()
          return
        }
        if (current) {
          setConflict(current)
          return
        }
      }
      setFailure(describeFailure(error, () => mutation.mutate(request)))
    },
  })

  function seeCurrentState() {
    if (conflict) refresh(conflict)
    setConflict(null)
    callbacks.onDone()
  }

  return {
    run: (request: ActionRequest) => mutation.mutate(request),
    pending: mutation.isPending ? (mutation.variables?.kind ?? null) : null,
    failure,
    clearFailure: () => setFailure(null),
    conflict,
    seeCurrentState,
  }
}

function describeFailure(error: unknown, retry: () => void): ActionFailure {
  if (error instanceof ApiError) {
    if (error.status === 403) {
      const owner = error.body?.assignee?.name
      return {
        message: owner
          ? `Só ${owner}, responsável por este incidente, pode mudar o status dele.`
          : error.detail,
      }
    }
    if (error.status === 404) return { message: 'Este incidente não existe mais ou foi arquivado.' }
    if (error.status === 422) return { message: error.detail }
  }
  if (isRetryable(error)) {
    // Safe to retry: if the first attempt did arrive, the repeat answers 409 instead
    // of applying the change twice (optimistic locking, ADR 0002).
    return { message: 'Não foi possível salvar. Nada foi alterado.', retry }
  }
  return { message: 'Algo deu errado ao salvar. Tente de novo em instantes.' }
}
