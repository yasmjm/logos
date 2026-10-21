import { useQuery } from '@tanstack/react-query'

import { apiRequest } from '@/api/client'
import type { AppConfig } from '@/api/types'

export function fetchAppConfig(): Promise<AppConfig> {
  return apiRequest('/config')
}

/** SLA rules and available tools; fetched once per session (outside /incidents,
 *  so chaos mode never affects it). Until it arrives, SLA colors stay neutral. */
export function useAppConfig() {
  return useQuery({ queryKey: ['config'], queryFn: fetchAppConfig, staleTime: Infinity })
}
