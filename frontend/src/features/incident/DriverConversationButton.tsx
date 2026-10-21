import { useQuery } from '@tanstack/react-query'
import { MessageSquareText } from 'lucide-react'

import { fetchIncidentConversation } from '@/api/demo'
import type { Incident } from '@/api/types'
import { Button } from '@/components/ui/button'
import { simulatorKeys, useDriverSimulator } from '@/features/demo/useDriverSimulator'

/** Demo: open the driver simulator on the conversation that created this incident,
 *  e.g. to check the update the driver got when it was taken. */
export function DriverConversationButton({ incident, onOpen }: { incident: Incident; onOpen: () => void }) {
  const simulator = useDriverSimulator()
  const enabled = simulator.available && incident.source === 'whatsapp'
  // Seeded WhatsApp incidents have no conversation (404): no button for them.
  const conversation = useQuery({
    queryKey: simulatorKeys.incident(incident.id),
    queryFn: () => fetchIncidentConversation(incident.id),
    enabled,
    staleTime: Infinity,
  })
  if (!enabled || !conversation.data) return null

  const phone = conversation.data.phone
  return (
    <Button
      type="button"
      variant="outline"
      size="sm"
      className="justify-self-start"
      onClick={() => {
        onOpen()
        simulator.openFor(phone)
      }}
    >
      <MessageSquareText aria-hidden />
      Ver conversa com o motorista
    </Button>
  )
}
