import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { Lock, Plus, Trash2 } from 'lucide-react'
import { useState } from 'react'
import { toast } from 'sonner'

import { rolesApi } from '@/api/roles'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
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
import { Separator } from '@/components/ui/separator'
import { usePermissions } from '@/hooks/use-permissions'
import { cn } from '@/lib/utils'
import type { Role, RoleScope } from '@/types'

const SCOPE_LABEL: Record<RoleScope, string> = {
  org: 'Org',
  project: 'Project',
  both: 'Both',
}

const SCOPE_COLOR: Record<RoleScope, string> = {
  org: 'border-blue-500/40 bg-blue-500/10 text-blue-700 dark:text-blue-300',
  project: 'border-green-500/40 bg-green-500/10 text-green-700 dark:text-green-300',
  both: 'border-purple-500/40 bg-purple-500/10 text-purple-700 dark:text-purple-300',
}

const ALL_PERMISSIONS = [
  { group: 'Org', perms: ['org:manage_users', 'org:read_users', 'org:manage_roles', 'org:manage_settings'] },
  { group: 'Projects', perms: ['projects:create', 'projects:read', 'projects:update', 'projects:delete', 'projects:manage_members', 'projects:manage_settings'] },
  { group: 'Stages', perms: ['stages:create', 'stages:update', 'stages:delete', 'stages:reorder'] },
  { group: 'Tickets', perms: ['tickets:create', 'tickets:read', 'tickets:update', 'tickets:delete', 'tickets:move', 'tickets:assign', 'tickets:be_assigned'] },
  { group: 'Comments', perms: ['comments:create', 'comments:read', 'comments:delete_own', 'comments:delete_any'] },
]

function PermissionPicker({
  value,
  onChange,
  disabled,
}: {
  value: string[]
  onChange: (v: string[]) => void
  disabled?: boolean
}) {
  const set = new Set(value)
  const toggle = (p: string) => {
    const next = new Set(set)
    if (next.has(p)) next.delete(p)
    else next.add(p)
    onChange(Array.from(next))
  }
  return (
    <div className="space-y-3 max-h-64 overflow-y-auto pr-1">
      {ALL_PERMISSIONS.map(({ group, perms }) => (
        <div key={group}>
          <p className="text-xs font-semibold uppercase tracking-wide text-muted-foreground mb-1">{group}</p>
          <div className="space-y-1">
            {perms.map((p) => (
              <label key={p} className={cn('flex items-center gap-2 text-sm', disabled && 'opacity-50')}>
                <input
                  type="checkbox"
                  checked={set.has(p)}
                  onChange={() => !disabled && toggle(p)}
                  disabled={disabled}
                />
                <span className="font-mono text-xs">{p}</span>
                {p === 'tickets:be_assigned' && (
                  <span className="text-xs text-muted-foreground">(RL assignment eligibility)</span>
                )}
              </label>
            ))}
          </div>
        </div>
      ))}
    </div>
  )
}

function CreateRoleDialog({ open, onClose }: { open: boolean; onClose: () => void }) {
  const qc = useQueryClient()
  const [name, setName] = useState('')
  const [description, setDescription] = useState('')
  const [scope, setScope] = useState<RoleScope>('project')
  const [permissions, setPermissions] = useState<string[]>([])

  const mutation = useMutation({
    mutationFn: () => rolesApi.create({ name, description: description || undefined, scope, permissions }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['roles'] })
      toast.success('Role created')
      onClose()
      setName('')
      setDescription('')
      setScope('project')
      setPermissions([])
    },
    onError: (err: any) => toast.error(err?.response?.data?.detail ?? 'Failed to create role'),
  })

  return (
    <Dialog open={open} onOpenChange={(v) => !v && onClose()}>
      <DialogContent className="max-w-lg">
        <DialogHeader>
          <DialogTitle>New Role</DialogTitle>
        </DialogHeader>
        <div className="space-y-4">
          <div>
            <Label>Name *</Label>
            <Input value={name} onChange={(e) => setName(e.target.value)} placeholder="e.g. reviewer" />
          </div>
          <div>
            <Label>Description</Label>
            <Input value={description} onChange={(e) => setDescription(e.target.value)} placeholder="Optional" />
          </div>
          <div>
            <Label>Scope</Label>
            <Select value={scope} onValueChange={(v) => setScope(v as RoleScope)}>
              <SelectTrigger><SelectValue /></SelectTrigger>
              <SelectContent>
                <SelectItem value="org">Org</SelectItem>
                <SelectItem value="project">Project</SelectItem>
                <SelectItem value="both">Both</SelectItem>
              </SelectContent>
            </Select>
          </div>
          <div>
            <Label>Permissions</Label>
            <div className="mt-2 rounded-md border p-3">
              <PermissionPicker value={permissions} onChange={setPermissions} />
            </div>
          </div>
        </div>
        <DialogFooter>
          <Button variant="outline" onClick={onClose}>Cancel</Button>
          <Button disabled={!name || mutation.isPending} onClick={() => mutation.mutate()}>
            Create
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}

function RoleDetail({ role, onDeleted }: { role: Role; onDeleted: () => void }) {
  const qc = useQueryClient()
  const [permissions, setPermissions] = useState<string[]>(role.permissions)
  const [dirty, setDirty] = useState(false)

  const updateMutation = useMutation({
    mutationFn: () => rolesApi.update(role.id, { permissions }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['roles'] })
      toast.success('Role updated')
      setDirty(false)
    },
    onError: (err: any) => toast.error(err?.response?.data?.detail ?? 'Failed to update'),
  })

  const deleteMutation = useMutation({
    mutationFn: () => rolesApi.delete(role.id),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['roles'] })
      toast.success('Role deleted')
      onDeleted()
    },
    onError: (err: any) => toast.error(err?.response?.data?.detail ?? 'Cannot delete role'),
  })

  return (
    <div className="space-y-4">
      <div className="flex items-center gap-2 flex-wrap">
        <h2 className="text-lg font-semibold">{role.name}</h2>
        {role.is_builtin && <Lock className="h-4 w-4 text-muted-foreground" />}
        <Badge variant="outline" className={cn('text-xs', SCOPE_COLOR[role.scope])}>
          {SCOPE_LABEL[role.scope]}
        </Badge>
        <span className="text-xs text-muted-foreground">{role.permissions.length} permissions</span>
      </div>
      {role.description && <p className="text-sm text-muted-foreground">{role.description}</p>}
      <Separator />
      <div>
        <p className="text-sm font-medium mb-2">Permissions</p>
        <PermissionPicker
          value={permissions}
          onChange={(v) => { setPermissions(v); setDirty(true) }}
          disabled={role.is_builtin}
        />
      </div>
      {!role.is_builtin && (
        <div className="flex gap-2 pt-2">
          <Button disabled={!dirty || updateMutation.isPending} onClick={() => updateMutation.mutate()}>
            Save
          </Button>
          <Button
            variant="ghost"
            size="icon"
            className="text-destructive hover:text-destructive ml-auto"
            disabled={deleteMutation.isPending}
            onClick={() => {
              if (confirm(`Delete role "${role.name}"?`)) deleteMutation.mutate()
            }}
          >
            <Trash2 className="h-4 w-4" />
          </Button>
        </div>
      )}
      {role.is_builtin && (
        <p className="text-xs text-muted-foreground">Built-in roles cannot be modified.</p>
      )}
    </div>
  )
}

export function RolesPage() {
  const { can } = usePermissions()
  const [createOpen, setCreateOpen] = useState(false)
  const [selected, setSelected] = useState<Role | null>(null)

  const { data: roles, isPending } = useQuery({
    queryKey: ['roles'],
    queryFn: () => rolesApi.list(),
  })

  const grouped = {
    org: roles?.filter((r) => r.scope === 'org') ?? [],
    project: roles?.filter((r) => r.scope === 'project') ?? [],
    both: roles?.filter((r) => r.scope === 'both') ?? [],
  }

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-semibold">Roles</h1>
        {can('org:manage_roles') && (
          <Button size="sm" onClick={() => setCreateOpen(true)}>
            <Plus className="h-4 w-4 mr-1" />
            New Role
          </Button>
        )}
      </div>

      <div className="flex gap-4 h-[calc(100vh-12rem)]">
        {/* Left: role list */}
        <div className="w-72 shrink-0 overflow-y-auto space-y-4">
          {isPending && <p className="text-sm text-muted-foreground">Loading…</p>}
          {(['org', 'project', 'both'] as RoleScope[]).map((scope) =>
            grouped[scope].length === 0 ? null : (
              <div key={scope}>
                <p className="text-xs font-semibold uppercase tracking-wide text-muted-foreground px-1 pb-1">
                  {SCOPE_LABEL[scope]}
                </p>
                <div className="space-y-1">
                  {grouped[scope].map((r) => (
                    <button
                      key={r.id}
                      onClick={() => setSelected(r)}
                      className={cn(
                        'w-full flex items-center gap-2 rounded-md px-3 py-2 text-sm text-left transition-colors',
                        selected?.id === r.id
                          ? 'bg-accent/40 font-medium'
                          : 'hover:bg-accent/20',
                      )}
                    >
                      {r.is_builtin && <Lock className="h-3 w-3 shrink-0 text-muted-foreground" />}
                      <span className="flex-1 truncate">{r.name}</span>
                      <span className="text-xs text-muted-foreground shrink-0">{r.permissions.length}</span>
                    </button>
                  ))}
                </div>
              </div>
            ),
          )}
        </div>

        {/* Right: detail */}
        <Card className="flex-1 overflow-y-auto">
          <CardContent className="p-6">
            {selected ? (
              <RoleDetail
                key={selected.id}
                role={selected}
                onDeleted={() => setSelected(null)}
              />
            ) : (
              <p className="text-sm text-muted-foreground">Select a role to view details.</p>
            )}
          </CardContent>
        </Card>
      </div>

      <CreateRoleDialog open={createOpen} onClose={() => setCreateOpen(false)} />
    </div>
  )
}
