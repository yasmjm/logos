import { CircleAlert, Gauge, Timer, TimerReset, type LucideIcon } from 'lucide-react'
import type { ReactNode } from 'react'

import { useAppConfig } from '@/api/appConfig'
import type { IncidentMetrics, Severity } from '@/api/types'
import { Tooltip, TooltipContent, TooltipTrigger } from '@/components/ui/tooltip'
import { formatSeconds } from '@/lib/format'
import { SEVERITY_LABELS } from '@/lib/labels'
import { cn } from '@/lib/utils'

function Metric({
  icon: Icon,
  label,
  value,
  hint,
  help,
  alert = false,
}: {
  icon: LucideIcon
  label: string
  value: ReactNode
  hint?: string
  help: string
  alert?: boolean
}) {
  return (
    <Tooltip>
      <TooltipTrigger asChild>
        <div
          tabIndex={0}
          className={cn(
            'flex min-w-0 items-center gap-2 rounded-md border bg-surface-1 px-3 py-1.5 text-xs',
            alert && 'border-sev-high-border bg-sev-high-bg',
          )}
        >
          <Icon aria-hidden className={cn('size-4 shrink-0 text-text-muted', alert && 'text-sev-high')} />
          <span className="text-text-muted">{label}:</span>
          <span className={cn('font-semibold tabular-nums text-text', alert && 'text-sev-high')}>{value}</span>
          {hint && <span className="hidden truncate text-text-subtle lg:inline">{hint}</span>}
          <span className="sr-only">. {help}</span>
        </div>
      </TooltipTrigger>
      <TooltipContent side="bottom" className="max-w-xs">
        {help}
      </TooltipContent>
    </Tooltip>
  )
}

function plural(count: number, one: string, many: string): string {
  return `${count} ${count === 1 ? one : many}`
}

/** Response times and what needs attention right now, in business language. */
export function MetricsStrip({ metrics }: { metrics: IncidentMetrics | undefined }) {
  const hours = metrics?.window_hours ?? 24
  const breached = metrics?.sla_breached_now ?? 0
  const sla = useAppConfig().data?.sla_minutes
  const slaText = sla
    ? ` (${(Object.keys(sla) as Severity[]).map((s) => `${SEVERITY_LABELS[s]} ${sla[s]} min`).join(', ')})`
    : ''
  return (
    <section aria-label="Métricas de resposta" className="grid gap-2 sm:grid-cols-3">
      <Metric
        icon={Timer}
        label={`Tempo médio de reação (${hours} h)`}
        value={metrics?.mtta_seconds != null ? formatSeconds(metrics.mtta_seconds) : '—'}
        hint={metrics ? `(${plural(metrics.mtta_count, 'incidente', 'incidentes')})` : undefined}
        help={`Do recebimento até alguém assumir, em média, para os incidentes assumidos nas últimas ${hours} horas (MTTA).`}
      />
      <Metric
        icon={TimerReset}
        label={`Tempo médio de resolução (${hours} h)`}
        value={metrics?.mttr_seconds != null ? formatSeconds(metrics.mttr_seconds) : '—'}
        hint={metrics ? `(${plural(metrics.mttr_count, 'incidente', 'incidentes')})` : undefined}
        help={`Do recebimento até fechar ou marcar como inconclusivo, em média, para os incidentes resolvidos nas últimas ${hours} horas (MTTR).`}
      />
      <Metric
        icon={breached > 0 ? CircleAlert : Gauge}
        label="Sem dono acima do SLA"
        value={metrics ? breached : '—'}
        alert={breached > 0}
        help={`Incidentes abertos, sem ninguém assumindo, que já passaram do prazo de reação da sua criticidade${slaText}.`}
      />
    </section>
  )
}
