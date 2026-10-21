import { useMutation, useQueryClient } from '@tanstack/react-query'
import { toast } from 'sonner'

import { resetDemoData } from '@/api/demo'
import { ApiError } from '@/api/errors'
import {
  AlertDialog,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
} from '@/components/ui/alert-dialog'
import { Button } from '@/components/ui/button'

export function ResetDialog({ open, onOpenChange }: { open: boolean; onOpenChange: (open: boolean) => void }) {
  const queryClient = useQueryClient()
  const reset = useMutation({
    mutationFn: resetDemoData,
    retry: false,
    onSuccess: (result) => {
      // Clear (not just refetch) so 120 fresh rows load as a first load, without highlights.
      void queryClient.resetQueries({ queryKey: ['incidents'] })
      toast.success(`Dados restaurados: ${result.created} incidentes novos, ${result.deleted} arquivados`)
      onOpenChange(false)
    },
  })

  const error = reset.error
  const message =
    error instanceof ApiError && error.status === 429
      ? `Os dados foram restaurados há pouco. Tente de novo em ${error.retryAfterSeconds ?? 60} s.`
      : error
        ? 'Não foi possível restaurar agora. Tente de novo em instantes.'
        : null

  return (
    <AlertDialog
      open={open}
      onOpenChange={(next) => {
        if (reset.isPending) return
        if (!next) reset.reset()
        onOpenChange(next)
      }}
    >
      <AlertDialogContent>
        <AlertDialogHeader>
          <AlertDialogTitle>Restaurar dados de demonstração?</AlertDialogTitle>
          <AlertDialogDescription>
            Cria de novo os 120 incidentes de exemplo, com horários relativos a agora. Nada é apagado:
            os incidentes atuais são arquivados com o histórico preservado, e fica registrado que você
            pediu a restauração.
          </AlertDialogDescription>
        </AlertDialogHeader>
        {message && (
          <p role="alert" className="text-sm text-danger">
            {message}
          </p>
        )}
        <AlertDialogFooter>
          <AlertDialogCancel disabled={reset.isPending}>Cancelar</AlertDialogCancel>
          <Button onClick={() => reset.mutate()} disabled={reset.isPending}>
            {reset.isPending ? 'Restaurando…' : 'Restaurar'}
          </Button>
        </AlertDialogFooter>
      </AlertDialogContent>
    </AlertDialog>
  )
}
