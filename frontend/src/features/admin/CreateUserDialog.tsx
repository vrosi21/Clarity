import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { useState } from 'react'
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
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'

interface Props {
  open: boolean
  onOpenChange: (v: boolean) => void
}

const EMPTY = { email: '', username: '', fullName: '', password: '', yearsExp: 0 }

export function CreateUserDialog({ open, onOpenChange }: Props) {
  const qc = useQueryClient()
  const [form, setForm] = useState(EMPTY)
  const [orgRoleId, setOrgRoleId] = useState<number | null>(null)

  const { data: orgRoles } = useQuery({
    queryKey: ['roles', 'org'],
    queryFn: () => rolesApi.list('org'),
  })
  const { data: bothRoles } = useQuery({
    queryKey: ['roles', 'both'],
    queryFn: () => rolesApi.list('both'),
  })
  const allOrgRoles = [...(orgRoles ?? []), ...(bothRoles ?? [])]

  const set = (k: keyof typeof EMPTY) => (e: React.ChangeEvent<HTMLInputElement>) =>
    setForm((f) => ({ ...f, [k]: e.target.type === 'number' ? Number(e.target.value) : e.target.value }))

  const mutation = useMutation({
    mutationFn: adminApi.createUser,
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['admin', 'users'] })
      toast.success('User created')
      onOpenChange(false)
      setForm(EMPTY)
      setOrgRoleId(null)
    },
    onError: () => toast.error('Failed to create user'),
  })

  const submit = () =>
    mutation.mutate({
      email: form.email,
      username: form.username,
      full_name: form.fullName || undefined,
      password: form.password,
      years_experience: form.yearsExp,
      org_role_id: orgRoleId ?? undefined,
    })

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>New User</DialogTitle>
        </DialogHeader>
        <div className="space-y-3">
          <div>
            <Label>Full name <span className="text-muted-foreground">(optional)</span></Label>
            <Input value={form.fullName} onChange={set('fullName')} placeholder="Jane Doe" />
          </div>
          <div>
            <Label>Email *</Label>
            <Input value={form.email} onChange={set('email')} />
          </div>
          <div>
            <Label>Username *</Label>
            <Input value={form.username} onChange={set('username')} />
          </div>
          <div>
            <Label>Password *</Label>
            <Input value={form.password} onChange={set('password')} type="password" />
          </div>
          <div>
            <Label>Years of experience (0–20)</Label>
            <Input
              value={form.yearsExp}
              onChange={set('yearsExp')}
              type="number"
              min={0}
              max={20}
            />
          </div>
          <div>
            <Label>Org role <span className="text-muted-foreground">(defaults to member)</span></Label>
            <Select
              value={orgRoleId !== null ? String(orgRoleId) : ''}
              onValueChange={(v) => setOrgRoleId(Number(v))}
            >
              <SelectTrigger>
                <SelectValue placeholder="Default (member)" />
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
          </div>
        </div>
        <DialogFooter>
          <Button variant="outline" onClick={() => onOpenChange(false)}>
            Cancel
          </Button>
          <Button
            disabled={!form.email || !form.username || !form.password || mutation.isPending}
            onClick={submit}
          >
            Create
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}
