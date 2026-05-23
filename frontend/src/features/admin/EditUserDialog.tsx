import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { useEffect, useState } from 'react'
import { toast } from 'sonner'

import { adminApi } from '@/api/admin'
import { rolesApi } from '@/api/roles'
import { Button } from '@/components/ui/button'
import {
  Dialog,
  DialogContent,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Textarea } from '@/components/ui/textarea'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'
import { useAuthStore } from '@/store/auth-store'
import type { UserDetail } from '@/types'

interface Props {
  user: UserDetail | null
  onClose: () => void
}

export function EditUserDialog({ user, onClose }: Props) {
  const qc = useQueryClient()
  const currentUser = useAuthStore((s) => s.user)
  const isSelf = !!user && user.id === currentUser?.id

  const [email, setEmail] = useState('')
  const [username, setUsername] = useState('')
  const [fullName, setFullName] = useState('')
  const [yearsExp, setYearsExp] = useState(0)
  const [isActive, setIsActive] = useState(true)
  const [orgRoleId, setOrgRoleId] = useState<number | null>(null)
  const [bio, setBio] = useState<string>('')

  const { data: orgRoles } = useQuery({
    queryKey: ['roles', 'org'],
    queryFn: () => rolesApi.list('org'),
  })
  const { data: bothRoles } = useQuery({
    queryKey: ['roles', 'both'],
    queryFn: () => rolesApi.list('both'),
  })
  const allOrgRoles = [...(orgRoles ?? []), ...(bothRoles ?? [])]

  useEffect(() => {
    if (user) {
      setEmail(user.email)
      setUsername(user.username)
      setFullName(user.full_name ?? '')
      setYearsExp(user.years_experience)
      setIsActive(user.is_active)
      setOrgRoleId(user.org_role_id ?? null)
      setBio(user.bio ?? '')
    }
  }, [user])

  const mutation = useMutation({
    mutationFn: (data: Parameters<typeof adminApi.updateUser>[1]) =>
      adminApi.updateUser(user!.id, data),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['admin', 'users'] })
      qc.invalidateQueries({ queryKey: ['admin', 'user', user!.id] })
      toast.success('User updated')
      onClose()
    },
    onError: (err: any) =>
      toast.error(err?.response?.data?.detail ?? 'Failed to update user'),
  })

  const submit = () => {
    if (isSelf && !isActive) {
      toast.error('Cannot deactivate your own account')
      return
    }
    mutation.mutate({
      email,
      username,
      full_name: fullName || null,
      years_experience: Math.max(0, Math.min(20, yearsExp)),
      is_active: isActive,
      org_role_id: orgRoleId,
      bio: bio.trim() || null,
    })
  }

  return (
    <Dialog open={!!user} onOpenChange={(v) => !v && onClose()}>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>Edit User</DialogTitle>
        </DialogHeader>
        <div className="space-y-3">
          <div>
            <Label>Full name</Label>
            <Input value={fullName} onChange={(e) => setFullName(e.target.value)} placeholder="Jane Doe" />
          </div>
          <div>
            <Label>Email</Label>
            <Input value={email} onChange={(e) => setEmail(e.target.value)} />
          </div>
          <div>
            <Label>Username</Label>
            <Input value={username} onChange={(e) => setUsername(e.target.value)} />
          </div>
          <div>
            <Label>Years of experience (0–20)</Label>
            <Input
              value={yearsExp}
              onChange={(e) => setYearsExp(Number(e.target.value))}
              type="number"
              min={0}
              max={20}
            />
          </div>
          <div>
            <Label>Org role</Label>
            <Select
              value={orgRoleId !== null ? String(orgRoleId) : ''}
              onValueChange={(v) => setOrgRoleId(Number(v))}
              disabled={isSelf}
            >
              <SelectTrigger>
                <SelectValue placeholder="Select role" />
              </SelectTrigger>
              <SelectContent>
                {allOrgRoles.map((r) => (
                  <SelectItem
                    key={r.id}
                    value={String(r.id)}
                    disabled={r.name === 'root_user'}
                  >
                    {r.name}
                    {r.name === 'root_user' ? ' (set at deploy time only)' : ''}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
            {isSelf && (
              <p className="text-xs text-muted-foreground mt-1">Cannot change your own role</p>
            )}
          </div>
          <div>
            <Label>Bio / Skills description</Label>
            <Textarea
              rows={3}
              value={bio}
              onChange={(e) => setBio(e.target.value)}
              placeholder="Free-text bio used by the assignment engine"
            />
            <p className="mt-1 text-xs text-muted-foreground">
              Use the Worker Profile sheet for skill extraction with bubble suggestions.
            </p>
          </div>
          <label className="flex items-center gap-2 text-sm">
            <input
              type="checkbox"
              checked={isActive}
              disabled={isSelf}
              onChange={(e) => setIsActive(e.target.checked)}
            />
            Active
            {isSelf && <span className="text-muted-foreground text-xs">(cannot deactivate yourself)</span>}
          </label>
        </div>
        <DialogFooter>
          <Button variant="outline" onClick={onClose}>
            Cancel
          </Button>
          <Button disabled={mutation.isPending} onClick={submit}>
            Save
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}
