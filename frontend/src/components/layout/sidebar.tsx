import {
  ChevronDown,
  FlaskConical,
  FolderKanban,
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

import { useTheme } from '@/components/common/theme-provider'
import { CreateProjectDialog } from '@/features/projects/create-project-dialog'
import { Avatar, AvatarFallback } from '@/components/ui/avatar'
import { Button } from '@/components/ui/button'
import { Separator } from '@/components/ui/separator'
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

const navItemClass = ({ isActive }: { isActive: boolean }) =>
  cn(
    'flex items-center gap-2.5 rounded-lg px-3 py-2 text-sm font-medium transition-colors',
    isActive
      ? 'bg-accent/15 text-accent-foreground'
      : 'text-muted-foreground hover:bg-accent/10 hover:text-foreground',
  )

export function Sidebar() {
  const { theme, toggleTheme } = useTheme()
  const navigate = useNavigate()
  const user = useAuthStore((s) => s.user)
  const logout = useAuthStore((s) => s.logout)
  const [createOpen, setCreateOpen] = useState(false)
  const [adminOpen, setAdminOpen] = useState(false)

  const isAdmin = !!user?.org_role?.permissions?.includes('org:manage_users')
  const canSimulate = !!user?.org_role?.permissions?.includes('simulation:run')

  return (
    <aside className="flex h-full w-60 shrink-0 flex-col border-r border-border bg-card">
      {/* Brand */}
      <div className="flex h-14 items-center gap-2 px-4">
        <div className="flex h-7 w-7 items-center justify-center rounded-lg bg-accent/15">
          <Sparkles className="h-4 w-4 text-accent" />
        </div>
        <span className="text-base font-semibold tracking-tight">Clarity</span>
      </div>

      {/* Nav sections */}
      <div className="flex-1 overflow-y-auto px-2 py-2 space-y-1">
        <NavLink to="/projects" className={navItemClass}>
          <FolderKanban className="h-4 w-4 shrink-0" />
          Projects
        </NavLink>

        {canSimulate && (
          <NavLink to="/simulation" className={navItemClass}>
            <FlaskConical className="h-4 w-4 shrink-0" />
            Simulation
          </NavLink>
        )}

        {/* Admin section */}
        {isAdmin && (
          <div className="pt-2">
            <button
              onClick={() => setAdminOpen((o) => !o)}
              className="flex w-full items-center gap-1 rounded-md px-3 py-1.5 text-xs font-semibold uppercase tracking-wide text-muted-foreground/70 hover:text-muted-foreground transition-colors"
            >
              <ChevronDown
                className={cn('h-3.5 w-3.5 transition-transform', !adminOpen && '-rotate-90')}
              />
              Admin
            </button>

            <div
              className={cn(
                'grid transition-all duration-200 ease-in-out',
                adminOpen ? 'grid-rows-[1fr]' : 'grid-rows-[0fr]',
              )}
            >
              <nav className="mt-0.5 space-y-0.5 overflow-hidden">
                {ADMIN_NAV.map(({ to, label, icon: Icon, end }) => (
                  <NavLink key={to} to={to} end={end} className={navItemClass}>
                    <Icon className="h-4 w-4 shrink-0" />
                    {label}
                  </NavLink>
                ))}
              </nav>
            </div>
          </div>
        )}
      </div>

      {/* Quick action */}
      <div className="px-3 pb-1">
        <Button
          variant="outline"
          size="sm"
          className="w-full justify-start gap-2"
          onClick={() => setCreateOpen(true)}
        >
          <Plus className="h-4 w-4" />
          New project
        </Button>
      </div>

      <Separator className="mt-2" />

      {/* User panel */}
      <div className="flex items-center gap-2 px-3 py-3">
        <DropdownMenu>
          <DropdownMenuTrigger className="flex flex-1 items-center gap-2 rounded-lg p-1 hover:bg-accent/10 transition-colors">
            <Avatar className="h-8 w-8">
              <AvatarFallback>{user ? getInitials(user.username) : '?'}</AvatarFallback>
            </Avatar>
            <div className="flex-1 text-left min-w-0">
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
