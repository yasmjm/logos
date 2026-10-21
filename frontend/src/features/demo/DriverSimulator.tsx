import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { Bot, SendHorizontal } from 'lucide-react'
import { type FormEvent, useEffect, useRef, useState } from 'react'
import { toast } from 'sonner'

import { fetchConversation, fetchFleet, sendDriverMessage } from '@/api/demo'
import type { ConversationMessage } from '@/api/types'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { Sheet, SheetContent, SheetDescription, SheetHeader, SheetTitle } from '@/components/ui/sheet'
import { simulatorKeys, useDriverSimulator } from '@/features/demo/useDriverSimulator'
import { cn } from '@/lib/utils'

const POLL_MS = 2000
const time = new Intl.DateTimeFormat('pt-BR', { hour: '2-digit', minute: '2-digit' })

/** Fictitious phone per truck (WhatsApp ids are digits only): TRK-1001 -> 5511990001001. */
function phoneOf(truckCode: string): string {
  return `5511990${truckCode.replace(/\D/g, '').padStart(6, '0')}`
}

/** Demo: chat as a driver with the triage bot. Opens on the left, so the queue (and the
 *  incident panel on the right) stay usable while the conversation goes on. */
export function DriverSimulator() {
  const simulator = useDriverSimulator()
  return (
    <Sheet open={simulator.open} onOpenChange={(next) => (next ? simulator.openFor() : simulator.close())} modal={false}>
      <SheetContent
        side="left"
        className="w-full gap-0 border-border-strong bg-surface-1 p-0 sm:max-w-[400px]"
        onInteractOutside={(event) => event.preventDefault()}
      >
        {simulator.open && <Chat />}
      </SheetContent>
    </Sheet>
  )
}

function Chat() {
  const queryClient = useQueryClient()
  const simulator = useDriverSimulator()
  const fleet = useQuery({ queryKey: ['demo', 'fleet'], queryFn: fetchFleet, staleTime: Infinity })
  const firstTruck = fleet.data?.[0]?.code
  // Last conversation of this tab, or the first truck of the fleet.
  const phone = simulator.phone ?? (firstTruck ? phoneOf(firstTruck) : null)
  const truckCode = fleet.data?.find((t) => phoneOf(t.code) === phone)?.code ?? null

  const thread = useQuery({
    queryKey: simulatorKeys.thread(phone),
    queryFn: () => fetchConversation(phone as string),
    enabled: phone !== null,
    refetchInterval: POLL_MS,
  })

  const [draft, setDraft] = useState('')
  const send = useMutation({
    mutationFn: (text: string) => sendDriverMessage(phone as string, text),
    retry: false,
    onMutate: () => {
      // Remember this conversation for the tab (also when it is the default truck).
      if (phone && simulator.phone !== phone) simulator.setPhone(phone)
    },
    onSuccess: (reply) => {
      void queryClient.invalidateQueries({ queryKey: simulatorKeys.all })
      // The incident was created: refetch the queue so it arrives with the highlight.
      if (reply.replies.some((text) => text.includes('protocolo'))) {
        void queryClient.invalidateQueries({ queryKey: ['incidents'] })
      }
    },
    onError: () => toast.error('Não foi possível enviar a mensagem.'),
  })

  const submit = (event: FormEvent) => {
    event.preventDefault()
    const text = draft.trim()
    if (!text || send.isPending) return
    // Cleared now, not on success: the driver may already be typing the next answer.
    setDraft('')
    send.mutate(text, { onError: () => setDraft((current) => current || text) })
  }

  const messages = thread.data?.messages ?? []
  const options = thread.data?.options ?? []
  const waitingTruck = thread.data?.step === 'truck'

  return (
    <div className="flex h-full min-h-0 flex-col">
      <SheetHeader className="gap-3 border-b p-4">
        <div className="flex items-center gap-2.5">
          <span className="inline-flex size-9 items-center justify-center rounded-full bg-surface-3">
            <Bot aria-hidden className="size-5" />
          </span>
          <div>
            <SheetTitle className="text-base">Simulador do motorista</SheetTitle>
            <SheetDescription className="text-xs">
              Logos Motorista · triagem automática no WhatsApp (simulado)
            </SheetDescription>
          </div>
        </div>
        <div className="grid gap-1">
          <Label htmlFor="sim-truck" className="text-xs text-text-muted">
            Você é o motorista do caminhão
          </Label>
          <Select
            value={truckCode ?? undefined}
            onValueChange={(code) => simulator.setPhone(phoneOf(code))}
            disabled={!fleet.data}
          >
            <SelectTrigger id="sim-truck" className="w-full">
              <SelectValue placeholder="Carregando a frota…" />
            </SelectTrigger>
            <SelectContent className="max-h-72">
              {fleet.data?.map((t) => (
                <SelectItem key={t.code} value={t.code}>
                  <span className="font-mono">{t.code}</span>
                  <span className="text-text-muted"> · {t.client_name}</span>
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>
        <RecentConversations current={phone} />
      </SheetHeader>

      <MessageList messages={messages} empty={thread.isSuccess && messages.length === 0} />

      <div className="grid gap-2 border-t p-3">
        {(options.length > 0 || waitingTruck) && (
          <div className="flex flex-wrap gap-1.5" aria-label="Respostas rápidas">
            {(waitingTruck && truckCode ? [truckCode] : options).map((option) => (
              <Button
                key={option}
                type="button"
                size="sm"
                variant="outline"
                disabled={send.isPending}
                onClick={() => send.mutate(option)}
              >
                {option}
              </Button>
            ))}
          </div>
        )}
        <form onSubmit={submit} className="flex gap-2">
          <Input
            value={draft}
            onChange={(event) => setDraft(event.target.value)}
            placeholder={messages.length ? 'Mensagem' : 'Diga "oi" para começar'}
            aria-label="Mensagem do motorista"
            maxLength={1000}
            disabled={!phone}
          />
          <Button type="submit" size="icon" aria-label="Enviar" disabled={!draft.trim() || send.isPending}>
            <SendHorizontal aria-hidden />
          </Button>
        </form>
      </div>
    </div>
  )
}

function MessageList({ messages, empty }: { messages: ConversationMessage[]; empty: boolean }) {
  const end = useRef<HTMLDivElement>(null)
  useEffect(() => {
    end.current?.scrollIntoView({ block: 'end' })
  }, [messages.length])

  return (
    <div className="min-h-0 flex-1 overflow-y-auto bg-bg px-3 py-4" aria-live="polite">
      {empty && (
        <p className="mt-8 text-center text-sm text-text-muted">
          Nenhuma conversa ainda. Mande uma mensagem como o motorista.
        </p>
      )}
      <ol className="grid gap-2">
        {messages.map((message) => {
          const driver = message.direction === 'in'
          return (
            <li key={message.id} className={cn('flex', driver ? 'justify-end' : 'justify-start')}>
              <div
                className={cn(
                  'max-w-[85%] rounded-lg px-3 py-2 text-sm whitespace-pre-line',
                  driver
                    ? 'rounded-br-sm bg-chat-driver text-chat-driver-text'
                    : 'rounded-bl-sm border bg-surface-2 text-text',
                )}
              >
                <span className="sr-only">{driver ? 'Motorista: ' : 'Central: '}</span>
                {message.text}
                <time
                  dateTime={message.created_at}
                  className="mt-0.5 block text-right text-xs opacity-70"
                >
                  {time.format(new Date(message.created_at))}
                </time>
              </div>
            </li>
          )
        })}
      </ol>
      <div ref={end} />
    </div>
  )
}

/** One click to switch between the drivers that have talked to the bot. */
function RecentConversations({ current }: { current: string | null }) {
  const simulator = useDriverSimulator()
  if (!simulator.recent.length) return null
  return (
    <div className="grid gap-1">
      <span id="sim-recent" className="text-xs text-text-muted">
        Conversas recentes
      </span>
      <div role="group" aria-labelledby="sim-recent" className="flex flex-wrap gap-1">
        {simulator.recent.map((conversation) => (
          <Button
            key={conversation.phone}
            type="button"
            size="sm"
            variant="outline"
            aria-pressed={conversation.phone === current}
            onClick={() => simulator.setPhone(conversation.phone)}
            className={cn(
              'h-7 px-2 font-mono text-xs',
              conversation.phone === current && 'border-border-strong bg-surface-3',
            )}
          >
            {conversation.truck_code ?? `…${conversation.phone.slice(-4)}`}
          </Button>
        ))}
      </div>
    </div>
  )
}
