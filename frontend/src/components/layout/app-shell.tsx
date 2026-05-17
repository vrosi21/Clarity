import { useEffect } from 'react'
import { Outlet, useNavigate } from 'react-router-dom'

import { authApi } from '@/api/auth'
import { ErrorBoundary } from '@/components/common/error-boundary'
import { Sidebar } from '@/components/layout/sidebar'
import { useAuthStore } from '@/store/auth-store'

export function AppShell() {
  const token = useAuthStore((s) => s.token)
  const setUser = useAuthStore((s) => s.setUser)
  const logout = useAuthStore((s) => s.logout)
  const navigate = useNavigate()

  // Refresh user info on mount; if the token is invalid, sign out.
  useEffect(() => {
    if (!token) return
    authApi
      .me()
      .then(setUser)
      .catch(() => {
        logout()
        navigate('/login')
      })
  }, [token, setUser, logout, navigate])

  return (
    <div className="flex h-screen w-screen overflow-hidden">
      <Sidebar />
      <main className="flex-1 overflow-hidden">
        <ErrorBoundary>
          <Outlet />
        </ErrorBoundary>
      </main>
    </div>
  )
}
