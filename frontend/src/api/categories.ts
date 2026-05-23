import client from '@/api/client'
import type { Category } from '@/types'

export const categoriesApi = {
  list: () => client.get<Category[]>('/categories').then((r) => r.data),

  create: (name: string, description = '') =>
    client
      .post<Category>('/categories', { name, description })
      .then((r) => r.data),

  delete: (id: number) => client.delete(`/categories/${id}`),
}
