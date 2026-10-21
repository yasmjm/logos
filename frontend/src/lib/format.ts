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

/** "há 3 s", "há 2 min", for "Atualizado há ...". */
export function formatAgo(ms: number): string {
  const seconds = Math.max(0, Math.floor(ms / 1000))
  if (seconds < 60) return `há ${seconds} s`
  return `há ${Math.floor(seconds / 60)} min`
}

export function wholeMinutes(ms: number): number {
  return Math.max(0, Math.floor(ms / 60_000))
}
