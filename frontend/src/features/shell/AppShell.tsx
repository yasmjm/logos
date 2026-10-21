import { useQuery, useQueryClient } from '@tanstack/react-query'
import { useEffect, useRef } from 'react'
import { LogOut } from 'lucide-react'

import { useAppConfig } from '@/api/appConfig'
import { fetchMe } from '@/api/auth'
import { endSession, type Session } from '@/api/session'
import { AssigneeBadge } from '@/components/AssigneeBadge'
import { LogoMark } from '@/components/LogoMark'
import { ThemeToggle } from '@/components/ThemeToggle'
import { Button } from '@/components/ui/button'
import { ChaosBanner } from '@/features/demo/ChaosBanner'
import { DemoMenu } from '@/features/demo/DemoMenu'
import { DriverSimulatorProvider } from '@/features/demo/DriverSimulatorProvider'
import { NewIncidentButton } from '@/features/incident/NewIncidentButton'
import { QueuePage } from '@/features/queue/QueuePage'
import { UpdatedIndicator } from '@/features/queue/UpdatedIndicator'

export function AppShell({ session }: { session: Session }) {
  const queryClient = useQueryClient()
  // Validates the stored token on load; a 401 sends the analyst back to login.
  useQuery({ queryKey: ['me'], queryFn: fetchMe, staleTime: Infinity })
  useAppConfig() // SLA rules and tools, once per session
  const top = useStickyTopHeight()

  function signOut() {
    endSession('logout')
    queryClient.clear()
  }

  return (
    <DriverSimulatorProvider>
      <div className="flex min-h-svh flex-col">
        <div ref={top} className="sticky top-0 z-10">
          <ChaosBanner />
          <header className="flex h-12 items-center gap-3 border-b bg-surface-1 px-4">
          <LogoMark />
          <span className="hidden text-sm text-text-muted sm:inline">Central de Incidentes</span>
          <div className="ml-auto flex items-center gap-1">
            <UpdatedIndicator />
            <NewIncidentButton />
            <DemoMenu />
            <AssigneeBadge analyst={session.analyst} className="mx-2 text-text" />
            <ThemeToggle />
            <Button variant="ghost" size="sm" onClick={signOut}>
              <LogOut aria-hidden />
              Sair
            </Button>
          </div>
          </header>
        </div>

        <main className="flex-1">
          <QueuePage myId={session.analyst.id} />
        </main>
      </div>
    </DriverSimulatorProvider>
  )
}

/** Exposes the sticky top's height (header + chaos banner) as --app-header-h, so the
 *  queue's sticky column header sits right below it. */
function useStickyTopHeight() {
  const ref = useRef<HTMLDivElement>(null)
  useEffect(() => {
    const node = ref.current
    if (!node) return
    const observer = new ResizeObserver(([entry]) => {
      const height = entry?.borderBoxSize[0]?.blockSize ?? node.offsetHeight
      document.documentElement.style.setProperty('--app-header-h', `${height}px`)
    })
    observer.observe(node)
    return () => observer.disconnect()
  }, [])
  return ref
}
