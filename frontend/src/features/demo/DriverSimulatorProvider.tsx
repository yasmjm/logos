import { useQuery } from '@tanstack/react-query'
import { type ReactNode, useCallback, useMemo, useState } from 'react'

import { useAppConfig } from '@/api/appConfig'
import { fetchRecentConversations } from '@/api/demo'
import { DriverSimulator } from '@/features/demo/DriverSimulator'
import { DriverSimulatorContext, simulatorKeys } from '@/features/demo/useDriverSimulator'
import { readStorage, writeStorage } from '@/lib/storage'

const PHONE_KEY = 'logos.simulator.phone'
const SEEN_KEY = 'logos.simulator.seen-at'
const RECENT_POLL_MS = 5000

const time = (iso: string) => Date.parse(iso)

function latest(dates: (string | null)[]): string | null {
  return dates.reduce<string | null>((max, d) => (d && (!max || time(d) > time(max)) ? d : max), null)
}

/** Shares the driver simulator between the demo menu and the incident panel. */
export function DriverSimulatorProvider({ children }: { children: ReactNode }) {
  const available = useAppConfig().data?.features.demo ?? false
  const [open, setOpen] = useState(false)
  const [phone, setPhoneState] = useState(() => readStorage('session', PHONE_KEY))
  const [seenAt, setSeenAt] = useState(() => readStorage('session', SEEN_KEY))

  const recent = useQuery({
    queryKey: simulatorKeys.recent,
    queryFn: fetchRecentConversations,
    enabled: available,
    refetchInterval: RECENT_POLL_MS,
    refetchIntervalInBackground: false,
  })
  const lastSent = latest((recent.data ?? []).map((c) => c.last_out_at))

  const setPhone = useCallback((next: string) => {
    setPhoneState(next)
    writeStorage('session', PHONE_KEY, next)
  }, [])

  const openFor = useCallback(
    (next?: string) => {
      if (next) setPhone(next)
      setOpen(true)
    },
    [setPhone],
  )

  const close = useCallback(() => {
    setOpen(false)
    // Everything sent while it was open has been seen.
    if (lastSent) {
      setSeenAt(lastSent)
      writeStorage('session', SEEN_KEY, lastSent)
    }
  }, [lastSent])

  const unread = !open && seenAt !== null && lastSent !== null && time(lastSent) > time(seenAt)

  const value = useMemo(
    () => ({ available, open, phone, setPhone, openFor, close, recent: recent.data ?? [], unread }),
    [available, open, phone, setPhone, openFor, close, recent.data, unread],
  )

  return (
    <DriverSimulatorContext.Provider value={value}>
      {children}
      {available && <DriverSimulator />}
    </DriverSimulatorContext.Provider>
  )
}
