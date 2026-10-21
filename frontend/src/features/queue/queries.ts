import { keepPreviousData, useQuery } from '@tanstack/react-query'

import { fetchIncidents, fetchMetrics, fetchMyActiveCount, fetchSummary } from '@/api/incidents'
import type { IncidentFilters } from '@/api/types'

export const POLL_MS = 5_000

/** Polling every 5 s; TanStack Query pauses it while the tab is hidden. */
const polling = { refetchInterval: POLL_MS, refetchIntervalInBackground: false } as const

export const queueKeys = {
  all: ['incidents'] as const,
  list: (filters: IncidentFilters) => ['incidents', 'list', filters] as const,
  summary: ['incidents', 'summary'] as const,
  mine: ['incidents', 'mine-count'] as const,
  metrics: ['incidents', 'metrics'] as const,
}

export function useIncidentList(filters: IncidentFilters) {
  return useQuery({
    queryKey: queueKeys.list(filters),
    queryFn: () => fetchIncidents(filters),
    // Keep showing the previous list while new filters load, and after a failed refresh.
    placeholderData: keepPreviousData,
    ...polling,
  })
}

export function useSummary() {
  return useQuery({ queryKey: queueKeys.summary, queryFn: fetchSummary, ...polling })
}

export function useMyActiveCount() {
  return useQuery({ queryKey: queueKeys.mine, queryFn: fetchMyActiveCount, ...polling })
}

export function useMetrics() {
  return useQuery({ queryKey: queueKeys.metrics, queryFn: fetchMetrics, ...polling })
}
