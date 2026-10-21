import { useQuery } from '@tanstack/react-query'

import { fetchIncident } from '@/api/incidents'
import { POLL_MS } from '@/features/queue/queries'

export const detailKey = (id: string) => ['incidents', 'detail', id] as const

/** Live detail of the open incident. `frozen` (editing or a dialog open) pauses the
 *  polling so nothing on screen changes under the analyst's hands. */
export function useIncidentDetail(id: string | null, frozen: boolean) {
  return useQuery({
    queryKey: detailKey(id ?? ''),
    queryFn: () => fetchIncident(id!),
    enabled: id !== null,
    refetchInterval: frozen ? false : POLL_MS,
    refetchOnWindowFocus: !frozen,
  })
}
