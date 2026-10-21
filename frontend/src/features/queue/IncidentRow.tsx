import { MapPinOff, Siren } from 'lucide-react'
import { forwardRef, type KeyboardEvent } from 'react'

import type { Incident } from '@/api/types'
import { AssigneeBadge } from '@/components/AssigneeBadge'
import { SourceBadge } from '@/components/SourceBadge'
import { ImpactMarkers } from '@/components/ImpactMarkers'
import { CategoryLabel } from '@/components/CategoryLabel'
import { SeverityBadge } from '@/components/SeverityBadge'
import { StatusBadge } from '@/components/StatusBadge'
import { Tooltip, TooltipContent, TooltipTrigger } from '@/components/ui/tooltip'
import { ScoreCell } from '@/features/queue/ScoreCell'
import { TimingCell } from '@/features/queue/TimingCell'
import { type SlaRules, unownedMinutes } from '@/features/queue/sla'
import { formatLocation } from '@/lib/format'
import { cn } from '@/lib/utils'

interface IncidentRowProps {
  incident: Incident
  now: number
  rules: SlaRules | undefined
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
  { incident, now, rules, myId, selected, arrived, tabbable, onSelect, onKeyDown, onFocus },
  ref,
) {
  const unowned = unownedMinutes(incident, now, rules)
  const isMine = incident.assignee?.id === myId
  const reported = incident.source !== 'api' // WhatsApp or manual: worth a badge

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
      <div role="gridcell" data-area="score" className="hidden md:block">
        <ScoreCell incident={incident} />
      </div>

      <div role="gridcell" data-area="sev" className="flex flex-col items-start gap-1">
        <SeverityBadge severity={incident.severity} />
        {/* Phones: the score sits under the severity, where desktop shows its own column. */}
        <span className="pl-1 md:hidden">
          <ScoreCell incident={incident} />
        </span>
      </div>

      <div role="gridcell" data-area="cat" className="hidden min-w-0 md:flex">
        <CategoryLabel category={incident.category} labelClassName="hidden xl:inline" />
      </div>

      <div role="gridcell" data-area="desc" className="flex min-w-0 items-center gap-2 overflow-hidden">
        {unowned !== null && <UnownedBadge minutes={unowned} className="hidden md:inline-flex" />}
        {reported && <SourceBadge source={incident.source} className="xl:hidden" iconOnlyBelowSm />}
        <Tooltip>
          <TooltipTrigger asChild>
            <span className="truncate text-text">{incident.description}</span>
          </TooltipTrigger>
          <TooltipContent side="bottom" align="start" className="max-w-md">
            {incident.description}
          </TooltipContent>
        </Tooltip>
      </div>

      <div role="gridcell" data-area="impact" className="hidden md:flex">
        <ImpactMarkers incident={incident} />
      </div>

      <div role="gridcell" data-area="truck" className="hidden font-mono text-xs lg:block">
        {incident.truck_code}
      </div>

      <div role="gridcell" data-area="loc" className="hidden md:flex">
        <Location incident={incident} />
      </div>

      <div role="gridcell" data-area="time" className="text-xs">
        <TimingCell incident={incident} now={now} rules={rules} />
      </div>

      <div role="gridcell" data-area="src" className="hidden xl:block">
        <SourceBadge source={incident.source} />
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
        <ImpactMarkers incident={incident} className="shrink-0" />
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
