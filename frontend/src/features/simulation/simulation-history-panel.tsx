import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { Trash2 } from 'lucide-react'
import { toast } from 'sonner'

import { simulationApi } from '@/api/simulation'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { ScrollArea } from '@/components/ui/scroll-area'
import { Skeleton } from '@/components/ui/skeleton'
import { formatRelative, getApiErrorMessage } from '@/lib/utils'
import { useAuthStore } from '@/store/auth-store'
import type { SimulationRun, SimulationRunSummary } from '@/types'

interface Props {
  projectId: number | null
  onLoadRun: (run: SimulationRun) => void
}

export function SimulationHistoryPanel({ projectId, onLoadRun }: Props) {
  const queryClient = useQueryClient()
  const user = useAuthStore((s) => s.user)
  const isRoot = user?.org_role?.role_name === 'root_user'

  const { data: runs, isPending } = useQuery({
    queryKey: ['simulation', 'runs', projectId],
    queryFn: () => simulationApi.listRuns(projectId!),
    enabled: projectId !== null,
  })

  const loadMutation = useMutation({
    mutationFn: (id: number) => simulationApi.getRun(id),
    onSuccess: (run) => onLoadRun(run),
    onError: (e) => toast.error(getApiErrorMessage(e)),
  })

  return (
    <aside className="flex h-full w-[300px] shrink-0 flex-col border-l border-border bg-card">
      <div className="border-b border-border px-4 py-3">
        <h2 className="text-sm font-semibold">Run history</h2>
        <p className="mt-0.5 text-[10px] text-muted-foreground">
          {projectId ? `${runs?.length ?? 0} past runs` : 'Select a project'}
        </p>
      </div>
      <ScrollArea className="flex-1 px-3 py-3">
        {!projectId && (
          <p className="px-2 text-xs text-muted-foreground">
            Pick a project to view its history.
          </p>
        )}
        {projectId && isPending && (
          <div className="space-y-2">
            {Array.from({ length: 4 }).map((_, i) => (
              <Skeleton key={i} className="h-20 w-full" />
            ))}
          </div>
        )}
        {runs && runs.length === 0 && (
          <p className="px-2 text-xs text-muted-foreground">No runs yet.</p>
        )}
        <ul className="space-y-2">
          {(runs ?? []).map((r) => (
            <RunCard
              key={r.id}
              run={r}
              isRoot={isRoot}
              currentUserId={user?.id ?? 0}
              onClick={() => loadMutation.mutate(r.id)}
              onDelete={async () => {
                // Backend doesn't expose run delete (only team delete); soft-disable here.
                toast.message('Run deletion not supported.')
                queryClient.invalidateQueries({ queryKey: ['simulation', 'runs', projectId] })
              }}
            />
          ))}
        </ul>
      </ScrollArea>
    </aside>
  )
}

function RunCard({
  run,
  isRoot,
  currentUserId,
  onClick,
  onDelete,
}: {
  run: SimulationRunSummary
  isRoot: boolean
  currentUserId: number
  onClick: () => void
  onDelete: () => void
}) {
  const canDelete = isRoot || run.created_by === currentUserId
  const summary = run.summary as Record<string, number>
  return (
    <li>
      <button
        onClick={onClick}
        className="w-full rounded-md border border-border/60 bg-background/40 p-2.5 text-left hover:border-accent/40 hover:bg-accent/5"
      >
        <div className="flex items-center justify-between gap-2">
          <span className="text-xs font-medium">Run #{run.id}</span>
          <Badge
            variant="outline"
            className={`h-4 px-1 text-[9px] ${
              run.status === 'completed'
                ? 'border-emerald-500/30 text-emerald-700 dark:text-emerald-300'
                : 'border-red-500/30 text-red-700 dark:text-red-300'
            }`}
          >
            {run.status}
          </Badge>
        </div>
        <div className="mt-1 flex items-center justify-between text-[10px] text-muted-foreground">
          <span>{formatRelative(run.created_at)}</span>
          <span>{run.team_source}</span>
        </div>
        {summary && Object.keys(summary).length > 0 && (
          <div className="mt-2 grid grid-cols-3 gap-1 text-[10px]">
            <div>
              <div className="text-muted-foreground">Time</div>
              <div className="font-mono">{summary.total_time?.toFixed(0) ?? '–'}m</div>
            </div>
            <div>
              <div className="text-muted-foreground">Eff</div>
              <div className="font-mono">{summary.avg_efficiency?.toFixed(2) ?? '–'}</div>
            </div>
            <div>
              <div className="text-muted-foreground">Tasks</div>
              <div className="font-mono">{summary.n_tasks ?? 0}</div>
            </div>
          </div>
        )}
        {canDelete && (
          <div className="mt-2 flex justify-end">
            <Button
              variant="ghost"
              size="icon"
              className="h-6 w-6 opacity-50 hover:opacity-100"
              onClick={(e) => {
                e.stopPropagation()
                onDelete()
              }}
              aria-label="Delete run"
            >
              <Trash2 className="h-3 w-3" />
            </Button>
          </div>
        )}
      </button>
    </li>
  )
}
