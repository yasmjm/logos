import { apiRequest } from '@/api/client'
import type { Analyst, TokenResponse } from '@/api/types'

export function login(username: string, password: string): Promise<TokenResponse> {
  // OAuth2 password flow: form-encoded, same as Swagger's Authorize button.
  return apiRequest<TokenResponse>('/auth/login', {
    method: 'POST',
    form: new URLSearchParams({ username, password }),
    auth: false,
  })
}

export function fetchMe(): Promise<Analyst> {
  return apiRequest<Analyst>('/auth/me')
}
