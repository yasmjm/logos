import { createContext, useContext } from 'react'

import type { RecentConversation } from '@/api/types'

export interface DriverSimulatorState {
  /** Demo mode is on (the simulator exists). */
  available: boolean
  open: boolean
  /** Conversation shown (WhatsApp id: digits only); remembered per tab. */
  phone: string | null
  setPhone: (phone: string) => void
  openFor: (phone?: string) => void
  close: () => void
  recent: RecentConversation[]
  /** A message was sent to a driver since the simulator was last closed. */
  unread: boolean
}

export const DriverSimulatorContext = createContext<DriverSimulatorState | null>(null)

export function useDriverSimulator(): DriverSimulatorState {
  const state = useContext(DriverSimulatorContext)
  if (!state) throw new Error('useDriverSimulator must be used inside DriverSimulatorProvider')
  return state
}

export const simulatorKeys = {
  all: ['demo', 'whatsapp'] as const,
  recent: ['demo', 'whatsapp', 'recent'] as const,
  thread: (phone: string | null) => ['demo', 'whatsapp', 'thread', phone] as const,
  incident: (id: string) => ['demo', 'whatsapp', 'incident', id] as const,
}
