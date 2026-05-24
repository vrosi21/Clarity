import client from '@/api/client'
import type { RLProjectConfig, WorkerProfile } from '@/types'

export const rlConfigApi = {
  get: (projectId: number) =>
    client.get<RLProjectConfig>(`/projects/${projectId}/rl-config`).then((r) => r.data),
}

export const workerProfileApi = {
  get: (userId: number) =>
    client.get<WorkerProfile>(`/users/${userId}/worker-profile`).then((r) => r.data),
}
