import { QueryClient } from '@tanstack/react-query'

import { ApiError, isRetryable } from '@/api/errors'

export const MAX_RETRIES = 3
const MAX_DELAY_MS = 30_000

/** Up to 3 retries, only for network failures and 502/503/504; never for 4xx. */
export function shouldRetry(failureCount: number, error: unknown): boolean {
  return failureCount < MAX_RETRIES && isRetryable(error)
}

/** Honor Retry-After when the API sends it; otherwise exponential backoff with jitter. */
export function retryDelay(failureCount: number, error: unknown): number {
  if (error instanceof ApiError && error.retryAfterSeconds !== null) {
    return Math.min(error.retryAfterSeconds * 1000, MAX_DELAY_MS)
  }
  const cap = Math.min(1000 * 2 ** failureCount, MAX_DELAY_MS)
  return cap / 2 + Math.random() * (cap / 2)
}

export function createQueryClient(): QueryClient {
  return new QueryClient({
    defaultOptions: {
      queries: { retry: shouldRetry, retryDelay, staleTime: 5_000 },
      // Writes carry the version (optimistic locking): repeating one that already
      // happened returns 409 with the current state, never a duplicate (ADR 0002).
      mutations: { retry: shouldRetry, retryDelay },
    },
  })
}
