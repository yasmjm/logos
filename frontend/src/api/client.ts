import { API_URL } from '@/api/config'
import { ApiError, NetworkError, parseRetryAfter } from '@/api/errors'
import { endSession, getSession } from '@/api/session'
import type { ProblemDetail } from '@/api/types'

const DEFAULT_TIMEOUT_MS = 15_000

export type QueryValue = string | number | boolean | undefined | readonly (string | number)[]

export interface RequestOptions {
  method?: 'GET' | 'POST' | 'PUT' | 'PATCH' | 'DELETE'
  /** JSON body. */
  json?: unknown
  /** Form body (application/x-www-form-urlencoded), used by the OAuth2 login. */
  form?: URLSearchParams
  query?: Record<string, QueryValue>
  /** Send the analyst token (default). A 401 then ends the session. */
  auth?: boolean
  signal?: AbortSignal
  timeoutMs?: number
}

function buildUrl(path: string, query?: RequestOptions['query']): string {
  const url = new URL(API_URL + path)
  for (const [key, value] of Object.entries(query ?? {})) {
    if (value === undefined) continue
    for (const item of Array.isArray(value) ? value : [value]) {
      url.searchParams.append(key, String(item)) // repeated keys for multi-value filters
    }
  }
  return url.toString()
}

async function readProblem(response: Response): Promise<ProblemDetail | null> {
  try {
    const body: unknown = await response.json()
    return body && typeof body === 'object' ? (body as ProblemDetail) : null
  } catch {
    return null // not JSON (e.g. a proxy error page)
  }
}

export async function apiRequest<T>(path: string, options: RequestOptions = {}): Promise<T> {
  const { method = 'GET', json, form, query, auth = true, signal, timeoutMs } = options

  const headers = new Headers({ Accept: 'application/json, application/problem+json' })
  let body: BodyInit | undefined
  if (json !== undefined) {
    headers.set('Content-Type', 'application/json')
    body = JSON.stringify(json)
  } else if (form) {
    body = form // fetch sets the form content type
  }
  const token = auth ? getSession()?.token : undefined
  if (token) headers.set('Authorization', `Bearer ${token}`)

  const timeout = AbortSignal.timeout(timeoutMs ?? DEFAULT_TIMEOUT_MS)
  let response: Response
  try {
    response = await fetch(buildUrl(path, query), {
      method,
      headers,
      body,
      signal: signal ? AbortSignal.any([signal, timeout]) : timeout,
    })
  } catch (error) {
    if (signal?.aborted) throw error // cancelled by the caller (e.g. TanStack Query)
    const timedOut = timeout.aborted
    throw new NetworkError(timedOut ? 'The API took too long to answer.' : 'Could not reach the API.', {
      cause: error,
      timedOut,
    })
  }

  if (!response.ok) {
    const error = new ApiError({
      status: response.status,
      body: await readProblem(response),
      retryAfterSeconds: parseRetryAfter(response.headers.get('Retry-After')),
      requestId: response.headers.get('X-Request-ID'),
      fallbackTitle: response.statusText || `HTTP ${response.status}`,
    })
    // Missing, invalid or expired token on any authenticated route: back to login.
    if (response.status === 401 && token) endSession('expired')
    throw error
  }

  if (response.status === 204) return undefined as T
  return (await response.json()) as T
}
