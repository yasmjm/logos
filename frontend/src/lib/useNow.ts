import { useSyncExternalStore } from 'react'

/** One shared 1-second clock for the whole app (not one timer per row). */
const listeners = new Set<() => void>()
let now = Date.now()
let timer: number | undefined

function subscribe(notify: () => void): () => void {
  listeners.add(notify)
  if (timer === undefined) {
    timer = window.setInterval(() => {
      now = Date.now()
      listeners.forEach((listener) => listener())
    }, 1000)
  }
  return () => {
    listeners.delete(notify)
    if (listeners.size === 0) {
      window.clearInterval(timer)
      timer = undefined
    }
  }
}

export function useNow(): number {
  return useSyncExternalStore(subscribe, () => now, () => now)
}
