import { useMemo } from 'react'

import { IncidentDrawer } from '@/features/incident/IncidentDrawer'

import { FilterBar } from '@/features/queue/FilterBar'
import { IncidentQueue } from '@/features/queue/IncidentQueue'
import { KpiBar } from '@/features/queue/KpiBar'
import { QueueEmpty, QueueError, QueueSkeleton, StaleBanner } from '@/features/queue/QueueStates'
import { useIncidentList, useMetrics, useMyActiveCount, useSummary } from '@/features/queue/queries'
import { MetricsStrip } from '@/features/queue/MetricsStrip'
import { useNewArrivals } from '@/features/queue/useNewArrivals'
import { useQueueFilters } from '@/features/queue/useQueueFilters'
import { formatAgo } from '@/lib/format'
import { useNow } from '@/lib/useNow'

export function QueuePage({ myId }: { myId: string }) {
  const { filters, apiFilters, isDefault, update, clear, incidentId, selectIncident } = useQueueFilters()
  const list = useIncidentList(apiFilters)
  const summary = useSummary()
  const myCount = useMyActiveCount()
  const metrics = useMetrics()
  const now = useNow()

  const incidents = list.data?.items
  const ids = useMemo(() => incidents?.map((incident) => incident.id), [incidents])
  const arrivedIds = useNewArrivals(
    JSON.stringify(apiFilters),
    ids,
    list.dataUpdatedAt,
    list.isPlaceholderData,
  )
  const retry = () => void list.refetch()

  return (
    <div className="mx-auto grid w-full max-w-[1600px] gap-3 px-3 py-3 sm:px-4">
      <KpiBar
        summary={summary.data}
        myCount={myCount.data}
        filters={filters}
        isDefault={isDefault}
        update={update}
        clear={clear}
      />
      <MetricsStrip metrics={metrics.data} />
      <FilterBar
        filters={filters}
        isDefault={isDefault}
        update={update}
        clear={clear}
        shown={incidents?.length}
        total={list.data?.total}
      />

      {list.isError && incidents && (
        <StaleBanner ago={formatAgo(now - list.dataUpdatedAt)} onRetry={retry} retrying={list.isFetching} />
      )}

      <section aria-label="Fila de incidentes" className="overflow-clip rounded-md border bg-surface-1">
        {incidents === undefined ? (
          list.isError ? (
            <QueueError onRetry={retry} retrying={list.isFetching} />
          ) : (
            <QueueSkeleton />
          )
        ) : incidents.length === 0 ? (
          <QueueEmpty filtered={!isDefault} onClear={clear} />
        ) : (
          <IncidentQueue
            incidents={incidents}
            myId={myId}
            selectedId={incidentId}
            arrivedIds={arrivedIds}
            onSelect={selectIncident}
          />
        )}
      </section>

      <IncidentDrawer incidentId={incidentId} myId={myId} onClose={() => selectIncident(null)} />
    </div>
  )
}
