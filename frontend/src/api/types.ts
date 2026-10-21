/** TypeScript mirror of the backend schemas (backend/app/schemas). */

export type Severity = 'high' | 'medium' | 'low'
export type IncidentCategory =
  | 'vehicle_accident'
  | 'accident_with_victims'
  | 'adverse_weather'
  | 'mechanical_failure'
  | 'road_blockage'
export type IncidentStatus = 'open' | 'investigating' | 'closed' | 'inconclusive'
export type IncidentSource = 'api' | 'whatsapp'
export type IncidentEventType = 'created' | 'status_changed' | 'deleted' | 'updated'

/** ISO 8601 date-time string, as returned by the API. */
export type IsoDateTime = string

export interface AnalystRef {
  id: string
  name: string
}

export interface Analyst extends AnalystRef {
  username: string
}

export interface Incident {
  id: string
  description: string
  category: IncidentCategory
  severity: Severity
  status: IncidentStatus
  truck_code: string
  driver_name: string | null
  highway: string | null
  km: number | null
  location_note: string | null
  source: IncidentSource
  raw_message: string | null
  assignee: AnalystRef | null
  version: number
  created_at: IsoDateTime
  updated_at: IsoDateTime
  acknowledged_at: IsoDateTime | null
  resolved_at: IsoDateTime | null
  priority_score: number
}

export interface IncidentEvent {
  id: string
  event_type: IncidentEventType
  from_status: IncidentStatus | null
  to_status: IncidentStatus | null
  note: string | null
  analyst: AnalystRef | null
  created_at: IsoDateTime
}

export interface IncidentDetail extends Incident {
  events: IncidentEvent[]
}

export interface IncidentListResponse {
  items: Incident[]
  total: number
  limit: number
  offset: number
}

export interface IncidentSummary {
  total_active: number
  by_severity: Record<Severity, number>
  by_category: Record<IncidentCategory, number>
}

export interface IncidentFilters {
  severity?: Severity[]
  category?: IncidentCategory[]
  status?: IncidentStatus[]
  assigned_to?: 'me'
  limit?: number
  offset?: number
}

export interface StatusChange {
  status: IncidentStatus
  version: number
  note?: string
}

export interface IncidentUpdate {
  version: number
  severity?: Severity
  category?: IncidentCategory
  description?: string
  highway?: string | null
  km?: number | string | null
  location_note?: string | null
}

export interface TokenResponse {
  access_token: string
  token_type: 'bearer'
  expires_in: number
  analyst: Analyst
}

export interface InvalidParam {
  location: string
  message: string
  input?: unknown
}

/** RFC 9457 problem details; extension members depend on the status. */
export interface ProblemDetail {
  type: string
  title: string
  status: number
  detail: string
  request_id?: string
  errors?: InvalidParam[] // 422
  current?: IncidentDetail // 409
  assignee?: AnalystRef | null // 403
}

export interface ChaosStatus {
  latency_ms: number
  failure_rate: number
  active: boolean
  expires_at: IsoDateTime | null
}

export interface DemoResetResponse {
  deleted: number
  created: number
}

export interface DemoSimulateResponse {
  items: Incident[]
}
