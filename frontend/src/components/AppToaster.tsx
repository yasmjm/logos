import { Toaster } from 'sonner'

import { useTheme } from '@/lib/theme'

/** Short confirmations ("Incidente assumido"), announced to screen readers by sonner. */
export function AppToaster() {
  const { theme } = useTheme()
  return (
    <Toaster
      theme={theme}
      position="bottom-right"
      duration={3000}
      toastOptions={{
        style: {
          background: 'var(--surface-2)',
          color: 'var(--text)',
          border: '1px solid var(--border-strong)',
          fontFamily: 'var(--font-sans)',
        },
      }}
    />
  )
}
