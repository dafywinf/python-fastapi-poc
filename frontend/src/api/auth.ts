import type { components } from './generated/schema'
import { apiClient } from './client'

export type TokenResponse = components['schemas']['TokenResponse']

export async function loginWithPassword(
  username: string,
  password: string,
): Promise<TokenResponse> {
  const body = new URLSearchParams()
  body.set('username', username)
  body.set('password', password)

  return apiClient.post<TokenResponse>('/auth/token', body, {
    headers: {
      'Content-Type': 'application/x-www-form-urlencoded',
    },
  })
}
