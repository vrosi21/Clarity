import client from '@/api/client'
import type { AuthToken, User } from '@/types'

export const authApi = {
  register: (data: { email: string; username: string; password: string }) =>
    client.post<User>('/auth/register', data).then((r) => r.data),
  login: (data: { email: string; password: string }) =>
    client.post<AuthToken>('/auth/login', data).then((r) => r.data),
  me: () => client.get<User>('/auth/me').then((r) => r.data),
}
