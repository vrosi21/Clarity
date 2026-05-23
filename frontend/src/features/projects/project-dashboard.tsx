import { useQuery } from '@tanstack/react-query'
import {
  Calendar,
  Kanban,
  Settings,
  Users,
  Wrench,
} from 'lucide-react'
import { useEffect, useMemo, useState } from 'react'
import { Link, useParams } from 'react-router-dom'

import { ProjectSettingsSheet } from '@/features/settings/ProjectSettingsSheet'

import { membersApi } from '@/api/members'
import { projectsApi } from '@/api/projects'
import { stagesApi } from '@/api/stages'
import { ticketsApi } from '@/api/tickets'
import { Avatar, AvatarFallback } from '@/components/ui/avatar'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Skeleton } from '@/components/ui/skeleton'
import { TeamManagementSheet } from '@/features/projects/team-management-sheet'
import { usePermissions } from '@/hooks/use-permissions'
import { cn, getInitials } from '@/lib/utils'
import { useAuthStore } from '@/store/auth-store'
import type { Priority, Ticket } from '@/types'

const PRIORITY_LABEL: Record<Priority, string> = {
  p1: 'P1',
  p2: 'P2',
  p3: 'P3',
  p4: 'P4',
  p5: 'P5',
}

const PRIORITY_COLOR: Record<Priority, string> = {
  p1: 'bg-red-500',
  p2: 'bg-orange-400',
  p3: 'bg-yellow-400',
  p4: 'bg-blue-400',
  p5: 'bg-slate-400',
}

function StatCard({
  label,
  value,
  sub,
  accent,
}: {
  label: string
  value: number | string
  sub?: string
  accent?: string
}) {
  return (
    <Card>
      <CardContent className="pt-5 pb-4 px-5">
        <p className="text-xs font-medium uppercase tracking-wide text-muted-foreground">{label}</p>
        <p className={cn('mt-1 text-3xl font-bold tabular-nums', accent)}>{value}</p>
        {sub && <p className="mt-0.5 text-xs text-muted-foreground">{sub}</p>}
      </CardContent>
    </Card>
  )
}

function ProgressBar({ pct }: { pct: number }) {
  return (
    <div className="h-2 w-full overflow-hidden rounded-full bg-muted">
      <div
        className="h-full rounded-full bg-accent transition-all duration-500"
        style={{ width: `${Math.min(100, pct)}%` }}
      />
    </div>
  )
}

function countByPriority(tickets: Ticket[]) {
  const counts: Record<Priority, number> = { p1: 0, p2: 0, p3: 0, p4: 0, p5: 0 }
  for (const t of tickets) counts[t.priority]++
  return counts
}

export function ProjectDashboard() {
  const { projectId } = useParams<{ projectId: string }>()
  const id = Number(projectId)
  const currentUser = useAuthStore((s) => s.user)
  const [manageOpen, setManageOpen] = useState(false)
  const [settingsOpen, setSettingsOpen] = useState(false)

  const { data: project } = useQuery({
    queryKey: ['project', id],
    queryFn: () => projectsApi.get(id),
    enabled: !Number.isNaN(id),
  })
  const { data: stages } = useQuery({
    queryKey: ['stages', id],
    queryFn: () => stagesApi.list(id),
    enabled: !Number.isNaN(id),
  })
  const { data: tickets } = useQuery({
    queryKey: ['tickets', id],
    queryFn: () => ticketsApi.list(id),
    enabled: !Number.isNaN(id),
  })
  const { data: members } = useQuery({
    queryKey: ['members', id],
    queryFn: () => membersApi.list(id),
    enabled: !Number.isNaN(id),
  })

  useEffect(() => {
    document.title = project ? `${project.name} — Clarity` : 'Project — Clarity'
  }, [project])

  const myMember = members?.find((m) => m.user_id === currentUser?.id)
  const { can, isAdmin } = usePermissions(myMember)
  const canManage = can('projects:manage_members') || isAdmin

  const stats = useMemo(() => {
    if (!tickets || !stages) return null

    const stageMap = new Map(stages.map((s) => [s.id, s]))
    const finalStageIds = new Set(stages.filter((s) => s.type === 'final').map((s) => s.id))
    const startStageIds = new Set(stages.filter((s) => s.type === 'start').map((s) => s.id))

    const total = tickets.length
    const done = tickets.filter((t) => finalStageIds.has(t.stage_id)).length
    const backlog = tickets.filter((t) => startStageIds.has(t.stage_id)).length
    const active = total - done - backlog
    const pct = total > 0 ? Math.round((done / total) * 100) : 0

    const byStage: { id: number; name: string; color: string | null; count: number }[] = stages
      .map((s) => ({
        id: s.id,
        name: s.name,
        color: s.color,
        count: tickets.filter((t) => t.stage_id === s.id).length,
      }))
      .filter((s) => s.count > 0)

    const priorities = countByPriority(tickets)

    const assigneeCounts = new Map<number, number>()
    for (const t of tickets) {
      if (t.assignee_id) {
        assigneeCounts.set(t.assignee_id, (assigneeCounts.get(t.assignee_id) ?? 0) + 1)
      }
    }
    const unassigned = tickets.filter((t) => !t.assignee_id).length

    return { total, done, backlog, active, pct, byStage, priorities, assigneeCounts, unassigned, stageMap }
  }, [tickets, stages])

  if (Number.isNaN(id)) {
    return <div className="p-8 text-sm text-muted-foreground">Invalid project ID.</div>
  }

  return (
    <div className="h-full overflow-y-auto">
      <div className="mx-auto max-w-5xl px-6 py-8 space-y-8">

        {/* Header */}
        <div className="flex items-start justify-between gap-4">
          <div className="min-w-0">
            <h1 className="text-2xl font-semibold tracking-tight truncate">
              {project?.name ?? <Skeleton className="inline-block h-7 w-48" />}
            </h1>
            {project?.description && (
              <p className="mt-1 text-sm text-muted-foreground">{project.description}</p>
            )}
            {project?.created_at && (
              <div className="mt-2 flex items-center gap-1.5 text-xs text-muted-foreground">
                <Calendar className="h-3.5 w-3.5" />
                Created {new Date(project.created_at).toLocaleDateString()}
              </div>
            )}
          </div>
          <div className="flex items-center gap-2 shrink-0">
            <Button variant="outline" size="sm" onClick={() => setSettingsOpen(true)}>
              <Settings className="h-4 w-4" />
              Settings
            </Button>
            <Button size="sm" asChild>
              <Link to={`/projects/${id}/board`}>
                <Kanban className="h-4 w-4" />
                Agile Board
              </Link>
            </Button>
          </div>
        </div>

        {/* Stat cards */}
        {!stats ? (
          <div className="grid grid-cols-2 gap-4 sm:grid-cols-4">
            {Array.from({ length: 4 }).map((_, i) => (
              <Skeleton key={i} className="h-24 w-full" />
            ))}
          </div>
        ) : (
          <div className="grid grid-cols-2 gap-4 sm:grid-cols-4">
            <StatCard label="Total" value={stats.total} sub="tickets" />
            <StatCard label="Backlog" value={stats.backlog} sub="not started" />
            <StatCard label="Active" value={stats.active} sub="in progress" accent="text-accent" />
            <StatCard
              label="Done"
              value={stats.done}
              sub={`${stats.pct}% complete`}
              accent="text-green-500"
            />
          </div>
        )}

        {/* Progress + Priority row */}
        {stats && (
          <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
            {/* Progress */}
            <Card>
              <CardHeader className="pb-2 pt-5 px-5">
                <CardTitle className="text-sm font-medium">Completion</CardTitle>
              </CardHeader>
              <CardContent className="px-5 pb-5 space-y-3">
                <div className="flex items-end justify-between">
                  <span className="text-4xl font-bold tabular-nums text-green-500">
                    {stats.pct}%
                  </span>
                  <span className="text-xs text-muted-foreground">
                    {stats.done} / {stats.total} tickets
                  </span>
                </div>
                <ProgressBar pct={stats.pct} />
                {stats.unassigned > 0 && (
                  <p className="text-xs text-muted-foreground">
                    {stats.unassigned} ticket{stats.unassigned !== 1 ? 's' : ''} unassigned
                  </p>
                )}
              </CardContent>
            </Card>

            {/* Priority breakdown */}
            <Card>
              <CardHeader className="pb-2 pt-5 px-5">
                <CardTitle className="text-sm font-medium">Priority Breakdown</CardTitle>
              </CardHeader>
              <CardContent className="px-5 pb-5">
                <div className="space-y-2">
                  {(['p1', 'p2', 'p3', 'p4', 'p5'] as Priority[]).map((p) => {
                    const count = stats.priorities[p]
                    const pct = stats.total > 0 ? (count / stats.total) * 100 : 0
                    return (
                      <div key={p} className="flex items-center gap-3">
                        <span className="w-6 text-xs font-mono text-muted-foreground">
                          {PRIORITY_LABEL[p]}
                        </span>
                        <div className="flex-1 h-1.5 overflow-hidden rounded-full bg-muted">
                          <div
                            className={cn('h-full rounded-full', PRIORITY_COLOR[p])}
                            style={{ width: `${pct}%` }}
                          />
                        </div>
                        <span className="w-5 text-right text-xs tabular-nums text-muted-foreground">
                          {count}
                        </span>
                      </div>
                    )
                  })}
                </div>
              </CardContent>
            </Card>
          </div>
        )}

        {/* Stage breakdown */}
        {stats && stats.byStage.length > 0 && (
          <Card>
            <CardHeader className="pb-2 pt-5 px-5">
              <CardTitle className="text-sm font-medium">Tickets by Stage</CardTitle>
            </CardHeader>
            <CardContent className="px-5 pb-5">
              <div className="flex flex-wrap gap-3">
                {stats.byStage.map((s) => (
                  <div
                    key={s.id}
                    className="flex items-center gap-2 rounded-full border border-border bg-muted/30 px-3 py-1.5"
                  >
                    {s.color && (
                      <span
                        className="h-2.5 w-2.5 rounded-full shrink-0"
                        style={{ backgroundColor: s.color }}
                      />
                    )}
                    <span className="text-sm">{s.name}</span>
                    <span className="text-sm font-semibold tabular-nums">{s.count}</span>
                  </div>
                ))}
              </div>
            </CardContent>
          </Card>
        )}

        {/* Team card */}
        <Card>
          <CardHeader className="pb-3 pt-5 px-5">
            <div className="flex items-center justify-between">
              <CardTitle className="text-sm font-medium flex items-center gap-2">
                <Users className="h-4 w-4" />
                Team
                {members && (
                  <span className="text-xs font-normal text-muted-foreground">
                    {members.length} member{members.length !== 1 ? 's' : ''}
                  </span>
                )}
              </CardTitle>
              {canManage && (
                <Button
                  variant="outline"
                  size="sm"
                  onClick={() => setManageOpen(true)}
                  className="h-7 gap-1.5 text-xs"
                >
                  <Wrench className="h-3.5 w-3.5" />
                  Manage
                </Button>
              )}
            </div>
          </CardHeader>
          <CardContent className="px-5 pb-5">
            {!members && (
              <div className="flex flex-wrap gap-3">
                {Array.from({ length: 3 }).map((_, i) => (
                  <Skeleton key={i} className="h-14 w-40" />
                ))}
              </div>
            )}
            {members && members.length === 0 && (
              <p className="text-sm text-muted-foreground">No members yet.</p>
            )}
            {members && members.length > 0 && (
              <div className="flex flex-wrap gap-3">
                {members.map((m) => {
                  const assignedCount = stats?.assigneeCounts.get(m.user_id) ?? 0
                  const isMe = m.user_id === currentUser?.id

                  return (
                    <div
                      key={m.user_id}
                      className="flex items-center gap-2.5 rounded-lg border border-border bg-card px-3 py-2.5 min-w-0"
                    >
                      <Avatar className="h-8 w-8 shrink-0">
                        <AvatarFallback className="text-xs">
                          {getInitials(m.username)}
                        </AvatarFallback>
                      </Avatar>
                      <div className="min-w-0">
                        <div className="flex items-center gap-1">
                          <span className="truncate text-sm font-medium">{m.username}</span>
                          {isMe && (
                            <span className="text-xs text-muted-foreground shrink-0">(you)</span>
                          )}
                        </div>
                        <div className="flex items-center gap-2 mt-0.5">
                          <Badge variant="outline" className="text-xs capitalize h-4 px-1.5 py-0">
                            {m.role_name}
                          </Badge>
                          {assignedCount > 0 && (
                            <span className="text-xs text-muted-foreground">
                              {assignedCount} ticket{assignedCount !== 1 ? 's' : ''}
                            </span>
                          )}
                        </div>
                      </div>
                    </div>
                  )
                })}
              </div>
            )}
          </CardContent>
        </Card>

      </div>

      <TeamManagementSheet
        projectId={id}
        open={manageOpen}
        onOpenChange={setManageOpen}
      />

      <ProjectSettingsSheet
        projectId={id}
        projectName={project?.name}
        open={settingsOpen}
        onOpenChange={setSettingsOpen}
      />
    </div>
  )
}
