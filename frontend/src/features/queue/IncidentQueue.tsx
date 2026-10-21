import { type KeyboardEvent, useRef, useState } from 'react'

import type { Incident } from '@/api/types'
import { IncidentRow } from '@/features/queue/IncidentRow'
import { useNow } from '@/lib/useNow'

const HEADERS = [
  { area: 'sev', label: 'Criticidade', className: '' },
  { area: 'cat', label: 'Categoria', className: 'xl:visible invisible' },
  { area: 'desc', label: 'Descrição', className: '' },
  { area: 'truck', label: 'Caminhão', className: 'hidden lg:block' },
  { area: 'loc', label: 'Localização', className: '' },
  { area: 'time', label: 'Tempo', className: '' },
  { area: 'src', label: 'Origem', className: 'hidden xl:block' },
  { area: 'owner', label: 'Responsável', className: 'invisible lg:visible' },
  { area: 'status', label: 'Status', className: '' },
] as const

/** Keyboard: Tab enters the queue, arrows/Home/End move, Enter or Space selects. */
export function IncidentQueue({
  incidents,
  myId,
  selectedId,
  arrivedIds,
  onSelect,
}: {
  incidents: Incident[]
  myId: string
  selectedId: string | null
  arrivedIds: ReadonlySet<string>
  onSelect: (id: string) => void
}) {
  const now = useNow()
  const rows = useRef(new Map<string, HTMLDivElement>())
  const [activeId, setActiveId] = useState<string | null>(null)

  // One row is tabbable (roving tabindex): the focused one, else the selected, else the first.
  const tabbableId =
    [activeId, selectedId].find((id) => id && incidents.some((i) => i.id === id)) ??
    incidents[0]?.id

  function focusAt(index: number) {
    const target = incidents[Math.max(0, Math.min(index, incidents.length - 1))]
    if (target) rows.current.get(target.id)?.focus()
  }

  function onKeyDown(event: KeyboardEvent<HTMLDivElement>, index: number, id: string) {
    const moves: Record<string, number> = {
      ArrowDown: index + 1,
      ArrowUp: index - 1,
      Home: 0,
      End: incidents.length - 1,
      PageDown: index + 10,
      PageUp: index - 10,
    }
    if (event.key in moves) {
      event.preventDefault()
      focusAt(moves[event.key]!)
    } else if (event.key === 'Enter' || event.key === ' ') {
      event.preventDefault()
      onSelect(id)
    }
  }

  return (
    <div role="grid" aria-label="Fila de incidentes" aria-rowcount={incidents.length + 1}>
      <div
        role="row"
        className="queue-row sticky top-12 z-[5] hidden border-b bg-surface-1 text-xs font-medium text-text-subtle md:grid"
      >
        {HEADERS.map((header) => (
          <div
            key={header.area}
            role="columnheader"
            data-area={header.area}
            className={header.className}
          >
            {header.label}
          </div>
        ))}
      </div>
      {incidents.map((incident, index) => (
        <IncidentRow
          key={incident.id}
          ref={(node) => {
            if (node) rows.current.set(incident.id, node)
            else rows.current.delete(incident.id)
          }}
          incident={incident}
          now={now}
          myId={myId}
          selected={incident.id === selectedId}
          arrived={arrivedIds.has(incident.id)}
          tabbable={incident.id === tabbableId}
          onSelect={() => onSelect(incident.id)}
          onFocus={() => setActiveId(incident.id)}
          onKeyDown={(event) => onKeyDown(event, index, incident.id)}
        />
      ))}
    </div>
  )
}
