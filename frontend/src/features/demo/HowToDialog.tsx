import { Dialog, DialogContent, DialogDescription, DialogHeader, DialogTitle } from '@/components/ui/dialog'

const STEPS = [
  {
    title: 'Conflito entre analistas',
    text: 'Abra duas abas: entre como Ana numa e como Bruno na outra. Abram o mesmo incidente aberto e cliquem em "Assumir" quase juntos. Quem chegar depois vê quem assumiu e há quanto tempo, sem nada ser sobrescrito.',
  },
  {
    title: 'Incidentes chegando',
    text: 'Use "Simular incidentes" neste menu. Os novos entram na fila na ordem de prioridade, com um destaque breve, e os indicadores se atualizam.',
  },
  {
    title: 'Falhas e lentidão',
    text: 'Ligue o "Modo caos" com latência e taxa de falha. A fila continua mostrando os últimos dados, e as ações oferecem "Tentar de novo" sem risco de duplicar. Ele desliga sozinho em 3 minutos.',
  },
]

export function HowToDialog({ open, onOpenChange }: { open: boolean; onOpenChange: (open: boolean) => void }) {
  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>Como testar</DialogTitle>
          <DialogDescription>Três roteiros rápidos para ver o Logos sob pressão.</DialogDescription>
        </DialogHeader>
        <ol className="grid gap-4">
          {STEPS.map((step, index) => (
            <li key={step.title} className="flex gap-3">
              <span
                aria-hidden
                className="inline-flex size-6 shrink-0 items-center justify-center rounded-full bg-surface-3 text-xs font-semibold"
              >
                {index + 1}
              </span>
              <div className="grid gap-0.5">
                <p className="font-medium">{step.title}</p>
                <p className="text-sm text-text-muted">{step.text}</p>
              </div>
            </li>
          ))}
        </ol>
      </DialogContent>
    </Dialog>
  )
}
