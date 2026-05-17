import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { Loader2, Trash2, UserPlus } from 'lucide-react'
import { useEffect, useState } from 'react'
import { useParams } from 'react-router-dom'
import { toast } from 'sonner'

import { membersApi } from '@/api/members'
import { projectsApi } from '@/api/projects'
import { rolesApi } from '@/api/roles'
import { Avatar, AvatarFallback } from '@/components/ui/avatar'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Card, CardContent } from '@/components/ui/card'
import {
  Dialog,
  DialogContent,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'
import { Skeleton } from '@/components/ui/skeleton'
import { usePermissions } from '@/hooks/use-permissions'
import { getApiErrorMessage, getInitials } from '@/lib/utils'
import { useAuthStore } from '@/store/auth-store'

export function MembersPage() {
  const { projectId } = useParams<{ projectId: string }>()
  const id = Number(projectId)
  const queryClient = useQueryClient()
  const currentUser = useAuthStore((s) => s.user)
  const [addOpen, setAddOpen] = useState(false)
  const [userId, setUserId] = useState('')
  const [newRoleId, setNewRoleId] = useState<number | null>(null)
  const [adding, setAdding] = useState(false)

  const { data: project } = useQuery({
    queryKey: ['project', id],
    queryFn: () => projectsApi.get(id),
    enabled: !Number.isNaN(id),
  })

  const { data: members, isPending, isError } = useQuery({
    queryKey: ['members', id],
    queryFn: () => membersApi.list(id),
    enabled: !Number.isNaN(id),
  })

  const { data: projectRoles } = useQuery({
    queryKey: ['roles', 'project'],
    queryFn: () => rolesApi.list('project'),
  })

  const { data: bothRoles } = useQuery({
    queryKey: ['roles', 'both'],
    queryFn: () => rolesApi.list('both'),
  })

  const availableRoles = [...(projectRoles ?? []), ...(bothRoles ?? [])]

  useEffect(() => {
    document.title = project ? `Members — ${project.name} — Clarity` : 'Members — Clarity'
  }, [project])

  const myMember = members?.find((m) => m.user_id === currentUser?.id)
  const { can } = usePermissions(myMember)
  const canManage = can('projects:manage_members')

  useEffect(() => {
    if (availableRoles.length > 0 && newRoleId === null) {
      const contributor = availableRoles.find((r) => r.name === 'contributor')
      setNewRoleId(contributor?.id ?? availableRoles[0].id)
    }
  }, [availableRoles, newRoleId])

  const updateRoleMutation = useMutation({
    mutationFn: ({ userId, roleId }: { userId: number; roleId: number }) =>
      membersApi.updateRole(id, userId, roleId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['members', id] })
      toast.success('Role updated')
    },
    onError: (err) => toast.error(getApiErrorMessage(err)),
  })

  const removeMutation = useMutation({
    mutationFn: (userId: number) => membersApi.remove(id, userId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['members', id] })
      toast.success('Member removed')
    },
    onError: (err) => toast.error(getApiErrorMessage(err)),
  })

  const handleAdd = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!userId.trim() || newRoleId === null) return
    setAdding(true)
    try {
      await membersApi.add(id, { user_id: Number(userId), role_id: newRoleId })
      queryClient.invalidateQueries({ queryKey: ['members', id] })
      toast.success('Member added')
      setAddOpen(false)
      setUserId('')
    } catch (err) {
      toast.error(getApiErrorMessage(err))
    } finally {
      setAdding(false)
    }
  }

  return (
    <div className="h-full overflow-y-auto">
      <div className="mx-auto max-w-3xl px-6 py-8">
        <div className="mb-8 flex items-center justify-between gap-4">
          <div>
            <h1 className="text-2xl font-semibold tracking-tight">
              {project?.name ?? <Skeleton className="inline-block h-6 w-40" />} — Members
            </h1>
            <p className="text-sm text-muted-foreground">
              {members?.length ?? 0} member{members?.length === 1 ? '' : 's'}
            </p>
          </div>
          {canManage && (
            <Button onClick={() => setAddOpen(true)}>
              <UserPlus className="h-4 w-4" />
              Add member
            </Button>
          )}
        </div>

        {isPending && (
          <div className="space-y-3">
            {Array.from({ length: 4 }).map((_, i) => (
              <Skeleton key={i} className="h-16 w-full" />
            ))}
          </div>
        )}

        {isError && (
          <Card>
            <CardContent className="py-8 text-center text-sm text-muted-foreground">
              Couldn't load members. Make sure the API is running.
            </CardContent>
          </Card>
        )}

        {!isPending && members && (
          <div className="space-y-2">
            {members.map((m) => {
              const isMe = m.user_id === currentUser?.id
              const canModify = canManage && !isMe

              return (
                <Card key={m.user_id}>
                  <CardContent className="flex items-center gap-4 py-3">
                    <Avatar className="h-9 w-9 shrink-0">
                      <AvatarFallback className="text-sm">
                        {getInitials(m.username)}
                      </AvatarFallback>
                    </Avatar>
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center gap-2">
                        <span className="truncate text-sm font-medium">{m.username}</span>
                        {isMe && (
                          <span className="text-xs text-muted-foreground">(you)</span>
                        )}
                      </div>
                      <span className="truncate text-xs text-muted-foreground">{m.email}</span>
                    </div>
                    <div className="flex items-center gap-2 shrink-0">
                      {canModify ? (
                        <Select
                          value={String(m.role_id)}
                          onValueChange={(v) =>
                            updateRoleMutation.mutate({ userId: m.user_id, roleId: Number(v) })
                          }
                        >
                          <SelectTrigger className="w-36">
                            <SelectValue />
                          </SelectTrigger>
                          <SelectContent>
                            {availableRoles.map((r) => (
                              <SelectItem key={r.id} value={String(r.id)}>
                                {r.name}
                              </SelectItem>
                            ))}
                          </SelectContent>
                        </Select>
                      ) : (
                        <Badge variant="outline" className="text-xs capitalize">
                          {m.role_name}
                        </Badge>
                      )}
                      {canModify && (
                        <Button
                          variant="ghost"
                          size="icon"
                          className="h-8 w-8 text-muted-foreground hover:text-destructive"
                          onClick={() => {
                            if (confirm(`Remove ${m.username}?`)) {
                              removeMutation.mutate(m.user_id)
                            }
                          }}
                          disabled={removeMutation.isPending}
                        >
                          <Trash2 className="h-4 w-4" />
                        </Button>
                      )}
                    </div>
                  </CardContent>
                </Card>
              )
            })}
          </div>
        )}
      </div>

      <Dialog open={addOpen} onOpenChange={setAddOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Add member</DialogTitle>
          </DialogHeader>
          <form onSubmit={handleAdd} className="space-y-4">
            <div className="space-y-2">
              <Label htmlFor="user-id">User ID</Label>
              <Input
                id="user-id"
                type="number"
                placeholder="Enter numeric user ID"
                value={userId}
                onChange={(e) => setUserId(e.target.value)}
                required
              />
            </div>
            <div className="space-y-2">
              <Label htmlFor="role">Role</Label>
              <Select
                value={newRoleId !== null ? String(newRoleId) : ''}
                onValueChange={(v) => setNewRoleId(Number(v))}
              >
                <SelectTrigger id="role">
                  <SelectValue placeholder="Select a role" />
                </SelectTrigger>
                <SelectContent>
                  {availableRoles.map((r) => (
                    <SelectItem key={r.id} value={String(r.id)}>
                      {r.name}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
            <DialogFooter>
              <Button type="button" variant="outline" onClick={() => setAddOpen(false)}>
                Cancel
              </Button>
              <Button type="submit" disabled={adding || newRoleId === null}>
                {adding && <Loader2 className="h-4 w-4 animate-spin" />}
                Add
              </Button>
            </DialogFooter>
          </form>
        </DialogContent>
      </Dialog>
    </div>
  )
}
