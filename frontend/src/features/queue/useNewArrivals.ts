import { useEffect, useRef, useState } from 'react'

export const ARRIVAL_HIGHLIGHT_MS = 1_500

/**
 * Ids that appeared since the previous refresh of the SAME query. Never on the first
 * load, never when the query (filters) changes, never for placeholder data shown
 * while a new query loads.
 */
export function useNewArrivals(
  queryKey: string,
  ids: string[] | undefined,
  dataUpdatedAt: number,
  isPlaceholderData: boolean,
): ReadonlySet<string> {
  const seen = useRef<{ key: string; ids: Set<string> } | null>(null)
  const timer = useRef<number | undefined>(undefined)
  const [fresh, setFresh] = useState<ReadonlySet<string>>(() => new Set())

  // `ids` must be memoized by the caller: this runs once per refresh, not per render.
  useEffect(() => {
    const current = ids
    if (!current || isPlaceholderData) return
    const previous = seen.current
    seen.current = { key: queryKey, ids: new Set(current) }
    if (!previous || previous.key !== queryKey) return // first load or new filters

    const arrived = current.filter((id) => !previous.ids.has(id))
    if (!arrived.length) return
    window.clearTimeout(timer.current)
    setFresh(new Set(arrived))
    timer.current = window.setTimeout(() => setFresh(new Set()), ARRIVAL_HIGHLIGHT_MS)
  }, [queryKey, ids, dataUpdatedAt, isPlaceholderData])

  useEffect(() => () => window.clearTimeout(timer.current), [])

  return fresh
}
