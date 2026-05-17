import { Outlet } from 'react-router-dom'

import { useAuthStore } from '@/store/auth-store'

export function AdminLayout() {
  const user = useAuthStore((s) => s.user)
  const isAdmin = !!user?.org_role?.permissions?.includes('org:manage_users')

  if (!isAdmin) {
    return (
      <div className="flex h-full items-center justify-center text-muted-foreground">
        403 — Admin access required.
      </div>
    )
  }

  return (
    <div className="h-full overflow-y-auto p-6">
      <Outlet />
    </div>
  )
}
