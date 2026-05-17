import { useMemo } from 'react'
import { useAuthStore } from '@/store/auth-store'
import type { Member } from '@/types'

export function usePermissions(membership?: Member | null) {
  const user = useAuthStore((s) => s.user)
  return useMemo(() => {
    const perms = new Set<string>()
    user?.org_role?.permissions?.forEach((p) => perms.add(p))
    membership?.role_permissions?.forEach((p) => perms.add(p))
    return {
      can: (permission: string) => perms.has(permission),
      permissions: perms,
      isRootUser: user?.org_role?.role_name === 'root_user',
      isAdmin: perms.has('org:manage_users'),
    }
  }, [user, membership])
}
