import client from '@/api/client'
import type {
  SimulationRun,
  SimulationRunSummary,
  SyntheticTeam,
  SyntheticTeamListItem,
  SyntheticTeamCreatePayload,
  SimulationRunPayload,
} from '@/types'

export const simulationApi = {
  runProject: (projectId: number, payload: SimulationRunPayload) =>
    client
      .post<SimulationRun>(`/simulation/projects/${projectId}/run`, payload)
      .then((r) => r.data),

  listRuns: (projectId: number) =>
    client
      .get<SimulationRunSummary[]>('/simulation/runs', { params: { project_id: projectId } })
      .then((r) => r.data),

  getRun: (runId: number) =>
    client.get<SimulationRun>(`/simulation/runs/${runId}`).then((r) => r.data),

  listTeams: () =>
    client.get<SyntheticTeamListItem[]>('/simulation/teams').then((r) => r.data),

  createTeam: (payload: SyntheticTeamCreatePayload) =>
    client.post<SyntheticTeam>('/simulation/teams', payload).then((r) => r.data),

  deleteTeam: (teamId: number) =>
    client.delete(`/simulation/teams/${teamId}`).then(() => null),
}
