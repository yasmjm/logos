import { useQuery } from '@tanstack/react-query'
import { useEffect, useState } from 'react'

import { ApiError } from '@/api/errors'
import { fetchReadiness } from '@/api/health'

export type ApiStatus = 'checking' | 'waking' | 'online' | 'database-waking' | 'offline'

const SLOW_AFTER_MS = 2_500

/** Is the API reachable? Distinguishes "waking up" (slow or 503) from "offline". */
export function useApiStatus(): ApiStatus {
  const readiness = useQuery({
    queryKey: ['readiness'],
    queryFn: fetchReadiness,
    retry: false,
    refetchInterval: (query) => (query.state.status === 'success' ? false : 5_000),
  })
  const [slow, setSlow] = useState(false)

  useEffect(() => {
    if (!readiness.isFetching) return
    const timer = window.setTimeout(() => setSlow(true), SLOW_AFTER_MS)
    return () => {
      window.clearTimeout(timer)
      setSlow(false)
    }
  }, [readiness.isFetching])

  if (readiness.isSuccess) return 'online'
  if (readiness.error instanceof ApiError && readiness.error.status === 503) {
    return 'database-waking'
  }
  if (readiness.isError) return slow ? 'waking' : 'offline'
  return slow ? 'waking' : 'checking'
}
