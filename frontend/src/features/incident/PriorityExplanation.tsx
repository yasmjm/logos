import { Calculator, Siren } from 'lucide-react'

import { useAppConfig } from '@/api/appConfig'
import type { IncidentDetail } from '@/api/types'
import { CARGO_LABELS, CLIENT_TIER_LABELS } from '@/lib/labels'

const number = new Intl.NumberFormat('pt-BR', { maximumFractionDigits: 1 })

/** "Por que está nesta posição": the score's arithmetic in plain language. */
export function PriorityExplanation({ incident }: { incident: IncidentDetail }) {
  const weights = useAppConfig().data?.priority.weights
  const b = incident.priority_breakdown
  const resolved = incident.status === 'closed' || incident.status === 'inconclusive'

  return (
    <section aria-labelledby="priority-title" className="grid gap-2 rounded-md border bg-surface-2 p-3">
      <h3
        id="priority-title"
        className="flex items-center gap-1.5 text-xs font-semibold tracking-wide text-text-muted uppercase"
      >
        <Calculator aria-hidden className="size-3.5" />
        Por que está nesta posição
        <span className="ml-auto font-mono text-sm normal-case tracking-normal text-text tabular-nums">
          {incident.priority_score}
        </span>
      </h3>

      {b.victims ? (
        <p className="flex items-start gap-2 text-sm">
          <Siren aria-hidden className="mt-0.5 size-4 shrink-0 text-sev-high" />
          <span>
            <strong>Há vítimas: prioridade máxima.</strong> Enquanto estiver ativo, fica acima de
            todos os outros incidentes; entre vítimas, o mais antigo vem primeiro.
          </span>
        </p>
      ) : (
        <>
          <p className="text-sm leading-relaxed">
            <span className="text-text-muted">Média ponderada: </span>
            {CARGO_LABELS[incident.cargo_type]} {b.cargo_points} × {fmt(weights?.cargo)}
            <span className="text-text-subtle"> · </span>
            Problema {b.problem_points} × {fmt(weights?.problem)}
            <span className="text-text-subtle"> · </span>
            {CLIENT_TIER_LABELS[incident.client_tier]} {b.client_points} × {fmt(weights?.client)}
            <span className="text-text-subtle"> = </span>
            {number.format(b.base)}
            {b.wait_bonus > 0 && (
              <>
                <span className="text-text-subtle"> · </span>+{b.wait_bonus} de espera
              </>
            )}
            <span className="text-text-subtle"> = </span>
            <strong className="tabular-nums">{incident.priority_score}</strong>
          </p>
          <p className="text-xs text-text-subtle">
            {resolved
              ? 'Encerrado: sem bônus de espera, e fica no fim da fila.'
              : incident.acknowledged_at
                ? 'O bônus de espera parou de contar quando o incidente foi assumido.'
                : 'Sem responsável: o bônus de espera sobe 1 ponto por minuto, até 20.'}
          </p>
        </>
      )}
    </section>
  )
}

function fmt(weight: number | undefined): string {
  return weight === undefined ? '…' : number.format(weight)
}
