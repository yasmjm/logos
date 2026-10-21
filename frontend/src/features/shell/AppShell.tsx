import { useQuery, useQueryClient } from '@tanstack/react-query'
import { Construction, LogOut } from 'lucide-react'

import { fetchMe } from '@/api/auth'
import { endSession, type Session } from '@/api/session'
import { AssigneeBadge } from '@/components/AssigneeBadge'
import { LogoMark } from '@/components/LogoMark'
import { ThemeToggle } from '@/components/ThemeToggle'
import { Button } from '@/components/ui/button'

export function AppShell({ session }: { session: Session }) {
  const queryClient = useQueryClient()
  // Validates the stored token on load; a 401 sends the analyst back to login.
  useQuery({ queryKey: ['me'], queryFn: fetchMe, staleTime: Infinity })

  function signOut() {
    endSession('logout')
    queryClient.clear()
  }

  return (
    <div className="flex min-h-svh flex-col">
      <header className="sticky top-0 z-10 flex h-12 items-center gap-3 border-b bg-surface-1 px-4">
        <LogoMark />
        <span className="hidden text-sm text-text-muted sm:inline">Central de Incidentes</span>
        <div className="ml-auto flex items-center gap-1">
          <AssigneeBadge analyst={session.analyst} className="mr-2 text-text" />
          <ThemeToggle />
          <Button variant="ghost" size="sm" onClick={signOut}>
            <LogOut aria-hidden />
            Sair
          </Button>
        </div>
      </header>

      <main className="flex flex-1 items-center justify-center p-6">
        <div className="flex flex-col items-center gap-2 text-center text-text-muted">
          <Construction aria-hidden className="size-6" />
          <p className="text-lg font-medium text-text">Fila de incidentes — em construção</p>
          <p className="text-sm">A fila priorizada chega na próxima etapa.</p>
        </div>
      </main>
    </div>
  )
}
