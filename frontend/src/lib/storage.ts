/**
 * Web Storage can throw (private mode, blocked site data, quota). Every access
 * goes through these helpers so the app keeps working without persistence.
 */
type Area = 'local' | 'session'

function area(kind: Area): Storage | null {
  try {
    return kind === 'local' ? window.localStorage : window.sessionStorage
  } catch {
    return null
  }
}

export function readStorage(kind: Area, key: string): string | null {
  try {
    return area(kind)?.getItem(key) ?? null
  } catch {
    return null
  }
}

export function writeStorage(kind: Area, key: string, value: string | null): void {
  try {
    const store = area(kind)
    if (value === null) store?.removeItem(key)
    else store?.setItem(key, value)
  } catch {
    // Persistence is a convenience; ignore failures.
  }
}
