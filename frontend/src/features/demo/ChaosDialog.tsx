import { useMutation, useQueryClient } from '@tanstack/react-query'
import { useState } from 'react'
import { toast } from 'sonner'

import { updateChaos } from '@/api/demo'
import type { ChaosStatus } from '@/api/types'
import { Button } from '@/components/ui/button'
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog'
import { Label } from '@/components/ui/label'
import { chaosKey } from '@/features/demo/useChaosStatus'

const MAX_LATENCY_MS = 3000
const MAX_FAILURE_PERCENT = 50

export function ChaosDialog({
  open,
  current,
  onOpenChange,
}: {
  open: boolean
  current: ChaosStatus | undefined
  onOpenChange: (open: boolean) => void
}) {
  const queryClient = useQueryClient()
  const [latency, setLatency] = useState(current?.active ? current.latency_ms : 800)
  const [failure, setFailure] = useState(
    current?.active ? Math.round(current.failure_rate * 100) : 30,
  )

  const save = useMutation({
    mutationFn: (next: { latency_ms: number; failure_rate: number }) => updateChaos(next),
    retry: false,
    onSuccess: (status) => {
      queryClient.setQueryData(chaosKey, status)
      toast.success(status.active ? 'Modo caos aplicado por 3 minutos' : 'Modo caos desligado')
      onOpenChange(false)
    },
    onError: () => toast.error('Não foi possível mudar o modo caos. Tente de novo.'),
  })

  return (
    <Dialog open={open} onOpenChange={(next) => !save.isPending && onOpenChange(next)}>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>Modo caos</DialogTitle>
          <DialogDescription>
            Injeta latência e falhas (503) nas chamadas da fila para mostrar a interface segurando os
            erros. Desliga sozinho em 3 minutos.
          </DialogDescription>
        </DialogHeader>
        <div className="grid gap-5">
          <div className="grid gap-2">
            <div className="flex items-center justify-between">
              <Label htmlFor="chaos-latency">Latência</Label>
              <span className="text-sm font-semibold tabular-nums">{latency} ms</span>
            </div>
            <input
              id="chaos-latency"
              type="range"
              min={0}
              max={MAX_LATENCY_MS}
              step={100}
              value={latency}
              onChange={(e) => setLatency(Number(e.target.value))}
              className="w-full accent-[var(--accent)]"
            />
          </div>
          <div className="grid gap-2">
            <div className="flex items-center justify-between">
              <Label htmlFor="chaos-failure">Taxa de falha</Label>
              <span className="text-sm font-semibold tabular-nums">{failure}%</span>
            </div>
            <input
              id="chaos-failure"
              type="range"
              min={0}
              max={MAX_FAILURE_PERCENT}
              step={5}
              value={failure}
              onChange={(e) => setFailure(Number(e.target.value))}
              className="w-full accent-[var(--accent)]"
            />
          </div>
        </div>
        <DialogFooter>
          <Button
            variant="outline"
            disabled={save.isPending}
            onClick={() => save.mutate({ latency_ms: 0, failure_rate: 0 })}
          >
            Desligar
          </Button>
          <Button
            disabled={save.isPending || (latency === 0 && failure === 0)}
            onClick={() => save.mutate({ latency_ms: latency, failure_rate: failure / 100 })}
          >
            {save.isPending ? 'Aplicando…' : 'Aplicar'}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}
