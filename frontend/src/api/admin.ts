import client from './client'
import type { CategoryProficiency, DashboardStats, SkillSuggestResponse, UserDetail } from '@/types'

export const adminApi = {
  getDashboard: () =>
    client.get<DashboardStats>('/admin/dashboard').then((r) => r.data),
  listUsers: () => client.get<UserDetail[]>('/admin/users').then((r) => r.data),
  getUser: (id: number) =>
    client.get<UserDetail>(`/admin/users/${id}`).then((r) => r.data),
  createUser: (data: {
    email: string
    username: string
    full_name?: string
    password: string
    years_experience: number
    org_role_id?: number | null
  }) => client.post<UserDetail>('/admin/users', data).then((r) => r.data),
  updateUser: (
    id: number,
    data: Partial<{
      email: string
      username: string
      full_name: string | null
      years_experience: number
      org_role_id: number | null
      is_active: boolean
      bio: string | null
    }>,
  ) => client.patch<UserDetail>(`/admin/users/${id}`, data).then((r) => r.data),
  deactivateUser: (id: number) => client.delete(`/admin/users/${id}`),

  /** LangChain skill extraction from a free-text bio. Suggestion only — nothing
   * is persisted until the parent component calls applySkills. */
  suggestSkills: (bio: string) =>
    client
      .post<SkillSuggestResponse>('/users/me/skills/suggest', { bio })
      .then((r) => r.data),

  /** Persist the accepted category proficiency scores for the current user.
   * Called alongside updateUser (bio save) when the admin confirms the sheet. */
  applySkills: (category_proficiencies: CategoryProficiency[]) =>
    client.post('/users/me/skills/apply', { category_proficiencies }),
}
