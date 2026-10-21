import type { Incident, Severity } from '@/api/types'

/** Time to react (be assumed) per severity, in minutes. */
export const SLA_MINUTES: Record<Severity, number> = { high: 5, medium: 15, low: 30 }
/** Share of the SLA after which the timer turns amber. */
const NEAR_RATIO = 0.7
/** High + open + nobody on it for longer than this: escalate. */
export const ESCALATION_MINUTES = 5

export type TimingState =
  | { kind: 'waiting'; elapsedMs: number; level: 'ok' | 'near' | 'breached' } // nobody took it yet
  | { kind: 'assumed'; elapsedMs: number } // time until someone took it
  | { kind: 'resolved'; elapsedMs: number } // time until closed/inconclusive

export function timing(incident: Incident, now: number): TimingState {
  const created = Date.parse(incident.created_at)
  if (incident.resolved_at && (incident.status === 'closed' || incident.status === 'inconclusive')) {
    return { kind: 'resolved', elapsedMs: Date.parse(incident.resolved_at) - created }
  }
  if (incident.assignee && incident.acknowledged_at) {
    return { kind: 'assumed', elapsedMs: Date.parse(incident.acknowledged_at) - created }
  }
  const elapsedMs = now - created
  const slaMs = SLA_MINUTES[incident.severity] * 60_000
  const level = elapsedMs >= slaMs ? 'breached' : elapsedMs >= slaMs * NEAR_RATIO ? 'near' : 'ok'
  return { kind: 'waiting', elapsedMs, level }
}

/** Minutes a high-severity, open incident has had no owner, if past the threshold. */
export function unownedMinutes(incident: Incident, now: number): number | null {
  if (incident.severity !== 'high' || incident.status !== 'open' || incident.assignee) return null
  const elapsedMs = now - Date.parse(incident.created_at)
  return elapsedMs > ESCALATION_MINUTES * 60_000 ? Math.floor(elapsedMs / 60_000) : null
}
