const kmFormat = new Intl.NumberFormat('pt-BR', { minimumFractionDigits: 1, maximumFractionDigits: 1 })

/** "BR-116 km 231,5", "BR-116", "km 231,5" or null when nothing is known. */
export function formatLocation(highway: string | null, km: number | null): string | null {
  const parts = [highway, km === null ? null : `km ${kmFormat.format(km)}`].filter(Boolean)
  return parts.length ? parts.join(' ') : null
}

/** Compact duration for dense rows: "40 s", "12 min", "1 h 05", "2 d 3 h". */
export function formatDuration(ms: number): string {
  const seconds = Math.max(0, Math.floor(ms / 1000))
  if (seconds < 60) return `${seconds} s`
  const minutes = Math.floor(seconds / 60)
  if (minutes < 60) return `${minutes} min`
  const hours = Math.floor(minutes / 60)
  if (hours < 24) return `${hours} h ${String(minutes % 60).padStart(2, '0')}`
  return `${Math.floor(hours / 24)} d ${hours % 24} h`
}

/** "há 3 s", "há 2 min", "há 4 h", "há 2 d". */
export function formatAgo(ms: number): string {
  const seconds = Math.max(0, Math.floor(ms / 1000))
  if (seconds < 60) return `há ${seconds} s`
  const minutes = Math.floor(seconds / 60)
  if (minutes < 60) return `há ${minutes} min`
  const hours = Math.floor(minutes / 60)
  if (hours < 24) return `há ${hours} h`
  return `há ${Math.floor(hours / 24)} d`
}

const clockFormat = new Intl.DateTimeFormat('pt-BR', { hour: '2-digit', minute: '2-digit' })
const fullFormat = new Intl.DateTimeFormat('pt-BR', { dateStyle: 'short', timeStyle: 'medium' })

/** "14:32" */
export function formatClock(iso: string): string {
  return clockFormat.format(new Date(iso))
}

/** "21/10/2026, 14:32:05" (tooltips). */
export function formatDateTime(iso: string): string {
  return fullFormat.format(new Date(iso))
}

export function wholeMinutes(ms: number): number {
  return Math.max(0, Math.floor(ms / 60_000))
}

/** "3 min 12 s", "1 h 05 min", "45 s" (business-friendly averages). */
export function formatSeconds(totalSeconds: number): string {
  const seconds = Math.round(totalSeconds)
  if (seconds < 60) return `${seconds} s`
  const minutes = Math.floor(seconds / 60)
  if (minutes < 60) return `${minutes} min ${String(seconds % 60).padStart(2, '0')} s`
  const hours = Math.floor(minutes / 60)
  return `${hours} h ${String(minutes % 60).padStart(2, '0')} min`
}
