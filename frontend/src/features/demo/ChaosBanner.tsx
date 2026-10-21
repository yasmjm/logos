import { useMutation, useQueryClient } from '@tanstack/react-query'
import { Zap } from 'lucide-react'
import { toast } from 'sonner'

import { updateChaos } from '@/api/demo'
import { Button } from '@/components/ui/button'
import { chaosKey, useChaosStatus } from '@/features/demo/useChaosStatus'
import { useNow } from '@/lib/useNow'

function countdown(ms: number): string {
  const total = Math.max(0, Math.ceil(ms / 1000))
  return `${Math.floor(total / 60)}:${String(total % 60).padStart(2, '0')}`
}

/** Fixed notice while chaos mode is active; disappears when it expires or is turned off. */
export function ChaosBanner() {
  const chaos = useChaosStatus()
  const now = useNow()
  const queryClient = useQueryClient()
  const turnOff = useMutation({
    mutationFn: () => updateChaos({ latency_ms: 0, failure_rate: 0 }),
    retry: false,
    onSuccess: (status) => {
      queryClient.setQueryData(chaosKey, status)
      toast.success('Modo caos desligado')
    },
    onError: () => toast.error('Não foi possível desligar o modo caos. Tente de novo.'),
  })

  const status = chaos.data
  const left = status?.expires_at ? Date.parse(status.expires_at) - now : 0
  if (!status?.active || left <= 0) return null

  return (
    <div
      role="status"
      className="flex flex-wrap items-center gap-x-3 gap-y-1 border-b border-sev-medium-border bg-sev-medium-bg px-4 py-1.5 text-xs"
    >
      <Zap aria-hidden className="size-3.5 shrink-0 text-sev-medium" />
      <span className="font-medium text-text">
        Modo caos ativo: {status.latency_ms} ms de latência e {Math.round(status.failure_rate * 100)}% de
        falhas · desliga sozinho em <span className="tabular-nums">{countdown(left)}</span>
      </span>
      <Button
        variant="outline"
        size="xs"
        className="ml-auto"
        onClick={() => turnOff.mutate()}
        disabled={turnOff.isPending}
      >
        {turnOff.isPending ? 'Desligando…' : 'Desligar'}
      </Button>
    </div>
  )
}
