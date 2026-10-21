/**
 * Every user-facing label for domain values, in one place.
 * Status and category texts follow the case statement exactly.
 */
import type { IncidentCategory, IncidentSource, IncidentStatus, Severity } from '@/api/types'

export const STATUS_LABELS: Record<IncidentStatus, string> = {
  open: 'Aberto',
  investigating: 'Em Investigação',
  closed: 'Fechado',
  inconclusive: 'Inconclusivo',
}

export const CATEGORY_LABELS: Record<IncidentCategory, string> = {
  vehicle_accident: 'Acidente com Veículo',
  accident_with_victims: 'Acidente com Vítimas',
  adverse_weather: 'Condição Climática Atípica na Pista',
  mechanical_failure: 'Problema Mecânico',
  road_blockage: 'Bloqueio de Pista',
}

export const SEVERITY_LABELS: Record<Severity, string> = {
  high: 'Alta',
  medium: 'Média',
  low: 'Baixa',
}

export const SOURCE_LABELS: Record<IncidentSource, string> = {
  api: 'Integração',
  whatsapp: 'WhatsApp',
}
