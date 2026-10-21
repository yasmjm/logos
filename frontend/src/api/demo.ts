import { apiRequest } from '@/api/client'
import type {
  BotReply,
  ChaosConfig,
  ChaosStatus,
  ConversationThread,
  DemoResetResponse,
  DemoSimulateResponse,
  FleetTruck,
} from '@/api/types'

export function simulateIncidents(count: number): Promise<DemoSimulateResponse> {
  return apiRequest('/demo/simulate', { method: 'POST', query: { count } })
}

export function resetDemoData(): Promise<DemoResetResponse> {
  return apiRequest('/demo/reset', { method: 'POST' })
}

export function fetchChaos(): Promise<ChaosStatus> {
  return apiRequest('/chaos')
}

export function updateChaos(config: ChaosConfig): Promise<ChaosStatus> {
  return apiRequest('/chaos', { method: 'PUT', json: config })
}

export function fetchFleet(): Promise<FleetTruck[]> {
  return apiRequest('/demo/fleet')
}

export function fetchConversation(phone: string): Promise<ConversationThread> {
  return apiRequest(`/demo/whatsapp/conversations/${phone}/messages`)
}

export function sendDriverMessage(phone: string, text: string): Promise<BotReply> {
  return apiRequest('/demo/whatsapp/messages', { method: 'POST', json: { phone, text } })
}
