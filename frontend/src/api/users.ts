export interface User {
  id: number
  email: string
  name: string
  picture: string | null
  created_at: string
}

const BASE_URL = '/users'

async function request<T>(url: string): Promise<T> {
  const response = await fetch(url)
  if (!response.ok) {
    const detail = await response.json().catch(() => ({ detail: response.statusText }))
    throw new Error((detail as { detail?: string }).detail ?? response.statusText)
  }
  return response.json() as Promise<T>
}

export const usersApi = {
  list(): Promise<User[]> {
    return request<User[]>(BASE_URL + '/')
  },
}
