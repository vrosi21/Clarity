import { useQuery } from '@tanstack/react-query'
import { Plus, Sparkles } from 'lucide-react'
import { useEffect, useState } from 'react'

import { membersApi } from '@/api/members'
import { rlConfigApi, workerProfileApi } from '@/api/simulation-extras'
import { simulationApi } from '@/api/simulation'
import { categoriesApi } from '@/api/categories'
import { projectsApi } from '@/api/projects'
import { Avatar, AvatarFallback } from '@/components/ui/avatar'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Label } from '@/components/ui/label'
import { ScrollArea } from '@/components/ui/scroll-area'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'
import { Slider } from '@/components/ui/slider'
import {
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from '@/components/ui/tooltip'
import { getInitials } from '@/lib/utils'
import type { Project } from '@/types'

import { SyntheticTeamBuilder } from './synthetic-team-builder'

export type TeamSource = 'project' | 'synthetic'

interface Props {
  projectId: number | null
  onProjectChange: (id: number | null) => void
  teamSource: TeamSource
  onTeamSourceChange: (s: TeamSource) => void
  syntheticTeamId: number | null
  onSyntheticTeamChange: (id: number | null) => void
  temperature: number
  onTemperatureChange: (t: number) => void
  onRun: () => void
  running: boolean
}

export function SimulationConfigPanel({
  projectId,
  onProjectChange,
  teamSource,
  onTeamSourceChange,
  syntheticTeamId,
  onSyntheticTeamChange,
  temperature,
  onTemperatureChange,
  onRun,
  running,
}: Props) {
  const [builderOpen, setBuilderOpen] = useState(false)

  const { data: projects } = useQuery({ queryKey: ['projects'], queryFn: projectsApi.list })
  const { data: categories } = useQuery({ queryKey: ['categories'], queryFn: categoriesApi.list })
  const { data: teams } = useQuery({
    queryKey: ['simulation', 'teams'],
    queryFn: simulationApi.listTeams,
  })

  const { data: rlConfig } = useQuery({
    queryKey: ['rl-config', projectId],
    queryFn: () => rlConfigApi.get(projectId!),
    enabled: projectId !== null,
  })

  // initial tau from project rl config
  useEffect(() => {
    if (rlConfig && temperature === 0.3) onTemperatureChange(rlConfig.temperature)
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [rlConfig])

  const canRun =
    projectId !== null &&
    !running &&
    (teamSource === 'project' || syntheticTeamId !== null)

  return (
    <aside className="flex h-full w-[280px] shrink-0 flex-col border-r border-border bg-card">
      <div className="border-b border-border px-4 py-3">
        <h2 className="flex items-center gap-2 text-sm font-semibold">
          <Sparkles className="h-4 w-4 text-accent" />
          Configuration
        </h2>
      </div>

      <ScrollArea className="flex-1 px-4 py-4">
        <div className="space-y-5">
          <div className="space-y-2">
            <Label>Project</Label>
            <Select
              value={projectId?.toString() ?? ''}
              onValueChange={(v) => onProjectChange(v ? Number(v) : null)}
            >
              <SelectTrigger>
                <SelectValue placeholder="Select a project" />
              </SelectTrigger>
              <SelectContent>
                {(projects ?? []).map((p: Project) => (
                  <SelectItem key={p.id} value={p.id.toString()}>
                    {p.name}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>

          <div className="space-y-2">
            <Label>Team source</Label>
            <div className="grid grid-cols-2 gap-1 rounded-md border border-border p-0.5">
              <button
                onClick={() => onTeamSourceChange('project')}
                className={cn(
                  'rounded px-2 py-1.5 text-xs font-medium transition-colors',
                  teamSource === 'project'
                    ? 'bg-accent/40 text-accent-foreground'
                    : 'text-muted-foreground hover:bg-accent/10',
                )}
              >
                Project Team
              </button>
              <button
                onClick={() => onTeamSourceChange('synthetic')}
                className={cn(
                  'rounded px-2 py-1.5 text-xs font-medium transition-colors',
                  teamSource === 'synthetic'
                    ? 'bg-accent/40 text-accent-foreground'
                    : 'text-muted-foreground hover:bg-accent/10',
                )}
              >
                Synthetic
              </button>
            </div>
          </div>

          {teamSource === 'project' && projectId && (
            <ProjectMembersList projectId={projectId} />
          )}

          {teamSource === 'synthetic' && (
            <div className="space-y-2">
              <Label>Synthetic team</Label>
              <Select
                value={syntheticTeamId?.toString() ?? ''}
                onValueChange={(v) => onSyntheticTeamChange(v ? Number(v) : null)}
              >
                <SelectTrigger>
                  <SelectValue placeholder="Pick a saved team" />
                </SelectTrigger>
                <SelectContent>
                  {(teams ?? []).map((t) => (
                    <SelectItem key={t.id} value={t.id.toString()}>
                      {t.name} · {t.worker_count}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
              <Button
                variant="outline"
                size="sm"
                className="w-full"
                onClick={() => setBuilderOpen(true)}
              >
                <Plus className="h-3.5 w-3.5" />
                Create new team
              </Button>
            </div>
          )}

          <div className="space-y-2 border-t border-border pt-4">
            <div className="flex items-center justify-between">
              <Label>RL temperature (τ)</Label>
              <TooltipProvider delayDuration={150}>
                <Tooltip>
                  <TooltipTrigger asChild>
                    <span className="font-mono text-xs">{temperature.toFixed(2)}</span>
                  </TooltipTrigger>
                  <TooltipContent side="left" className="max-w-xs">
                    High τ encourages workers to take on less-matched tasks to broaden skills;
                    low τ exploits the best-fit assignment.
                  </TooltipContent>
                </Tooltip>
              </TooltipProvider>
            </div>
            <Slider
              min={0.05}
              max={1}
              step={0.01}
              value={temperature}
              onChange={onTemperatureChange}
              aria-label="Temperature"
            />
            <div className="flex justify-between text-[10px] text-muted-foreground">
              <span>Exploitation</span>
              <span>Exploration</span>
            </div>
          </div>
        </div>
      </ScrollArea>

      <div className="border-t border-border p-3">
        <Button className="w-full" disabled={!canRun} onClick={onRun}>
          {running ? 'Running…' : 'Run Simulation'}
        </Button>
      </div>

      {categories && (
        <SyntheticTeamBuilder
          open={builderOpen}
          onOpenChange={setBuilderOpen}
          categories={categories}
          onCreated={(team) => onSyntheticTeamChange(team.id)}
        />
      )}
    </aside>
  )
}

function cn(...c: (string | false | null | undefined)[]) {
  return c.filter(Boolean).join(' ')
}

function ProjectMembersList({ projectId }: { projectId: number }) {
  const { data: members } = useQuery({
    queryKey: ['members', projectId],
    queryFn: () => membersApi.list(projectId),
  })

  return (
    <div className="space-y-1.5">
      <Label className="text-[11px] uppercase tracking-wide text-muted-foreground">
        Members ({members?.length ?? 0})
      </Label>
      <div className="space-y-1.5">
        {(members ?? []).map((m) => (
          <MemberRow key={m.user_id} userId={m.user_id} username={m.username} role={m.role_name} />
        ))}
        {members && members.length === 0 && (
          <p className="text-xs text-muted-foreground">No members yet.</p>
        )}
      </div>
    </div>
  )
}

function MemberRow({ userId, username, role }: { userId: number; username: string; role: string }) {
  const { data: profile } = useQuery({
    queryKey: ['worker-profile', userId],
    queryFn: () => workerProfileApi.get(userId),
    retry: false,
  })

  const avgProf =
    profile && profile.skill_profiles.length
      ? profile.skill_profiles.reduce((s, p) => s + p.proficiency, 0) /
        profile.skill_profiles.length
      : null

  return (
    <div className="rounded-md border border-border/60 bg-background/50 p-2">
      <div className="flex items-center gap-2">
        <Avatar className="h-6 w-6">
          <AvatarFallback className="text-[10px]">{getInitials(username)}</AvatarFallback>
        </Avatar>
        <div className="min-w-0 flex-1">
          <div className="truncate text-xs font-medium">{username}</div>
          <div className="truncate text-[10px] text-muted-foreground">{role}</div>
        </div>
        {profile && (
          <Badge variant="outline" className="h-4 px-1 text-[9px] capitalize">
            {profile.seniority}
          </Badge>
        )}
      </div>
      {avgProf !== null && (
        <div className="mt-1.5 flex items-center gap-1.5">
          <div className="h-1 flex-1 overflow-hidden rounded-full bg-muted">
            <div
              className="h-full rounded-full bg-accent"
              style={{ width: `${Math.round(avgProf * 100)}%` }}
            />
          </div>
          <span className="font-mono text-[9px] text-muted-foreground">
            {(avgProf * 100).toFixed(0)}%
          </span>
        </div>
      )}
    </div>
  )
}
