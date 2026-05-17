import { Loader2, Sparkles } from 'lucide-react'
import { useState } from 'react'
import { Link, useLocation, useNavigate } from 'react-router-dom'
import { toast } from 'sonner'

import { authApi } from '@/api/auth'
import { Button } from '@/components/ui/button'
import {
  Card,
  CardContent,
  CardDescription,
  CardFooter,
  CardHeader,
  CardTitle,
} from '@/components/ui/card'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { getApiErrorMessage } from '@/lib/utils'
import { useAuthStore } from '@/store/auth-store'

export function LoginPage() {
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [submitting, setSubmitting] = useState(false)
  const setAuth = useAuthStore((s) => s.setAuth)
  const navigate = useNavigate()
  const location = useLocation() as { state?: { from?: { pathname?: string } } }
  const from = location.state?.from?.pathname ?? '/projects'

  const onSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setSubmitting(true)
    try {
      const { access_token } = await authApi.login({ email, password })
      // Persist token first so the next call picks it up via interceptor.
      useAuthStore.setState({ token: access_token })
      const user = await authApi.me()
      setAuth(access_token, user)
      toast.success(`Welcome back, ${user.username}`)
      navigate(from, { replace: true })
    } catch (err) {
      toast.error(getApiErrorMessage(err))
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <div className="flex min-h-screen items-center justify-center bg-muted/30 p-4">
      <div className="w-full max-w-md">
        <div className="mb-6 flex items-center justify-center gap-2">
          <Sparkles className="h-6 w-6 text-accent" />
          <span className="text-xl font-semibold tracking-tight">Clarity</span>
        </div>
        <Card>
          <CardHeader>
            <CardTitle>Welcome back</CardTitle>
            <CardDescription>Sign in to your Clarity workspace.</CardDescription>
          </CardHeader>
          <form onSubmit={onSubmit}>
            <CardContent className="space-y-4">
              <div className="space-y-2">
                <Label htmlFor="email">Email</Label>
                <Input
                  id="email"
                  type="email"
                  autoComplete="email"
                  required
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                />
              </div>
              <div className="space-y-2">
                <Label htmlFor="password">Password</Label>
                <Input
                  id="password"
                  type="password"
                  autoComplete="current-password"
                  required
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                />
              </div>
            </CardContent>
            <CardFooter className="flex-col items-stretch gap-3">
              <Button type="submit" disabled={submitting} className="w-full">
                {submitting && <Loader2 className="h-4 w-4 animate-spin" />}
                Sign in
              </Button>
              <p className="text-center text-sm text-muted-foreground">
                Don't have an account?{' '}
                <Link to="/register" className="font-medium text-foreground underline-offset-4 hover:underline">
                  Create one
                </Link>
              </p>
            </CardFooter>
          </form>
        </Card>
        <p className="mt-6 text-center text-xs text-muted-foreground">
          <Link to="/" className="hover:underline">
            ← Back to home
          </Link>
        </p>
      </div>
    </div>
  )
}
