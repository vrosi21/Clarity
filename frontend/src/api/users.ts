import client from './client'
import type { User } from '@/types'

export const usersApi = {
  updateSelf: (data: {
    username?: string
    current_password: string
    new_password?: string
  }) => client.patch<User>('/users/me', data).then((r) => r.data),
}
