import type { IncidentDetail, ProblemDetail } from '@/api/types'

/** An HTTP error answered by the API, usually as application/problem+json. */
export class ApiError extends Error {
  readonly status: number
  readonly title: string
  readonly detail: string
  /** Full response body, including extension members such as "current" on 409. */
  readonly body: ProblemDetail | null
  /** Seconds from the Retry-After header (429, 503), if any. */
  readonly retryAfterSeconds: number | null
  readonly requestId: string | null

  constructor(init: {
    status: number
    body: ProblemDetail | null
    retryAfterSeconds: number | null
    requestId: string | null
    fallbackTitle: string
  }) {
    const title = init.body?.title ?? init.fallbackTitle
    const detail = init.body?.detail ?? title
    super(detail)
    this.name = 'ApiError'
    this.status = init.status
    this.title = title
    this.detail = detail
    this.body = init.body
    this.retryAfterSeconds = init.retryAfterSeconds
    this.requestId = init.requestId ?? init.body?.request_id ?? null
  }

  /** On 409, the incident as it is now (who changed it, and when). */
  get current(): IncidentDetail | undefined {
    return this.status === 409 ? this.body?.current : undefined
  }
}

/** The request never got an HTTP answer: offline, DNS, CORS, timeout or connection reset. */
export class NetworkError extends Error {
  readonly timedOut: boolean

  constructor(message: string, options: { cause?: unknown; timedOut?: boolean } = {}) {
    super(message, { cause: options.cause })
    this.name = 'NetworkError'
    this.timedOut = options.timedOut ?? false
  }
}

/** Retry only what may succeed later: network failures and unavailable upstreams.
 *  4xx is never retried (the request itself is wrong, or a 409 needs a human). */
export function isRetryable(error: unknown): boolean {
  if (error instanceof NetworkError) return true
  return error instanceof ApiError && [502, 503, 504].includes(error.status)
}

/** Retry-After as seconds (RFC 9110: delta-seconds or an HTTP date). */
export function parseRetryAfter(header: string | null, now = Date.now()): number | null {
  if (!header) return null
  const seconds = Number(header)
  if (Number.isFinite(seconds) && seconds >= 0) return Math.ceil(seconds)
  const date = Date.parse(header)
  return Number.isNaN(date) ? null : Math.max(0, Math.ceil((date - now) / 1000))
}
