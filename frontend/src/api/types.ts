/** TypeScript mirror of the backend schemas (backend/app/schemas). */

export type Severity = 'high' | 'medium' | 'low'
export type IncidentCategory =
  | 'vehicle_accident'
  | 'accident_with_victims'
  | 'adverse_weather'
  | 'mechanical_failure'
  | 'road_blockage'
export type IncidentStatus = 'open' | 'investigating' | 'closed' | 'inconclusive'
export type IncidentSource = 'api' | 'whatsapp' | 'manual'
export type IncidentEventType = 'created' | 'status_changed' | 'deleted' | 'updated'
export type CargoType = 'hazardous' | 'perishable' | 'high_value' | 'general' | 'empty'
export type ClientTier = 'strategic' | 'priority' | 'standard'

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
  /** Fleet snapshot copied when the incident was created. */
  cargo_type: CargoType
  client_name: string | null
  client_tier: ClientTier
  /** False when the truck was not found in the fleet (defaults were used). */
  fleet_match: boolean
  assignee: AnalystRef | null
  version: number
  created_at: IsoDateTime
  updated_at: IsoDateTime
  acknowledged_at: IsoDateTime | null
  resolved_at: IsoDateTime | null
  priority_score: number
  priority_breakdown: PriorityBreakdown
}

/** Why an incident has its priority_score (rules in GET /config → priority). */
export interface PriorityBreakdown {
  cargo_points: number
  problem_points: number
  client_points: number
  /** Weighted mean of the three grades, 0 to 100. */
  base: number
  wait_bonus: number
  /** Active incident with victims: fixed top score. */
  victims: boolean
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

/** GET /config: business rules and tools, read once after login. */
export interface AppConfig {
  sla_minutes: Record<Severity, number>
  escalation_minutes: number
  priority: {
    weights: { cargo: number; problem: number; client: number }
    cargo_points: Record<CargoType, number>
    problem_points: Record<string, Record<Severity, number>>
    client_points: Record<ClientTier, number>
    wait_bonus_per_minute: number
    wait_bonus_cap: number
    victims_score: number
  }
  features: { demo: boolean; chaos: boolean }
}

export interface IncidentMetrics {
  window_hours: number
  mtta_seconds: number | null
  mtta_count: number
  mttr_seconds: number | null
  mttr_count: number
  escalated_now: number
  sla_breached_now: number
}

export interface ChaosConfig {
  latency_ms: number
  failure_rate: number
}

// --- WhatsApp triage (driver simulator) ---------------------------------------------

export type MessageDirection = 'in' | 'out'

export interface ConversationMessage {
  id: string
  direction: MessageDirection
  text: string
  created_at: IsoDateTime
}

export interface ConversationThread {
  step: string | null
  options: string[]
  messages: ConversationMessage[]
}

export interface BotReply {
  replies: string[]
}

export interface FleetTruck {
  code: string
  cargo_type: CargoType
  client_name: string
  client_tier: ClientTier
}

export interface RecentConversation {
  phone: string
  truck_code: string | null
  last_message_at: IsoDateTime
  last_out_at: IsoDateTime | null
}

/** Body of POST /incidents/manual (same schema as the ingestion). */
export interface ManualIncidentInput {
  truck_code: string
  category: IncidentCategory
  severity: Severity
  description: string
  highway?: string
  km?: string
  location_note?: string
}
