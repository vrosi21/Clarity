import client from '@/api/client'
import type { Member } from '@/types'

export const membersApi = {
  list: (projectId: number) =>
    client.get<Member[]>(`/projects/${projectId}/members`).then((r) => r.data),
  add: (projectId: number, data: { user_id: number; role_id: number }) =>
    client.post<Member>(`/projects/${projectId}/members`, data).then((r) => r.data),
  updateRole: (projectId: number, userId: number, roleId: number) =>
    client
      .patch<Member>(`/projects/${projectId}/members/${userId}`, { role_id: roleId })
      .then((r) => r.data),
  remove: (projectId: number, userId: number) =>
    client.delete(`/projects/${projectId}/members/${userId}`).then(() => null),
}
