import axios, { type AxiosInstance } from 'axios'

import { useAuthStore } from '@/store/auth-store'

const client: AxiosInstance = axios.create({ baseURL: '/api/v1' })

client.interceptors.request.use((config) => {
  const token = useAuthStore.getState().token
  if (token) {
    config.headers.Authorization = `Bearer ${token}`
  }
  return config
})

client.interceptors.response.use(
  (r) => r,
  (error) => {
    const status = error?.response?.status
    if (status === 401) {
      // Token rejected — wipe auth state.
      // We don't redirect here directly; the ProtectedRoute will catch the
      // null token on the next render and route to /login.
      useAuthStore.getState().logout()
    }
    return Promise.reject(error)
  },
)

export default client
