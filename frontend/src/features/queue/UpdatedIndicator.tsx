import { useQueryClient } from '@tanstack/react-query'
import { useSyncExternalStore } from 'react'

import { queueKeys } from '@/features/queue/queries'
import { formatAgo } from '@/lib/format'
import { useNow } from '@/lib/useNow'
import { cn } from '@/lib/utils'

/** "Atualizado há Xs", from the most recent successful refresh of the queue. */
export function UpdatedIndicator() {
  const cache = useQueryClient().getQueryCache()
  const snapshot = useSyncExternalStore(
    (notify) => cache.subscribe(notify),
    () => {
      const queries = cache.findAll({ queryKey: queueKeys.all })
      const updatedAt = Math.max(0, ...queries.map((q) => q.state.dataUpdatedAt))
      const failing = queries.some((q) => q.state.status === 'error' || q.state.fetchFailureCount > 0)
      return `${updatedAt}|${failing}`
    },
  )
  const now = useNow()
  const [updatedAtText, failingText] = snapshot.split('|')
  const updatedAt = Number(updatedAtText)
  if (!updatedAt) return null
  const failing = failingText === 'true'

  return (
    <span
      role="status"
      aria-live="off"
      className={cn(
        'hidden items-center gap-1.5 text-xs tabular-nums sm:inline-flex',
        failing ? 'text-sev-medium' : 'text-text-subtle',
      )}
      title={failing ? 'A última tentativa de atualizar falhou' : 'A fila atualiza a cada 5 s'}
    >
      <span
        aria-hidden
        className={cn('size-1.5 rounded-full', failing ? 'bg-sev-medium' : 'bg-status-closed')}
      />
      Atualizado {formatAgo(now - updatedAt)}
    </span>
  )
}
