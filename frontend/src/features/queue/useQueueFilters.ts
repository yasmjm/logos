import { useCallback, useMemo, useSyncExternalStore } from 'react'

import { ACTIVE_STATUSES } from '@/api/incidents'
import type { IncidentCategory, IncidentFilters, IncidentStatus, Severity } from '@/api/types'
import { CATEGORY_LABELS, SEVERITY_LABELS, STATUS_LABELS } from '@/lib/labels'

/** Queue filters live in the URL (?severity=high&severity=medium&status=closed&mine=1),
 *  so a view can be reloaded or shared. No status in the URL = only active incidents. */
export interface QueueFilters {
  severity: Severity[]
  category: IncidentCategory[]
  status: IncidentStatus[]
  mine: boolean
}

const SEVERITIES = Object.keys(SEVERITY_LABELS) as Severity[]
const CATEGORIES = Object.keys(CATEGORY_LABELS) as IncidentCategory[]
const STATUSES = Object.keys(STATUS_LABELS) as IncidentStatus[]
export const DEFAULT_STATUSES: IncidentStatus[] = [...ACTIVE_STATUSES]

function pick<T extends string>(params: URLSearchParams, key: string, allowed: T[]): T[] {
  const values = params.getAll(key).filter((v): v is T => (allowed as string[]).includes(v))
  return allowed.filter((value) => values.includes(value)) // stable order, no duplicates
}

function parse(search: string): QueueFilters {
  const params = new URLSearchParams(search)
  const status = pick(params, 'status', STATUSES)
  return {
    severity: pick(params, 'severity', SEVERITIES),
    category: pick(params, 'category', CATEGORIES),
    status: status.length ? status : DEFAULT_STATUSES,
    mine: params.get('mine') === '1',
  }
}

function sameSet(a: string[], b: string[]): boolean {
  return a.length === b.length && a.every((value) => b.includes(value))
}

const INCIDENT_PARAM = 'incident'

function serialize(filters: QueueFilters, incident: string | null): string {
  const params = new URLSearchParams()
  filters.severity.forEach((v) => params.append('severity', v))
  filters.category.forEach((v) => params.append('category', v))
  if (!sameSet(filters.status, DEFAULT_STATUSES)) filters.status.forEach((v) => params.append('status', v))
  if (filters.mine) params.set('mine', '1')
  if (incident) params.set(INCIDENT_PARAM, incident)
  const query = params.toString()
  return query ? `?${query}` : ''
}

const listeners = new Set<() => void>()
function subscribe(notify: () => void): () => void {
  listeners.add(notify)
  window.addEventListener('popstate', notify)
  return () => {
    listeners.delete(notify)
    window.removeEventListener('popstate', notify)
  }
}

function currentIncident(search: string): string | null {
  return new URLSearchParams(search).get(INCIDENT_PARAM) || null
}

function navigate(filters: QueueFilters, incident = currentIncident(window.location.search)): void {
  const url = `${window.location.pathname}${serialize(filters, incident)}${window.location.hash}`
  window.history.replaceState(window.history.state, '', url)
  listeners.forEach((notify) => notify())
}

export function toggle<T>(values: T[], value: T): T[] {
  return values.includes(value) ? values.filter((v) => v !== value) : [...values, value]
}

export function useQueueFilters() {
  const search = useSyncExternalStore(subscribe, () => window.location.search, () => '')
  const filters = useMemo(() => parse(search), [search])

  const update = useCallback(
    (change: (current: QueueFilters) => Partial<QueueFilters>) => {
      const current = parse(window.location.search)
      const next = { ...current, ...change(current) }
      if (!next.status.length) next.status = DEFAULT_STATUSES // never an empty status filter
      navigate(next)
    },
    [],
  )
  const clear = useCallback(() => navigate(parse('')), [])
  /** The open incident (?incident=<id>) survives filter changes. */
  const selectIncident = useCallback(
    (id: string | null) => navigate(parse(window.location.search), id),
    [],
  )
  const incidentId = currentIncident(search)

  const isDefault =
    !filters.severity.length &&
    !filters.category.length &&
    !filters.mine &&
    sameSet(filters.status, DEFAULT_STATUSES)

  const apiFilters: IncidentFilters = useMemo(
    () => ({
      severity: filters.severity.length ? filters.severity : undefined,
      category: filters.category.length ? filters.category : undefined,
      status: filters.status,
      assigned_to: filters.mine ? 'me' : undefined,
    }),
    [filters],
  )

  return { filters, apiFilters, isDefault, update, clear, incidentId, selectIncident }
}
