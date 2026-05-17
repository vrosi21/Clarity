import client from '@/api/client'
import type { Priority, Ticket } from '@/types'

export interface TicketCreatePayload {
  title: string
  description?: string
  priority?: Priority
  complexity?: number
  stage_id: number
  category_id?: number | null
  estimated_minutes?: number | null
  assignee_id?: number | null
}

export interface TicketUpdatePayload {
  title?: string
  description?: string | null
  priority?: Priority
  complexity?: number
  stage_id?: number
  category_id?: number | null
  estimated_minutes?: number | null
  assignee_id?: number | null
}

export const ticketsApi = {
  list: (projectId: number, params?: { stage_id?: number }) =>
    client
      .get<Ticket[]>(`/projects/${projectId}/tickets`, { params })
      .then((r) => r.data),
  get: (projectId: number, ticketId: number) =>
    client.get<Ticket>(`/projects/${projectId}/tickets/${ticketId}`).then((r) => r.data),
  create: (projectId: number, data: TicketCreatePayload) =>
    client.post<Ticket>(`/projects/${projectId}/tickets`, data).then((r) => r.data),
  update: (projectId: number, ticketId: number, data: TicketUpdatePayload) =>
    client.patch<Ticket>(`/projects/${projectId}/tickets/${ticketId}`, data).then((r) => r.data),
  move: (projectId: number, ticketId: number, stageId: number) =>
    client
      .post<Ticket>(`/projects/${projectId}/tickets/${ticketId}/move`, { stage_id: stageId })
      .then((r) => r.data),
  remove: (projectId: number, ticketId: number) =>
    client.delete(`/projects/${projectId}/tickets/${ticketId}`).then(() => null),
}
