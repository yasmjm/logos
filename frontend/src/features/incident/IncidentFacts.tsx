import { MapPinOff, MessageCircle, TriangleAlert } from 'lucide-react'
import type { ReactNode } from 'react'

import type { IncidentDetail } from '@/api/types'
import { CategoryLabel } from '@/components/CategoryLabel'
import { SourceBadge } from '@/components/SourceBadge'
import { formatDateTime, formatLocation } from '@/lib/format'
import { CARGO_HINTS, CLIENT_TIER_LABELS, SOURCE_LABELS } from '@/lib/labels'

function Fact({ label, children }: { label: string; children: ReactNode }) {
  return (
    <div className="grid min-w-0 gap-0.5">
      <dt className="text-xs text-text-subtle">{label}</dt>
      <dd className="min-w-0 text-sm break-words">{children}</dd>
    </div>
  )
}

export function IncidentFacts({ incident }: { incident: IncidentDetail }) {
  const location = formatLocation(incident.highway, incident.km)
  return (
    <div className="grid gap-4">
      <p className="text-base leading-snug text-text">{incident.description}</p>

      {incident.source === 'whatsapp' && incident.raw_message && (
        <figure className="rounded-md border border-border-strong bg-surface-2 p-3">
          <figcaption className="mb-1.5 flex items-center gap-1.5 text-xs font-medium text-text-muted">
            <MessageCircle aria-hidden className="size-3.5" />
            Mensagem original do motorista (WhatsApp)
          </figcaption>
          <blockquote className="text-sm whitespace-pre-wrap text-text italic">“{incident.raw_message}”</blockquote>
        </figure>
      )}

      <dl className="grid grid-cols-2 gap-x-4 gap-y-3">
        <Fact label="Categoria">
          <CategoryLabel category={incident.category} />
        </Fact>
        <Fact label="Origem">
          {incident.source === 'api' ? SOURCE_LABELS.api : <SourceBadge source={incident.source} />}
        </Fact>
        <Fact label="Caminhão">
          <span className="font-mono">{incident.truck_code}</span>
        </Fact>
        <Fact label="Motorista">
          {incident.driver_name ?? <span className="text-text-subtle italic">Não informado</span>}
        </Fact>
        <Fact label="Localização">
          {location ? (
            <span className="font-mono">{location}</span>
          ) : (
            <span className="inline-flex items-center gap-1 text-text-subtle italic">
              <MapPinOff aria-hidden className="size-3.5" />
              Localização não informada
            </span>
          )}
          {incident.location_note && (
            <span className="mt-0.5 block text-xs text-text-muted">{incident.location_note}</span>
          )}
        </Fact>
        <Fact label="Recebido em">{formatDateTime(incident.created_at)}</Fact>
        <Fact label="Carga (no momento do incidente)">{CARGO_HINTS[incident.cargo_type]}</Fact>
        <Fact label="Cliente">
          {incident.client_name ?? <span className="text-text-subtle italic">Não identificado</span>}
          <span className="mt-0.5 block text-xs text-text-muted">
            {CLIENT_TIER_LABELS[incident.client_tier]}
          </span>
        </Fact>
      </dl>

      {!incident.fleet_match && (
        <p role="note" className="flex items-start gap-2 rounded-md border border-sev-medium-border bg-sev-medium-bg px-3 py-2 text-xs">
          <TriangleAlert aria-hidden className="mt-px size-3.5 shrink-0 text-sev-medium" />
          <span>
            Dados da frota não encontrados para <span className="font-mono">{incident.truck_code}</span>.
            A prioridade considera carga geral e cliente padrão.
          </span>
        </p>
      )}
    </div>
  )
}
