import { apiRequest } from '@/api/client'
import type { IncidentFilters, IncidentListResponse, IncidentSummary } from '@/api/types'

export const ACTIVE_STATUSES = ['open', 'investigating'] as const
export const QUEUE_LIMIT = 200 // the API maximum: the whole active queue in one page

export function fetchIncidents(filters: IncidentFilters): Promise<IncidentListResponse> {
  return apiRequest('/incidents', {
    query: {
      severity: filters.severity,
      category: filters.category,
      status: filters.status,
      assigned_to: filters.assigned_to,
      limit: filters.limit ?? QUEUE_LIMIT,
      offset: filters.offset,
    },
  })
}

export function fetchSummary(): Promise<IncidentSummary> {
  return apiRequest('/incidents/summary')
}

/** How many active incidents the current analyst owns (only the total is read). */
export async function fetchMyActiveCount(): Promise<number> {
  const page = await fetchIncidents({ assigned_to: 'me', status: [...ACTIVE_STATUSES], limit: 1 })
  return page.total
}
