import type { AppConfig, Incident } from '@/api/types'
import { CARGO_LABELS, CLIENT_TIER_LABELS } from '@/lib/labels'

const number = new Intl.NumberFormat('pt-BR', { maximumFractionDigits: 1 })

export function formatNumber(value: number | undefined): string {
  return value === undefined ? '…' : number.format(value)
}

/** One-line arithmetic of the score, e.g. for the queue tooltip:
 *  "Carga perecível 90 × 2 · Problema 30 × 1,5 · Cliente estratégico 100 × 1 = 72,2 · +13 de espera = 85". */
export function priorityFormula(
  incident: Incident,
  weights: AppConfig['priority']['weights'] | undefined,
): string {
  const b = incident.priority_breakdown
  if (b.victims) return 'Há vítimas: prioridade máxima'
  const parts = [
    `${CARGO_LABELS[incident.cargo_type]} ${b.cargo_points} × ${formatNumber(weights?.cargo)}`,
    `Problema ${b.problem_points} × ${formatNumber(weights?.problem)}`,
    `${CLIENT_TIER_LABELS[incident.client_tier]} ${b.client_points} × ${formatNumber(weights?.client)}`,
  ]
  const wait = b.wait_bonus > 0 ? ` · +${b.wait_bonus} de espera` : ''
  return `${parts.join(' · ')} = ${number.format(b.base)}${wait} = ${incident.priority_score}`
}
