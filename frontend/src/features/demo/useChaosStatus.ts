import { useQuery } from '@tanstack/react-query'

import { useAppConfig } from '@/api/appConfig'
import { fetchChaos } from '@/api/demo'
import { POLL_MS } from '@/features/queue/queries'

export const chaosKey = ['chaos'] as const

/** Chaos mode state, only when the API has it enabled (GET /config). */
export function useChaosStatus() {
  const enabled = useAppConfig().data?.features.chaos ?? false
  return useQuery({
    queryKey: chaosKey,
    queryFn: fetchChaos,
    enabled,
    refetchInterval: POLL_MS,
  })
}
