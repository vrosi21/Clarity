import client from '@/api/client'
import type { Project } from '@/types'

export const projectsApi = {
  list: () => client.get<Project[]>('/projects').then((r) => r.data),
  get: (id: number) => client.get<Project>(`/projects/${id}`).then((r) => r.data),
  create: (data: { name: string; description?: string }) =>
    client.post<Project>('/projects', data).then((r) => r.data),
  update: (id: number, data: { name?: string; description?: string }) =>
    client.patch<Project>(`/projects/${id}`, data).then((r) => r.data),
  remove: (id: number) => client.delete(`/projects/${id}`).then(() => null),
}
