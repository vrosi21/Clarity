import { useMutation } from '@tanstack/react-query'
import { useState } from 'react'
import { toast } from 'sonner'

import { usersApi } from '@/api/users'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Separator } from '@/components/ui/separator'
import { useAuthStore } from '@/store/auth-store'

export function AccountSettingsPage() {
  const user = useAuthStore((s) => s.user)

  const [username, setUsername] = useState(user?.username ?? '')
  const [currentPassword, setCurrentPassword] = useState('')
  const [newPassword, setNewPassword] = useState('')
  const [confirmPassword, setConfirmPassword] = useState('')

  const mutation = useMutation({
    mutationFn: usersApi.updateSelf,
    onSuccess: () => {
      toast.success('Account updated')
      setCurrentPassword('')
      setNewPassword('')
      setConfirmPassword('')
    },
    onError: (err: any) =>
      toast.error(err?.response?.data?.detail ?? 'Failed to update account'),
  })

  const submit = () => {
    if (newPassword && newPassword !== confirmPassword) {
      toast.error('New passwords do not match')
      return
    }
    mutation.mutate({
      username: username !== user?.username ? username : undefined,
      current_password: currentPassword,
      new_password: newPassword || undefined,
    })
  }

  return (
    <div className="mx-auto max-w-lg space-y-8 py-8 px-4">
      <h1 className="text-2xl font-semibold">Account Settings</h1>

      {/* Read-only profile info */}
      <section className="space-y-4">
        <h2 className="text-base font-medium">Profile</h2>
        <div className="rounded-lg border border-border p-4 space-y-3 text-sm">
          <div className="flex justify-between">
            <span className="text-muted-foreground">Full name</span>
            <span>{(user as any)?.full_name ?? '—'}</span>
          </div>
          <div className="flex justify-between">
            <span className="text-muted-foreground">Email</span>
            <span>{user?.email}</span>
          </div>
          <div className="flex justify-between">
            <span className="text-muted-foreground">Years of experience</span>
            <span>{(user as any)?.years_experience ?? 0}</span>
          </div>
        </div>
        <p className="text-xs text-muted-foreground">
          Contact an admin to update your full name, email, or experience level.
        </p>
      </section>

      <Separator />

      {/* Editable account fields */}
      <section className="space-y-4">
        <h2 className="text-base font-medium">Account</h2>
        <div className="space-y-3">
          <div>
            <Label>Username</Label>
            <Input value={username} onChange={(e) => setUsername(e.target.value)} />
          </div>
          <div>
            <Label>Current password *</Label>
            <Input
              value={currentPassword}
              onChange={(e) => setCurrentPassword(e.target.value)}
              type="password"
              placeholder="Required to save changes"
            />
          </div>
          <div>
            <Label>New password <span className="text-muted-foreground">(leave blank to keep current)</span></Label>
            <Input
              value={newPassword}
              onChange={(e) => setNewPassword(e.target.value)}
              type="password"
            />
          </div>
          {newPassword && (
            <div>
              <Label>Confirm new password</Label>
              <Input
                value={confirmPassword}
                onChange={(e) => setConfirmPassword(e.target.value)}
                type="password"
              />
            </div>
          )}
        </div>
        <Button
          disabled={!currentPassword || mutation.isPending}
          onClick={submit}
        >
          Save changes
        </Button>
      </section>
    </div>
  )
}
