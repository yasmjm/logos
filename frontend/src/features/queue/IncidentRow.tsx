import { MapPinOff, MessageCircle, Siren } from 'lucide-react'
import { forwardRef, type KeyboardEvent } from 'react'

import type { Incident } from '@/api/types'
import { AssigneeBadge } from '@/components/AssigneeBadge'
import { CategoryLabel } from '@/components/CategoryLabel'
import { SeverityBadge } from '@/components/SeverityBadge'
import { StatusBadge } from '@/components/StatusBadge'
import { Tooltip, TooltipContent, TooltipTrigger } from '@/components/ui/tooltip'
import { TimingCell } from '@/features/queue/TimingCell'
import { unownedMinutes } from '@/features/queue/sla'
import { formatLocation } from '@/lib/format'
import { cn } from '@/lib/utils'

interface IncidentRowProps {
  incident: Incident
  now: number
  myId: string
  selected: boolean
  arrived: boolean
  tabbable: boolean
  onSelect: () => void
  onKeyDown: (event: KeyboardEvent<HTMLDivElement>) => void
  onFocus: () => void
}

function Location({ incident }: { incident: Incident }) {
  const location = formatLocation(incident.highway, incident.km)
  if (location) {
    return (
      <span className="truncate font-mono text-xs" title={incident.location_note ?? undefined}>
        {location}
      </span>
    )
  }
  return (
    <span
      className="inline-flex min-w-0 items-center gap-1 text-xs text-text-subtle italic"
      title={incident.location_note ?? 'O relato não trouxe rodovia nem km.'}
    >
      <MapPinOff aria-hidden className="size-3.5 shrink-0" />
      <span className="truncate">Localização não informada</span>
    </span>
  )
}

function WhatsAppBadge({ className, iconOnlyBelowSm = false }: { className?: string; iconOnlyBelowSm?: boolean }) {
  return (
    <span
      title="Relato recebido pelo WhatsApp"
      className={cn(
        'inline-flex shrink-0 items-center gap-1 rounded-sm border border-border-strong px-1 py-px text-[11px] font-medium text-text-muted',
        className,
      )}
    >
      <MessageCircle aria-hidden className="size-3" />
      <span className={iconOnlyBelowSm ? 'sr-only sm:not-sr-only' : undefined}>WhatsApp</span>
    </span>
  )
}

function UnownedBadge({ minutes, className }: { minutes: number; className?: string }) {
  return (
    <span
      className={cn(
        'inline-flex shrink-0 items-center gap-1 rounded-sm bg-sev-high px-1.5 py-px text-[11px] font-semibold text-white dark:text-black',
        className,
      )}
    >
      <Siren aria-hidden className="size-3" />
      Sem dono há {minutes} min
    </span>
  )
}

export const IncidentRow = forwardRef<HTMLDivElement, IncidentRowProps>(function IncidentRow(
  { incident, now, myId, selected, arrived, tabbable, onSelect, onKeyDown, onFocus },
  ref,
) {
  const unowned = unownedMinutes(incident, now)
  const isMine = incident.assignee?.id === myId
  const whatsapp = incident.source === 'whatsapp'

  return (
    <div
      ref={ref}
      role="row"
      tabIndex={tabbable ? 0 : -1}
      aria-selected={selected}
      data-incident-id={incident.id}
      data-escalated={unowned !== null}
      data-arrived={arrived}
      onClick={onSelect}
      onKeyDown={onKeyDown}
      onFocus={onFocus}
      className={cn(
        'queue-row cursor-pointer border-b text-sm hover:bg-surface-2',
        incident.assignee && !selected && 'incident-assigned',
      )}
    >
      <div role="gridcell" data-area="sev">
        <SeverityBadge severity={incident.severity} />
      </div>

      <div role="gridcell" data-area="cat" className="hidden min-w-0 md:flex">
        <CategoryLabel category={incident.category} labelClassName="hidden xl:inline" />
      </div>

      <div role="gridcell" data-area="desc" className="flex min-w-0 items-center gap-2 overflow-hidden">
        {unowned !== null && <UnownedBadge minutes={unowned} className="hidden md:inline-flex" />}
        {whatsapp && <WhatsAppBadge className="xl:hidden" iconOnlyBelowSm />}
        <Tooltip>
          <TooltipTrigger asChild>
            <span className="truncate text-text">{incident.description}</span>
          </TooltipTrigger>
          <TooltipContent side="bottom" align="start" className="max-w-md">
            {incident.description}
          </TooltipContent>
        </Tooltip>
      </div>

      <div role="gridcell" data-area="truck" className="hidden font-mono text-xs lg:block">
        {incident.truck_code}
      </div>

      <div role="gridcell" data-area="loc" className="hidden md:flex">
        <Location incident={incident} />
      </div>

      <div role="gridcell" data-area="time" className="text-xs">
        <TimingCell incident={incident} now={now} />
      </div>

      <div role="gridcell" data-area="src" className="hidden xl:block">
        {whatsapp ? <WhatsAppBadge /> : <span className="sr-only">Integração</span>}
      </div>

      <div role="gridcell" data-area="owner" className="hidden md:flex">
        {incident.assignee ? (
          <AssigneeBadge analyst={incident.assignee} isMe={isMine} nameClassName="hidden lg:inline" />
        ) : (
          <span className="text-xs text-text-subtle">
            <span aria-hidden>—</span>
            <span className="sr-only">Sem responsável</span>
          </span>
        )}
      </div>

      <div role="gridcell" data-area="status" className="hidden md:block">
        <StatusBadge status={incident.status} />
      </div>

      {/* Narrow screens: secondary data on a second line. */}
      <div
        role="gridcell"
        data-area="meta"
        className="flex min-w-0 items-center gap-1.5 overflow-hidden text-xs text-text-muted md:hidden"
      >
        {unowned !== null && <UnownedBadge minutes={unowned} />}
        <span className="shrink-0 font-mono">{incident.truck_code}</span>
        <span aria-hidden>·</span>
        <span className="min-w-0 truncate">
          <Location incident={incident} />
        </span>
        {/* "Sem dono" already says it is open; keep the line short on phones. */}
        {unowned === null && <StatusBadge status={incident.status} className="ml-auto shrink-0" />}
        {incident.assignee && (
          <AssigneeBadge analyst={incident.assignee} isMe={isMine} compact className="shrink-0" />
        )}
      </div>
    </div>
  )
})
