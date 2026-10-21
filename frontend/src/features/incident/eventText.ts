import type { Incident, IncidentDetail, IncidentEvent, IncidentStatus } from '@/api/types'
import { CATEGORY_LABELS, SEVERITY_LABELS, SOURCE_LABELS } from '@/lib/labels'

/** "assumiu o incidente", "fechou o incidente", ... for a status change. */
export function describeStatusChange(from: IncidentStatus | null, to: IncidentStatus | null): string {
  if (to === 'investigating') return 'assumiu o incidente'
  if (to === 'closed') return 'fechou o incidente'
  if (to === 'inconclusive') return 'marcou o incidente como inconclusivo'
  if (to === 'open') return from === 'investigating' ? 'liberou o incidente' : 'reabriu o incidente'
  return 'mudou o status do incidente'
}

const FIELD_LABELS: Record<string, string> = {
  severity: 'Criticidade',
  category: 'Categoria',
  description: 'Descrição',
  highway: 'Rodovia',
  km: 'Km',
  location_note: 'Observação de local',
}

function translateValue(field: string, value: string): string {
  if (value === 'null') return 'vazio'
  if (field === 'severity' && value in SEVERITY_LABELS) {
    return SEVERITY_LABELS[value as keyof typeof SEVERITY_LABELS]
  }
  if (field === 'category' && value in CATEGORY_LABELS) {
    return CATEGORY_LABELS[value as keyof typeof CATEGORY_LABELS]
  }
  return value
}

/** Backend note "severity: medium → high; category: a → b" in Portuguese. */
export function translateUpdateNote(note: string | null): string | null {
  if (!note) return null
  // Split only before a known field: values themselves may contain "; ".
  const fields = Object.keys(FIELD_LABELS).join('|')
  return note
    .split(new RegExp(`; (?=(?:${fields}): )`))
    .map((change) => {
      const match = /^(\w+): ([\s\S]*?) → ([\s\S]*)$/.exec(change)
      if (!match) return change
      const [, field = '', before = '', after = ''] = match
      const label = FIELD_LABELS[field] ?? field
      return `${label}: ${translateValue(field, before)} → ${translateValue(field, after)}`
    })
    .join('; ')
}

export interface TimelineEntry {
  id: string
  actor: string | null // analyst name, or null for the system/ingestion
  action: string
  detail: string | null
  createdAt: string
}

export function describeEvent(event: IncidentEvent, incident: Incident): TimelineEntry {
  const base = { id: event.id, actor: event.analyst?.name ?? null, createdAt: event.created_at }
  switch (event.event_type) {
    case 'created':
      return {
        ...base,
        // With an analyst (manual source): "Ana Souza registrou o incidente".
        action: base.actor ? 'registrou o incidente' : `Incidente recebido via ${SOURCE_LABELS[incident.source]}`,
        detail: null,
      }
    case 'status_changed':
      return {
        ...base,
        action: describeStatusChange(event.from_status, event.to_status),
        detail: event.note,
      }
    case 'updated':
      return { ...base, action: 'editou o incidente', detail: translateUpdateNote(event.note) }
    case 'deleted':
      return { ...base, action: 'arquivou o incidente', detail: event.note }
  }
}

/** Last change that someone made, e.g. for "Bruno Lima assumiu este incidente há 8 s". */
export function lastChange(incident: IncidentDetail): IncidentEvent | undefined {
  return [...incident.events].reverse().find((event) => event.event_type !== 'created')
}
