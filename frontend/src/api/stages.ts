import client from '@/api/client'
import type { Stage, StageType } from '@/types'

export const stagesApi = {
  list: (projectId: number) =>
    client.get<Stage[]>(`/projects/${projectId}/stages`).then((r) => r.data),
  create: (projectId: number, data: { name: string; order: number; type: StageType; color?: string }) =>
    client.post<Stage>(`/projects/${projectId}/stages`, data).then((r) => r.data),
  update: (projectId: number, stageId: number, data: { name?: string; order?: number; color?: string }) =>
    client.patch<Stage>(`/projects/${projectId}/stages/${stageId}`, data).then((r) => r.data),
  remove: (projectId: number, stageId: number) =>
    client.delete(`/projects/${projectId}/stages/${stageId}`).then(() => null),
}
