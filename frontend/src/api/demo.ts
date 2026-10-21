import { apiRequest } from '@/api/client'
import type { ChaosConfig, ChaosStatus, DemoResetResponse, DemoSimulateResponse } from '@/api/types'

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
