import type { AppConfig, Incident } from '@/api/types'

/** Share of the SLA after which the timer turns amber. */
const NEAR_RATIO = 0.7

/** SLA and escalation rules come from GET /config (backend app/domain/sla.py). */
export type SlaRules = Pick<AppConfig, 'sla_minutes' | 'escalation_minutes'>

export type TimingState =
  | { kind: 'waiting'; elapsedMs: number; level: 'unknown' | 'ok' | 'near' | 'breached' } // nobody took it
  | { kind: 'assumed'; elapsedMs: number } // time until someone took it
  | { kind: 'resolved'; elapsedMs: number } // time until closed/inconclusive

export function timing(incident: Incident, now: number, rules: SlaRules | undefined): TimingState {
  const created = Date.parse(incident.created_at)
  if (incident.resolved_at && (incident.status === 'closed' || incident.status === 'inconclusive')) {
    return { kind: 'resolved', elapsedMs: Date.parse(incident.resolved_at) - created }
  }
  if (incident.assignee && incident.acknowledged_at) {
    return { kind: 'assumed', elapsedMs: Date.parse(incident.acknowledged_at) - created }
  }
  const elapsedMs = now - created
  if (!rules) return { kind: 'waiting', elapsedMs, level: 'unknown' } // rules not loaded yet
  const slaMs = rules.sla_minutes[incident.severity] * 60_000
  const level = elapsedMs >= slaMs ? 'breached' : elapsedMs >= slaMs * NEAR_RATIO ? 'near' : 'ok'
  return { kind: 'waiting', elapsedMs, level }
}

/** Minutes a high-severity, open incident has had no owner, if past the threshold. */
export function unownedMinutes(incident: Incident, now: number, rules: SlaRules | undefined): number | null {
  if (!rules) return null
  if (incident.severity !== 'high' || incident.status !== 'open' || incident.assignee) return null
  const elapsedMs = now - Date.parse(incident.created_at)
  return elapsedMs > rules.escalation_minutes * 60_000 ? Math.floor(elapsedMs / 60_000) : null
}
