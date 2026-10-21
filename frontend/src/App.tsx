import { useQueryClient } from '@tanstack/react-query'
import { useEffect } from 'react'

import { useSession } from '@/api/session'
import { LoginPage } from '@/features/auth/LoginPage'
import { AppShell } from '@/features/shell/AppShell'

export default function App() {
  const session = useSession()
  const queryClient = useQueryClient()

  // Never show one analyst's cached data to the next one.
  useEffect(() => {
    if (!session) queryClient.removeQueries({ predicate: (q) => q.queryKey[0] !== 'readiness' })
  }, [session, queryClient])

  return session ? <AppShell session={session} /> : <LoginPage />
}
