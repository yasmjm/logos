import { CircleAlert, RotateCw, ShieldCheck, SearchX } from 'lucide-react'

import { Button } from '@/components/ui/button'

export function QueueSkeleton({ rows = 10 }: { rows?: number }) {
  return (
    <div aria-busy="true" aria-label="Carregando a fila" role="status">
      {Array.from({ length: rows }, (_, index) => (
        <div key={index} className="queue-row border-b">
          <div data-area="sev">
            <div className="skeleton h-5 w-14" />
          </div>
          <div data-area="desc">
            <div className="skeleton h-4" style={{ width: `${55 + ((index * 37) % 40)}%` }} />
          </div>
          <div data-area="time">
            <div className="skeleton h-4 w-10" />
          </div>
        </div>
      ))}
    </div>
  )
}

export function QueueEmpty({ filtered, onClear }: { filtered: boolean; onClear: () => void }) {
  return (
    <div className="flex flex-col items-center gap-2 px-4 py-16 text-center">
      {filtered ? (
        <>
          <SearchX aria-hidden className="size-6 text-text-muted" />
          <p className="font-medium">Nenhum incidente com esses filtros</p>
          <Button variant="outline" size="sm" onClick={onClear}>
            Limpar filtros
          </Button>
        </>
      ) : (
        <>
          <ShieldCheck aria-hidden className="size-6 text-status-closed" />
          <p className="font-medium">Nenhum incidente ativo. Operação estável.</p>
        </>
      )}
    </div>
  )
}

export function QueueError({ onRetry, retrying }: { onRetry: () => void; retrying: boolean }) {
  return (
    <div role="alert" className="flex flex-col items-center gap-2 px-4 py-16 text-center">
      <CircleAlert aria-hidden className="size-6 text-danger" />
      <p className="font-medium">Não foi possível carregar a fila</p>
      <p className="text-sm text-text-muted">A API não respondeu. Tentamos de novo automaticamente.</p>
      <Button variant="outline" size="sm" onClick={onRetry} disabled={retrying}>
        <RotateCw aria-hidden className={retrying ? 'animate-spin' : undefined} />
        Tentar de novo
      </Button>
    </div>
  )
}

/** A refresh failed but we still have data: keep it on screen and say so. */
export function StaleBanner({ ago, onRetry, retrying }: { ago: string; onRetry: () => void; retrying: boolean }) {
  return (
    <div
      role="status"
      className="flex flex-wrap items-center gap-2 rounded-md border border-sev-medium-border bg-sev-medium-bg px-3 py-1.5 text-xs"
    >
      <CircleAlert aria-hidden className="size-3.5 text-sev-medium" />
      <span>Não foi possível atualizar a fila. Mostrando os dados de {ago}.</span>
      <Button variant="ghost" size="xs" className="ml-auto" onClick={onRetry} disabled={retrying}>
        <RotateCw aria-hidden className={retrying ? 'animate-spin' : undefined} />
        Tentar de novo
      </Button>
    </div>
  )
}
