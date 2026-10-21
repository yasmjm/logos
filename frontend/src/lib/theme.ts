import { useCallback, useSyncExternalStore } from 'react'

import { readStorage, writeStorage } from '@/lib/storage'

export type Theme = 'dark' | 'light'

const STORAGE_KEY = 'logos.theme' // also read by the inline script in index.html
const listeners = new Set<() => void>()

function currentTheme(): Theme {
  return document.documentElement.dataset.theme === 'light' ? 'light' : 'dark'
}

export function setTheme(theme: Theme): void {
  document.documentElement.dataset.theme = theme
  writeStorage('local', STORAGE_KEY, theme)
  listeners.forEach((notify) => notify())
}

/** Dark is the default; the saved preference is applied by index.html before paint. */
export function initTheme(): void {
  const saved = readStorage('local', STORAGE_KEY)
  document.documentElement.dataset.theme = saved === 'light' ? 'light' : 'dark'
}

export function useTheme(): { theme: Theme; toggle: () => void } {
  const theme = useSyncExternalStore(
    (notify) => {
      listeners.add(notify)
      return () => listeners.delete(notify)
    },
    currentTheme,
    () => 'dark' as const,
  )
  const toggle = useCallback(() => setTheme(theme === 'dark' ? 'light' : 'dark'), [theme])
  return { theme, toggle }
}
