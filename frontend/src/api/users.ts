import type { components } from './generated/schema'
import { apiClient } from './client'

export type User = components['schemas']['UserResponse']

const BASE_URL = '/users'

export const usersApi = {
  list(): Promise<User[]> {
    return apiClient.get<User[]>(BASE_URL + '/')
  },
}
