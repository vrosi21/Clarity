import client from '@/api/client'
import type { CategoryConfig, ProjectSettings, RoleConstraint } from '@/types'

export const projectSettingsApi = {
  get: (projectId: number) =>
    client.get<ProjectSettings>(`/projects/${projectId}/settings`).then((r) => r.data),

  upsertConstraint: (
    projectId: number,
    data: Omit<RoleConstraint, 'id' | 'role_name'>,
  ) => client.put(`/projects/${projectId}/settings/constraints`, data),

  deleteConstraint: (projectId: number, roleId: number) =>
    client.delete(`/projects/${projectId}/settings/constraints/${roleId}`),

  upsertCategoryConfig: (
    projectId: number,
    data: Omit<CategoryConfig, 'id' | 'category_name'>,
  ) => client.put(`/projects/${projectId}/settings/category-configs`, data),
}
