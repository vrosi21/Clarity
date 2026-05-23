import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { Check, Loader2, Search, Trash2, UserPlus, X } from 'lucide-react'
import { useEffect, useRef, useState } from 'react'
import { toast } from 'sonner'

import { membersApi } from '@/api/members'
import { rolesApi } from '@/api/roles'
import { usersApi, type UserSearchResult } from '@/api/users'
import { Avatar, AvatarFallback } from '@/components/ui/avatar'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'
import {
  Sheet,
  SheetContent,
  SheetHeader,
  SheetTitle,
} from '@/components/ui/sheet'
import { Skeleton } from '@/components/ui/skeleton'
import { cn, getApiErrorMessage, getInitials } from '@/lib/utils'
import { useAuthStore } from '@/store/auth-store'
import { usePermissions } from '@/hooks/use-permissions'

interface Props {
  projectId: number
  open: boolean
  onOpenChange: (open: boolean) => void
}

function UserSearchCombobox({
  selectedUser,
  onSelect,
  memberIds,
}: {
  selectedUser: UserSearchResult | null
  onSelect: (u: UserSearchResult | null) => void
  memberIds: Set<number>
}) {
  const [query, setQuery] = useState('')
  const [focused, setFocused] = useState(false)
  const containerRef = useRef<HTMLDivElement>(null)

  const { data: results, isFetching } = useQuery({
    queryKey: ['users', 'search', query],
    queryFn: () => usersApi.search(query),
    enabled: query.length >= 1 && !selectedUser,
    staleTime: 10_000,
  })

  useEffect(() => {
    function handleClick(e: MouseEvent) {
      if (containerRef.current && !containerRef.current.contains(e.target as Node)) {
        setFocused(false)
      }
    }
    document.addEventListener('mousedown', handleClick)
    return () => document.removeEventListener('mousedown', handleClick)
  }, [])

  const showDropdown = focused && query.length >= 1 && !selectedUser

  if (selectedUser) {
    return (
      <div className="flex items-center gap-2 rounded-md border border-border bg-muted/30 px-3 py-1.5">
        <Avatar className="h-6 w-6 shrink-0">
          <AvatarFallback className="text-xs">{getInitials(selectedUser.username)}</AvatarFallback>
        </Avatar>
        <div className="flex-1 min-w-0">
          <span className="text-sm font-medium">{selectedUser.username}</span>
          <span className="ml-2 text-xs text-muted-foreground">{selectedUser.email}</span>
        </div>
        <button
          type="button"
          onClick={() => { onSelect(null); setQuery('') }}
          className="text-muted-foreground hover:text-foreground transition-colors"
        >
          <X className="h-3.5 w-3.5" />
        </button>
      </div>
    )
  }

  return (
    <div ref={containerRef} className="relative">
      <div className="relative">
        <Search className="absolute left-2.5 top-1/2 -translate-y-1/2 h-3.5 w-3.5 text-muted-foreground pointer-events-none" />
        <Input
          placeholder="Search by name or email…"
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          onFocus={() => setFocused(true)}
          className="h-8 pl-8 text-sm"
          autoComplete="off"
        />
        {isFetching && (
          <Loader2 className="absolute right-2.5 top-1/2 -translate-y-1/2 h-3.5 w-3.5 animate-spin text-muted-foreground" />
        )}
      </div>

      {showDropdown && (
        <div className="absolute z-50 mt-1 w-full overflow-hidden rounded-md border border-border bg-card shadow-lg">
          {!results || results.length === 0 ? (
            <p className="px-3 py-2 text-xs text-muted-foreground">
              {isFetching ? 'Searching…' : 'No users found'}
            </p>
          ) : (
            <ul className="max-h-48 overflow-y-auto">
              {results.map((u) => {
                const alreadyMember = memberIds.has(u.id)
                return (
                  <li key={u.id}>
                    <button
                      type="button"
                      disabled={alreadyMember}
                      onClick={() => { onSelect(u); setQuery(''); setFocused(false) }}
                      className={cn(
                        'flex w-full items-center gap-2.5 px-3 py-2 text-left text-sm transition-colors',
                        alreadyMember
                          ? 'opacity-40 cursor-not-allowed'
                          : 'hover:bg-accent/20 cursor-pointer',
                      )}
                    >
                      <Avatar className="h-6 w-6 shrink-0">
                        <AvatarFallback className="text-xs">{getInitials(u.username)}</AvatarFallback>
                      </Avatar>
                      <div className="flex-1 min-w-0">
                        <span className="font-medium">{u.username}</span>
                        {u.full_name && (
                          <span className="ml-1.5 text-muted-foreground">{u.full_name}</span>
                        )}
                        <div className="text-xs text-muted-foreground truncate">{u.email}</div>
                      </div>
                      {alreadyMember && <Check className="h-3.5 w-3.5 shrink-0 text-muted-foreground" />}
                    </button>
                  </li>
                )
              })}
            </ul>
          )}
        </div>
      )}
    </div>
  )
}

export function TeamManagementSheet({ projectId, open, onOpenChange }: Props) {
  const qc = useQueryClient()
  const currentUser = useAuthStore((s) => s.user)
  const [selectedUser, setSelectedUser] = useState<UserSearchResult | null>(null)
  const [newRoleId, setNewRoleId] = useState<number | null>(null)
  const [adding, setAdding] = useState(false)

  const { data: members, isPending } = useQuery({
    queryKey: ['members', projectId],
    queryFn: () => membersApi.list(projectId),
    enabled: open,
  })

  const { data: projectRoles } = useQuery({
    queryKey: ['roles', 'project'],
    queryFn: () => rolesApi.list('project'),
    enabled: open,
  })
  const { data: bothRoles } = useQuery({
    queryKey: ['roles', 'both'],
    queryFn: () => rolesApi.list('both'),
    enabled: open,
  })

  const availableRoles = [...(projectRoles ?? []), ...(bothRoles ?? [])]
  const memberIds = new Set(members?.map((m) => m.user_id) ?? [])

  const myMember = members?.find((m) => m.user_id === currentUser?.id)
  const { can, isAdmin } = usePermissions(myMember)
  const canManage = can('projects:manage_members') || isAdmin

  useEffect(() => {
    if (availableRoles.length > 0 && newRoleId === null) {
      const contributor = availableRoles.find((r) => r.name === 'contributor')
      setNewRoleId(contributor?.id ?? availableRoles[0].id)
    }
  }, [availableRoles, newRoleId])

  const updateRoleMutation = useMutation({
    mutationFn: ({ userId, roleId }: { userId: number; roleId: number }) =>
      membersApi.updateRole(projectId, userId, roleId),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['members', projectId] })
      toast.success('Role updated')
    },
    onError: (err) => toast.error(getApiErrorMessage(err)),
  })

  const removeMutation = useMutation({
    mutationFn: (uid: number) => membersApi.remove(projectId, uid),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['members', projectId] })
      toast.success('Member removed')
    },
    onError: (err) => toast.error(getApiErrorMessage(err)),
  })

  const handleAdd = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!selectedUser || newRoleId === null) return
    setAdding(true)
    try {
      await membersApi.add(projectId, { user_id: selectedUser.id, role_id: newRoleId })
      qc.invalidateQueries({ queryKey: ['members', projectId] })
      toast.success(`${selectedUser.username} added`)
      setSelectedUser(null)
    } catch (err) {
      toast.error(getApiErrorMessage(err))
    } finally {
      setAdding(false)
    }
  }

  return (
    <Sheet open={open} onOpenChange={onOpenChange}>
      <SheetContent className="w-[420px] sm:w-[480px] overflow-y-auto flex flex-col gap-6">
        <SheetHeader>
          <SheetTitle>Manage Team</SheetTitle>
        </SheetHeader>

        {/* Add member */}
        {canManage && (
          <form onSubmit={handleAdd} className="space-y-3 rounded-lg border border-border p-4">
            <p className="text-sm font-medium">Add member</p>
            <div className="space-y-1">
              <Label className="text-xs text-muted-foreground">Search user</Label>
              <UserSearchCombobox
                selectedUser={selectedUser}
                onSelect={setSelectedUser}
                memberIds={memberIds}
              />
            </div>
            <div className="flex items-end gap-2">
              <div className="flex-1 space-y-1">
                <Label htmlFor="team-role" className="text-xs text-muted-foreground">
                  Role
                </Label>
                <Select
                  value={newRoleId !== null ? String(newRoleId) : ''}
                  onValueChange={(v) => setNewRoleId(Number(v))}
                >
                  <SelectTrigger id="team-role" className="h-8 text-sm">
                    <SelectValue placeholder="Role" />
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
              <Button
                type="submit"
                size="sm"
                disabled={adding || !selectedUser || newRoleId === null}
                className="h-8"
              >
                {adding ? (
                  <Loader2 className="h-3.5 w-3.5 animate-spin" />
                ) : (
                  <UserPlus className="h-3.5 w-3.5" />
                )}
                Add
              </Button>
            </div>
          </form>
        )}

        {/* Member list */}
        <div className="space-y-2">
          {isPending &&
            Array.from({ length: 3 }).map((_, i) => <Skeleton key={i} className="h-14 w-full" />)}

          {members?.map((m) => {
            const isMe = m.user_id === currentUser?.id
            const canModify = canManage && !isMe

            return (
              <div
                key={m.user_id}
                className="flex items-center gap-3 rounded-lg border border-border px-3 py-2.5"
              >
                <Avatar className="h-8 w-8 shrink-0">
                  <AvatarFallback className="text-xs">{getInitials(m.username)}</AvatarFallback>
                </Avatar>
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-1.5">
                    <span className="truncate text-sm font-medium">{m.username}</span>
                    {isMe && <span className="text-xs text-muted-foreground">(you)</span>}
                  </div>
                  <span className="truncate text-xs text-muted-foreground">{m.email}</span>
                </div>
                <div className="flex items-center gap-1.5 shrink-0">
                  {canModify ? (
                    <Select
                      value={String(m.role_id)}
                      onValueChange={(v) =>
                        updateRoleMutation.mutate({ userId: m.user_id, roleId: Number(v) })
                      }
                    >
                      <SelectTrigger className="h-7 w-32 text-xs">
                        <SelectValue />
                      </SelectTrigger>
                      <SelectContent>
                        {availableRoles.map((r) => (
                          <SelectItem key={r.id} value={String(r.id)} className="text-xs">
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
                      className="h-7 w-7 text-muted-foreground hover:text-destructive"
                      onClick={() => {
                        if (confirm(`Remove ${m.username} from this project?`)) {
                          removeMutation.mutate(m.user_id)
                        }
                      }}
                      disabled={removeMutation.isPending}
                    >
                      <Trash2 className="h-3.5 w-3.5" />
                    </Button>
                  )}
                </div>
              </div>
            )
          })}
        </div>
      </SheetContent>
    </Sheet>
  )
}
