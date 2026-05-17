import client from '@/api/client'
import type { Role, RoleScope } from '@/types'

export const rolesApi = {
  list: (scope?: RoleScope) =>
    client.get<Role[]>('/roles', { params: scope ? { scope } : {} }).then((r) => r.data),
  get: (id: number) => client.get<Role>(`/roles/${id}`).then((r) => r.data),
  create: (data: { name: string; description?: string; scope: RoleScope; permissions: string[] }) =>
    client.post<Role>('/roles', data).then((r) => r.data),
  update: (id: number, data: Partial<{ name: string; description: string; permissions: string[] }>) =>
    client.patch<Role>(`/roles/${id}`, data).then((r) => r.data),
  delete: (id: number) => client.delete(`/roles/${id}`),
  assignOrgRole: (userId: number, roleId: number) =>
    client.put(`/roles/assign/${userId}`, { role_id: roleId }),
}
