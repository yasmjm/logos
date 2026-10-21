const configured = import.meta.env.VITE_API_URL?.trim()

if (!configured && import.meta.env.PROD) {
  throw new Error('VITE_API_URL is not set for this build.')
}

/** Base URL of the Logos API, without a trailing slash. */
export const API_URL = (configured || 'http://localhost:8000').replace(/\/+$/, '')
