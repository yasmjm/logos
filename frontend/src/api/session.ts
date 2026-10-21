/**
 * The analyst session: JWT in memory, mirrored to sessionStorage so a reload keeps
 * you logged in. sessionStorage is per tab, so Ana and Bruno can use two tabs.
 */
import { useSyncExternalStore } from 'react'

import type { Analyst } from '@/api/types'
import { readStorage, writeStorage } from '@/lib/storage'

export interface Session {
  token: string
  analyst: Analyst
}

export type SessionEndReason = 'expired' | 'logout'

const STORAGE_KEY = 'logos.session'
const listeners = new Set<() => void>()

let session: Session | null = load()
let endReason: SessionEndReason | null = null

function load(): Session | null {
  const raw = readStorage('session', STORAGE_KEY)
  if (!raw) return null
  try {
    const parsed = JSON.parse(raw) as Partial<Session>
    return typeof parsed.token === 'string' && parsed.analyst ? (parsed as Session) : null
  } catch {
    return null
  }
}

function emit(): void {
  listeners.forEach((notify) => notify())
}

export function getSession(): Session | null {
  return session
}

export function startSession(next: Session): void {
  session = next
  endReason = null
  writeStorage('session', STORAGE_KEY, JSON.stringify(next))
  emit()
}

export function endSession(reason: SessionEndReason): void {
  if (!session) return
  session = null
  endReason = reason
  writeStorage('session', STORAGE_KEY, null)
  emit()
}

/** Why the last session ended ("Sua sessão expirou"), read once by the login screen. */
export function takeEndReason(): SessionEndReason | null {
  const reason = endReason
  endReason = null
  return reason
}

function subscribe(notify: () => void): () => void {
  listeners.add(notify)
  return () => listeners.delete(notify)
}

export function useSession(): Session | null {
  return useSyncExternalStore(subscribe, getSession, () => null)
}
