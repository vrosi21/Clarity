import client from './client'
import type { User } from '@/types'

export interface UserSearchResult {
  id: number
  username: string
  email: string
  full_name: string | null
}

export const usersApi = {
  updateSelf: (data: {
    username?: string
    current_password?: string
    new_password?: string
    bio?: string | null
  }) => client.patch<User>('/users/me', data).then((r) => r.data),

  search: (q: string) =>
    client.get<UserSearchResult[]>('/users/search', { params: { q } }).then((r) => r.data),
}
