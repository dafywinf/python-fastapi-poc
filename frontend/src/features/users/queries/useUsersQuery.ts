import { useQuery } from '@tanstack/vue-query'
import { usersApi } from '../../../api/users'

export function useUsersQuery() {
  return useQuery({
    queryKey: ['users'],
    queryFn: usersApi.list,
  })
}
