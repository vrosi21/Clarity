import client from '@/api/client'
import type { Comment } from '@/types'

export const commentsApi = {
  list: (ticketId: number) =>
    client.get<Comment[]>(`/tickets/${ticketId}/comments`).then((r) => r.data),
  create: (ticketId: number, data: { content: string; parent_id?: number }) =>
    client.post<Comment>(`/tickets/${ticketId}/comments`, data).then((r) => r.data),
  remove: (ticketId: number, commentId: number) =>
    client.delete(`/tickets/${ticketId}/comments/${commentId}`).then(() => null),
}
