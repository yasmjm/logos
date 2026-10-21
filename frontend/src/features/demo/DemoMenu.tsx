import { useMutation, useQueryClient } from '@tanstack/react-query'
import { CircleHelp, FlaskConical, History, Plus, Zap } from 'lucide-react'
import { useState } from 'react'
import { toast } from 'sonner'

import { useAppConfig } from '@/api/appConfig'
import { simulateIncidents } from '@/api/demo'
import { ApiError } from '@/api/errors'
import { Button } from '@/components/ui/button'
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu'
import { ChaosDialog } from '@/features/demo/ChaosDialog'
import { HowToDialog } from '@/features/demo/HowToDialog'
import { ResetDialog } from '@/features/demo/ResetDialog'
import { useChaosStatus } from '@/features/demo/useChaosStatus'

type Open = 'reset' | 'chaos' | 'howto' | null

/** Only rendered when the API offers demo or chaos tools (GET /config). */
export function DemoMenu() {
  const features = useAppConfig().data?.features
  const chaos = useChaosStatus()
  const queryClient = useQueryClient()
  const [open, setOpen] = useState<Open>(null)

  const simulate = useMutation({
    mutationFn: simulateIncidents,
    retry: false,
    onSuccess: (result) => {
      const count = result.items.length
      toast.success(count === 1 ? '1 incidente chegou' : `${count} incidentes chegaram`)
      // Same queries, refetched: the new rows get the arrival highlight.
      void queryClient.invalidateQueries({ queryKey: ['incidents'] })
    },
    onError: (error) =>
      toast.error(
        error instanceof ApiError && error.status === 429
          ? `Muitas simulações seguidas. Tente de novo em ${error.retryAfterSeconds ?? 60} s.`
          : 'Não foi possível simular agora.',
      ),
  })

  if (!features || (!features.demo && !features.chaos)) return null

  return (
    <>
      <DropdownMenu>
        <DropdownMenuTrigger asChild>
          <Button variant="ghost" size="sm">
            <FlaskConical aria-hidden />
            <span className="hidden sm:inline">Demonstração</span>
          </Button>
        </DropdownMenuTrigger>
        <DropdownMenuContent align="end" className="w-64">
          {features.demo && (
            <>
              <DropdownMenuLabel>Simular incidentes</DropdownMenuLabel>
              {[1, 5].map((count) => (
                <DropdownMenuItem key={count} disabled={simulate.isPending} onSelect={() => simulate.mutate(count)}>
                  <Plus aria-hidden />
                  {count === 1 ? 'Simular 1 incidente' : `Simular ${count} incidentes`}
                </DropdownMenuItem>
              ))}
              <DropdownMenuSeparator />
              <DropdownMenuItem onSelect={() => setOpen('reset')}>
                <History aria-hidden />
                Restaurar dados de demonstração
              </DropdownMenuItem>
            </>
          )}
          {features.chaos && (
            <DropdownMenuItem onSelect={() => setOpen('chaos')}>
              <Zap aria-hidden />
              Modo caos{chaos.data?.active ? ' (ativo)' : ''}
            </DropdownMenuItem>
          )}
          <DropdownMenuSeparator />
          <DropdownMenuItem onSelect={() => setOpen('howto')}>
            <CircleHelp aria-hidden />
            Como testar
          </DropdownMenuItem>
        </DropdownMenuContent>
      </DropdownMenu>

      {features.demo && <ResetDialog open={open === 'reset'} onOpenChange={(next) => setOpen(next ? 'reset' : null)} />}
      {features.chaos && open === 'chaos' && (
        <ChaosDialog open current={chaos.data} onOpenChange={(next) => setOpen(next ? 'chaos' : null)} />
      )}
      <HowToDialog open={open === 'howto'} onOpenChange={(next) => setOpen(next ? 'howto' : null)} />
    </>
  )
}
