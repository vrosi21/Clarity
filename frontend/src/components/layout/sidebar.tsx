import { useQuery } from '@tanstack/react-query'
import {
  ChevronDown,
  LayoutDashboard,
  LogOut,
  Moon,
  Plus,
  Shield,
  Sun,
  Sparkles,
  Tag,
  UserCog,
  Users,
} from 'lucide-react'
import { useState } from 'react'
import { NavLink, useNavigate } from 'react-router-dom'

import { projectsApi } from '@/api/projects'
import { useTheme } from '@/components/common/theme-provider'
import { CreateProjectDialog } from '@/features/projects/create-project-dialog'
import { Avatar, AvatarFallback } from '@/components/ui/avatar'
import { Button } from '@/components/ui/button'
import { Separator } from '@/components/ui/separator'
import { Skeleton } from '@/components/ui/skeleton'
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu'
import { cn, getInitials } from '@/lib/utils'
import { useAuthStore } from '@/store/auth-store'

const ADMIN_NAV = [
  { to: '/admin', label: 'Dashboard', icon: LayoutDashboard, end: true },
  { to: '/admin/users', label: 'Users', icon: Users, end: false },
  { to: '/admin/roles', label: 'Roles', icon: Shield, end: false },
  { to: '/admin/categories', label: 'Categories', icon: Tag, end: false },
]

export function Sidebar() {
  const { theme, toggleTheme } = useTheme()
  const navigate = useNavigate()
  const user = useAuthStore((s) => s.user)
  const logout = useAuthStore((s) => s.logout)
  const [createOpen, setCreateOpen] = useState(false)
  const [projectsOpen, setProjectsOpen] = useState(true)
  const [adminOpen, setAdminOpen] = useState(false)

  const isAdmin = !!user?.org_role?.permissions?.includes('org:manage_users')

  const { data: projects, isPending } = useQuery({
    queryKey: ['projects'],
    queryFn: projectsApi.list,
  })

  return (
    <aside className="flex h-full w-60 shrink-0 flex-col border-r border-border bg-card">
      {/* Brand */}
      <div className="flex h-14 items-center gap-2 border-b border-border px-4">
        <Sparkles className="h-5 w-5 text-accent" />
        <span className="text-base font-semibold tracking-tight">Clarity</span>
      </div>

      {/* Nav sections */}
      <div className="flex-1 overflow-y-auto py-3 space-y-1">
        {/* Projects section */}
        <div>
          <div className="flex items-center px-2">
            <button
              onClick={() => setProjectsOpen((o) => !o)}
              className="flex flex-1 items-center gap-1 rounded-md px-2 py-1.5 text-xs font-semibold uppercase tracking-wide text-muted-foreground hover:bg-accent/20 transition-colors"
            >
              <ChevronDown
                className={cn('h-3.5 w-3.5 transition-transform', !projectsOpen && '-rotate-90')}
              />
              Projects
            </button>
            <Button
              variant="ghost"
              size="icon"
              className="h-6 w-6 shrink-0"
              onClick={() => setCreateOpen(true)}
              aria-label="New project"
            >
              <Plus className="h-4 w-4" />
            </Button>
          </div>

          <div
            className={cn(
              'grid transition-all duration-200 ease-in-out',
              projectsOpen ? 'grid-rows-[1fr]' : 'grid-rows-[0fr]',
            )}
          >
            <nav className="mt-0.5 space-y-0.5 px-2 overflow-hidden">
              {isPending && (
                <div className="space-y-1 px-2">
                  <Skeleton className="h-8 w-full" />
                  <Skeleton className="h-8 w-full" />
                  <Skeleton className="h-8 w-full" />
                </div>
              )}
              {!isPending && projects?.length === 0 && (
                <p className="px-2 py-1 text-xs text-muted-foreground">No projects yet.</p>
              )}
              {!isPending &&
                projects?.map((p) => (
                  <NavLink
                    key={p.id}
                    to={`/projects/${p.id}`}
                    className={({ isActive }) =>
                      cn(
                        'block truncate rounded-md px-2 py-1.5 text-sm transition-colors',
                        isActive
                          ? 'bg-accent/40 text-accent-foreground font-medium'
                          : 'text-foreground hover:bg-accent/20',
                      )
                    }
                  >
                    {p.name}
                  </NavLink>
                ))}
            </nav>
          </div>
        </div>

        {/* Admin section */}
        {isAdmin && (
          <div>
            <div className="flex items-center px-2">
              <button
                onClick={() => setAdminOpen((o) => !o)}
                className="flex flex-1 items-center gap-1 rounded-md px-2 py-1.5 text-xs font-semibold uppercase tracking-wide text-muted-foreground hover:bg-accent/20 transition-colors"
              >
                <ChevronDown
                  className={cn('h-3.5 w-3.5 transition-transform', !adminOpen && '-rotate-90')}
                />
                Admin
              </button>
            </div>

            <div
              className={cn(
                'grid transition-all duration-200 ease-in-out',
                adminOpen ? 'grid-rows-[1fr]' : 'grid-rows-[0fr]',
              )}
            >
              <nav className="mt-0.5 space-y-0.5 px-2 overflow-hidden">
                {ADMIN_NAV.map(({ to, label, icon: Icon, end }) => (
                  <NavLink
                    key={to}
                    to={to}
                    end={end}
                    className={({ isActive }) =>
                      cn(
                        'flex items-center gap-2 rounded-md px-2 py-1.5 text-sm transition-colors',
                        isActive
                          ? 'bg-accent/40 font-medium text-accent-foreground'
                          : 'text-foreground hover:bg-accent/20',
                      )
                    }
                  >
                    <Icon className="h-4 w-4" />
                    {label}
                  </NavLink>
                ))}
              </nav>
            </div>
          </div>
        )}
      </div>

      <Separator />

      {/* User panel */}
      <div className="flex items-center gap-2 px-3 py-3">
        <DropdownMenu>
          <DropdownMenuTrigger className="flex flex-1 items-center gap-2 rounded-md p-1 hover:bg-accent/20">
            <Avatar className="h-8 w-8">
              <AvatarFallback>{user ? getInitials(user.username) : '?'}</AvatarFallback>
            </Avatar>
            <div className="flex-1 text-left">
              <div className="truncate text-sm font-medium">{user?.username ?? 'Guest'}</div>
              <div className="truncate text-xs text-muted-foreground">{user?.email}</div>
            </div>
          </DropdownMenuTrigger>
          <DropdownMenuContent align="end" className="w-56">
            <DropdownMenuLabel>{user?.email}</DropdownMenuLabel>
            <DropdownMenuSeparator />
            <DropdownMenuItem onSelect={() => navigate('/settings')}>
              <UserCog className="h-4 w-4" />
              Account settings
            </DropdownMenuItem>
            <DropdownMenuSeparator />
            <DropdownMenuItem
              onSelect={() => {
                logout()
                navigate('/login')
              }}
            >
              <LogOut className="h-4 w-4" />
              Sign out
            </DropdownMenuItem>
          </DropdownMenuContent>
        </DropdownMenu>
        <Button variant="ghost" size="icon" onClick={toggleTheme} aria-label="Toggle theme">
          {theme === 'dark' ? <Sun className="h-4 w-4" /> : <Moon className="h-4 w-4" />}
        </Button>
      </div>

      <CreateProjectDialog open={createOpen} onOpenChange={setCreateOpen} />
    </aside>
  )
}
