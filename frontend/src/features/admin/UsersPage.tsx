import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { Plus, Settings, Trash2, UserPen } from 'lucide-react'
import { useState } from 'react'
import { toast } from 'sonner'

import { adminApi } from '@/api/admin'
import { Avatar, AvatarFallback } from '@/components/ui/avatar'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Skeleton } from '@/components/ui/skeleton'
import { getInitials } from '@/lib/utils'
import type { UserDetail } from '@/types'
import { useAuthStore } from '@/store/auth-store'
import { CreateUserDialog } from './CreateUserDialog'
import { EditUserDialog } from './EditUserDialog'
import { SkillProfileDialog } from './SkillProfileDialog'

export function UsersPage() {
  const qc = useQueryClient()
  const currentUser = useAuthStore((s) => s.user)
  const [createOpen, setCreateOpen] = useState(false)
  const [editUser, setEditUser] = useState<UserDetail | null>(null)
  const [skillUser, setSkillUser] = useState<UserDetail | null>(null)

  const { data: users, isPending } = useQuery({
    queryKey: ['admin', 'users'],
    queryFn: adminApi.listUsers,
  })

  const deactivate = useMutation({
    mutationFn: adminApi.deactivateUser,
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['admin', 'users'] })
      toast.success('User deactivated')
    },
    onError: () => toast.error('Failed to deactivate user'),
  })

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-semibold">Users</h1>
        <Button size="sm" onClick={() => setCreateOpen(true)}>
          <Plus className="mr-1 h-4 w-4" />
          New User
        </Button>
      </div>

      {isPending ? (
        <div className="space-y-2">
          {Array.from({ length: 4 }).map((_, i) => (
            <Skeleton key={i} className="h-12 w-full" />
          ))}
        </div>
      ) : (
        <div className="overflow-hidden rounded-lg border border-border">
          <table className="w-full text-sm">
            <thead className="bg-muted/40">
              <tr>
                <th className="px-4 py-2 text-left font-medium text-muted-foreground">User</th>
                <th className="px-4 py-2 text-left font-medium text-muted-foreground">Full Name</th>
                <th className="px-4 py-2 text-left font-medium text-muted-foreground">Email</th>
                <th className="px-4 py-2 text-left font-medium text-muted-foreground">Exp</th>
                <th className="px-4 py-2 text-left font-medium text-muted-foreground">Org Role</th>
                <th className="px-4 py-2 text-left font-medium text-muted-foreground">Status</th>
                <th className="px-4 py-2 text-right font-medium text-muted-foreground">Actions</th>
              </tr>
            </thead>
            <tbody>
              {users?.map((u) => (
                <tr key={u.id} className="border-t border-border">
                  <td className="px-4 py-2">
                    <div className="flex items-center gap-2">
                      <Avatar className="h-7 w-7">
                        <AvatarFallback className="text-xs">{getInitials(u.username)}</AvatarFallback>
                      </Avatar>
                      <span className="font-medium">{u.username}</span>
                    </div>
                  </td>
                  <td className="px-4 py-2 text-muted-foreground">{u.full_name ?? '—'}</td>
                  <td className="px-4 py-2 text-muted-foreground">{u.email}</td>
                  <td className="px-4 py-2 text-muted-foreground">{u.years_experience} yr</td>
                  <td className="px-4 py-2 text-muted-foreground">
                    {u.org_role_name ?? '—'}
                  </td>
                  <td className="px-4 py-2">
                    <Badge variant={u.is_active ? 'default' : 'destructive'}>
                      {u.is_active ? 'Active' : 'Inactive'}
                    </Badge>
                  </td>
                  <td className="px-4 py-2">
                    <div className="flex justify-end gap-1">
                      <Button variant="ghost" size="icon" onClick={() => setEditUser(u)} title="Edit">
                        <UserPen className="h-4 w-4" />
                      </Button>
                      <Button variant="ghost" size="icon" onClick={() => setSkillUser(u)} title="Skills">
                        <Settings className="h-4 w-4" />
                      </Button>
                      {u.id !== currentUser?.id && (
                        <Button
                          variant="ghost"
                          size="icon"
                          className="text-destructive hover:text-destructive"
                          disabled={deactivate.isPending}
                          onClick={() => {
                            if (confirm(`Deactivate ${u.username}?`)) deactivate.mutate(u.id)
                          }}
                          title="Deactivate"
                        >
                          <Trash2 className="h-4 w-4" />
                        </Button>
                      )}
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      <CreateUserDialog open={createOpen} onOpenChange={setCreateOpen} />
      <EditUserDialog user={editUser} onClose={() => setEditUser(null)} />
      <SkillProfileDialog user={skillUser} onClose={() => setSkillUser(null)} />
    </div>
  )
}
