import { useEffect, useState } from 'react'

/** Seconds left from `seconds` (restarts whenever `startedAt` changes). */
export function useCountdown(seconds: number | null, startedAt: number): number {
  const [now, setNow] = useState(() => Date.now())

  useEffect(() => {
    if (seconds === null) return
    const timer = window.setInterval(() => setNow(Date.now()), 250)
    return () => window.clearInterval(timer)
  }, [seconds, startedAt])

  if (seconds === null) return 0
  return Math.max(0, Math.ceil((startedAt + seconds * 1000 - now) / 1000))
}
