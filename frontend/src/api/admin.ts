import client from './client'
import type { DashboardStats, SkillProfile, UserDetail } from '@/types'

export const adminApi = {
  getDashboard: () => client.get<DashboardStats>('/admin/dashboard').then((r) => r.data),
  listUsers: () => client.get<UserDetail[]>('/admin/users').then((r) => r.data),
  getUser: (id: number) => client.get<UserDetail>(`/admin/users/${id}`).then((r) => r.data),
  createUser: (data: {
    email: string
    username: string
    full_name?: string
    password: string
    years_experience: number
    org_role_id?: number | null
  }) => client.post<UserDetail>('/admin/users', data).then((r) => r.data),
  updateUser: (id: number, data: Partial<{
    email: string
    username: string
    full_name: string | null
    years_experience: number
    org_role_id: number | null
    is_active: boolean
  }>) => client.patch<UserDetail>(`/admin/users/${id}`, data).then((r) => r.data),
  deactivateUser: (id: number) => client.delete(`/admin/users/${id}`),
  getSkills: (userId: number) =>
    client.get<SkillProfile[]>(`/admin/users/${userId}/skills`).then((r) => r.data),
  setSkills: (userId: number, skills: SkillProfile[]) =>
    client.put(`/admin/users/${userId}/skills`, { skills }).then((r) => r.data),
}
