import { History } from 'lucide-react'

import type { IncidentDetail } from '@/api/types'
import { describeEvent } from '@/features/incident/eventText'
import { formatAgo, formatDateTime } from '@/lib/format'
import { useNow } from '@/lib/useNow'

/** Who did what and when, newest first, in plain language. */
export function Timeline({ incident }: { incident: IncidentDetail }) {
  const now = useNow()
  const entries = incident.events.map((event) => describeEvent(event, incident)).reverse()

  return (
    <section aria-labelledby="timeline-title" className="grid gap-2">
      <h3 id="timeline-title" className="flex items-center gap-1.5 text-xs font-semibold tracking-wide text-text-muted uppercase">
        <History aria-hidden className="size-3.5" />
        Linha do tempo
      </h3>
      <ol className="grid gap-0 border-l pl-4">
        {entries.map((entry) => (
          <li key={entry.id} className="relative pb-3 last:pb-0">
            <span aria-hidden className="absolute top-1.5 -left-[21px] size-2 rounded-full border-2 border-surface-1 bg-border-strong" />
            <p className="text-sm">
              {entry.actor ? <span className="font-semibold">{entry.actor} </span> : null}
              {entry.actor ? entry.action : entry.action.charAt(0).toUpperCase() + entry.action.slice(1)}
              <span className="text-text-subtle">
                {' · '}
                <time dateTime={entry.createdAt} title={formatDateTime(entry.createdAt)}>
                  {formatAgo(now - Date.parse(entry.createdAt))}
                </time>
              </span>
            </p>
            {entry.detail && (
              <p className="mt-0.5 rounded-sm bg-surface-2 px-2 py-1 text-xs text-text-muted">{entry.detail}</p>
            )}
          </li>
        ))}
      </ol>
    </section>
  )
}
