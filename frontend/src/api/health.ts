import { apiRequest } from '@/api/client'

/** Readiness: 200 when the API and its database answer. */
export function fetchReadiness(): Promise<{ status: string }> {
  return apiRequest('/ready', { auth: false, timeoutMs: 8_000 })
}
