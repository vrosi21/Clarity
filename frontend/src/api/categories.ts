import client from '@/api/client'
import type { Category } from '@/types'

export const categoriesApi = {
  list: () => client.get<Category[]>('/categories').then((r) => r.data),
}
