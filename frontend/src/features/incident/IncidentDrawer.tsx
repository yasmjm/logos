import { LoaderCircle, SearchX } from 'lucide-react'
import { useEffect, useRef, useState } from 'react'

import type { IncidentDetail } from '@/api/types'
import { SeverityBadge } from '@/components/SeverityBadge'
import { StatusBadge } from '@/components/StatusBadge'
import { Button } from '@/components/ui/button'
import { Sheet, SheetContent, SheetDescription, SheetHeader, SheetTitle } from '@/components/ui/sheet'
import { ActionPanel } from '@/features/incident/ActionPanel'
import { ArchiveDialog, ConflictDialog, InconclusiveDialog } from '@/features/incident/Dialogs'
import { EditForm } from '@/features/incident/EditForm'
import { IncidentFacts } from '@/features/incident/IncidentFacts'
import { PriorityExplanation } from '@/features/incident/PriorityExplanation'
import { Timeline } from '@/features/incident/Timeline'
import { type ActionKind, useIncidentActions } from '@/features/incident/useIncidentActions'
import { useIncidentDetail } from '@/features/incident/useIncidentDetail'
import { CATEGORY_LABELS } from '@/lib/labels'

type Mode = 'view' | 'edit' | 'inconclusive' | 'archive'

export function IncidentDrawer({
  incidentId,
  myId,
  onClose,
}: {
  incidentId: string | null
  myId: string
  onClose: (id: string | null) => void
}) {
  // The URL clears incidentId as soon as the panel starts closing; remember which row
  // to return focus to when the close animation ends.
  const lastOpenedId = useRef<string | null>(null)
  useEffect(() => {
    if (incidentId) lastOpenedId.current = incidentId
  }, [incidentId])

  return (
    <Sheet open={incidentId !== null} onOpenChange={(open) => !open && onClose(incidentId)}>
      <SheetContent
        side="right"
        // Modal (focus stays in the panel) but without dimming: the queue stays visible.
        overlayClassName="bg-transparent supports-backdrop-filter:backdrop-blur-none"
        className="w-full gap-0 border-border-strong bg-surface-1 p-0 sm:max-w-[520px]"
        onCloseAutoFocus={(event) => {
          // Focus goes back to the queue row this panel was opened from.
          const id = lastOpenedId.current
          const row = id && document.querySelector<HTMLElement>(`[data-incident-id="${id}"]`)
          if (row) {
            event.preventDefault()
            row.focus()
          }
        }}
      >
        {incidentId && <DrawerBody key={incidentId} incidentId={incidentId} myId={myId} onClose={() => onClose(incidentId)} />}
      </SheetContent>
    </Sheet>
  )
}

function DrawerBody({ incidentId, myId, onClose }: { incidentId: string; myId: string; onClose: () => void }) {
  const [mode, setMode] = useState<Mode>('view')
  // Frozen copy taken when editing or a dialog starts: its version is the one sent.
  const [snapshot, setSnapshot] = useState<IncidentDetail | null>(null)
  const frozen = mode !== 'view'
  const detail = useIncidentDetail(incidentId, frozen)
  const actions = useIncidentActions(incidentId, myId, {
    onArchived: onClose,
    onDone: () => {
      setMode('view')
      setSnapshot(null)
    },
  })

  const incident = detail.data
  const shown = frozen && snapshot ? snapshot : incident

  function begin(next: Mode) {
    if (!incident) return
    actions.clearFailure()
    setSnapshot(incident)
    setMode(next)
  }
  function cancel() {
    setMode('view')
    setSnapshot(null)
  }
  function run(kind: ActionKind, extra: { note?: string } = {}) {
    if (!incident) return
    actions.run({ kind, version: incident.version, ...extra })
  }

  if (!shown) {
    if (detail.isError) {
      return (
        <div className="flex flex-col items-center gap-2 p-8 text-center">
          <SearchX aria-hidden className="size-6 text-text-muted" />
          <SheetTitle className="text-base">Incidente não encontrado</SheetTitle>
          <SheetDescription>Ele pode ter sido arquivado ou o link está incorreto.</SheetDescription>
          <Button variant="outline" size="sm" onClick={onClose}>
            Fechar
          </Button>
        </div>
      )
    }
    return (
      <div className="flex items-center gap-2 p-6 text-text-muted" role="status">
        <LoaderCircle aria-hidden className="size-4 animate-spin" />
        <SheetTitle className="text-sm font-normal">Carregando incidente…</SheetTitle>
        <SheetDescription className="sr-only">Buscando os dados do incidente.</SheetDescription>
      </div>
    )
  }

  return (
    <>
      <SheetHeader className="gap-2 border-b px-5 pt-5 pb-4">
        <div className="flex flex-wrap items-center gap-2 pr-8">
          <SeverityBadge severity={shown.severity} />
          <StatusBadge status={shown.status} />
        </div>
        <SheetTitle className="text-lg leading-tight">{CATEGORY_LABELS[shown.category]}</SheetTitle>
        <SheetDescription className="font-mono text-xs">
          {shown.truck_code} · v{shown.version}
        </SheetDescription>
      </SheetHeader>

      <div className="grid flex-1 content-start gap-6 overflow-y-auto px-5 py-4">
        {mode === 'edit' && snapshot ? (
          <EditForm
            snapshot={snapshot}
            saving={actions.pending === 'edit'}
            onSave={(changes) => actions.run({ kind: 'edit', version: snapshot.version, changes })}
            onCancel={cancel}
          />
        ) : (
          <ActionPanel
            incident={shown}
            myId={myId}
            pending={actions.pending}
            failure={actions.failure}
            onAction={(kind) => run(kind)}
            onEdit={() => begin('edit')}
            onInconclusive={() => begin('inconclusive')}
            onArchive={() => begin('archive')}
          />
        )}
        {mode === 'edit' && actions.failure && (
          <p role="alert" className="text-sm text-danger">
            {actions.failure.message}
          </p>
        )}

        <PriorityExplanation incident={shown} />
        <IncidentFacts incident={shown} />
        <Timeline incident={shown} />
      </div>

      <InconclusiveDialog
        open={mode === 'inconclusive'}
        saving={actions.pending === 'inconclusive'}
        error={mode === 'inconclusive' ? (actions.failure?.message ?? null) : null}
        onConfirm={(note) => snapshot && actions.run({ kind: 'inconclusive', version: snapshot.version, note })}
        onCancel={cancel}
      />
      <ArchiveDialog
        open={mode === 'archive'}
        saving={actions.pending === 'archive'}
        onConfirm={() => snapshot && actions.run({ kind: 'archive', version: snapshot.version })}
        onCancel={cancel}
      />
      <ConflictDialog current={actions.conflict} onSeeCurrent={actions.seeCurrentState} />
    </>
  )
}
