import { Siren } from 'lucide-react'

import { useAppConfig } from '@/api/appConfig'
import type { Incident } from '@/api/types'
import { Tooltip, TooltipContent, TooltipTrigger } from '@/components/ui/tooltip'
import { priorityFormula } from '@/lib/priorityText'

/** Priority score (or the max-priority marker for victims), explained in a tooltip. */
export function ScoreCell({ incident }: { incident: Incident }) {
  const weights = useAppConfig().data?.priority.weights
  const victims = incident.priority_breakdown.victims
  const formula = priorityFormula(incident, weights)

  return (
    <Tooltip>
      <TooltipTrigger asChild>
        <span className="inline-flex items-center font-mono text-xs font-semibold tabular-nums text-text">
          {victims ? (
            <Siren aria-hidden className="size-4 text-sev-high" strokeWidth={2.25} />
          ) : (
            <span aria-hidden>{incident.priority_score}</span>
          )}
          <span className="sr-only">
            {victims ? 'Prioridade máxima: há vítimas' : `Prioridade ${incident.priority_score}`}
          </span>
        </span>
      </TooltipTrigger>
      <TooltipContent side="right" className="max-w-sm">
        <div className="grid gap-0.5">
          <p className="font-semibold">Por que está nesta posição</p>
          <p>{formula}</p>
        </div>
      </TooltipContent>
    </Tooltip>
  )
}
