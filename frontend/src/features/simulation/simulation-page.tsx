import { useMutation, useQuery } from '@tanstack/react-query'
import { useEffect, useMemo, useRef, useState } from 'react'
import { Navigate } from 'react-router-dom'
import { toast } from 'sonner'

import { simulationApi } from '@/api/simulation'
import { ticketsApi } from '@/api/tickets'
import { Skeleton } from '@/components/ui/skeleton'
import { getApiErrorMessage } from '@/lib/utils'
import { useAuthStore } from '@/store/auth-store'
import { deriveBoardState, useSimulationStore } from '@/store/simulation-store'
import type { SimulationRun } from '@/types'

import { SimulationBoard } from './simulation-board'
import {
  SimulationConfigPanel,
  type TeamSource,
} from './simulation-config-panel'
import { SimulationHistoryPanel } from './simulation-history-panel'
import { SimulationPlaybackPanel } from './simulation-playback-panel'

export function SimulationPage() {
  const user = useAuthStore((s) => s.user)
  const hasPerm = user?.org_role?.permissions?.includes('simulation:run')
  if (user && !hasPerm) return <Navigate to="/projects" replace />

  const [projectId, setProjectId] = useState<number | null>(null)
  const [teamSource, setTeamSource] = useState<TeamSource>('project')
  const [syntheticTeamId, setSyntheticTeamId] = useState<number | null>(null)
  const [temperature, setTemperature] = useState(0.3)

  const currentRun = useSimulationStore((s) => s.currentRun)
  const cursorIndex = useSimulationStore((s) => s.cursorEventIndex)
  const isPlaying = useSimulationStore((s) => s.isPlaying)
  const speed = useSimulationStore((s) => s.speed)
  const cursorTime = useSimulationStore((s) => s.cursorTime)
  const setRun = useSimulationStore((s) => s.setRun)
  const resetCursor = useSimulationStore((s) => s.reset)
  const setCursorTime = useSimulationStore((s) => s.setCursorTime)
  const setPlaying = useSimulationStore((s) => s.setPlaying)

  // ── tickets for current project (initial board state) ─────────────────────
  const { data: tickets } = useQuery({
    queryKey: ['tickets', projectId],
    queryFn: () => ticketsApi.list(projectId!),
    enabled: projectId !== null,
  })

  // ── derive board state from initial tickets + events up to cursor ────────
  const board = useMemo(() => {
    if (!tickets) return new Map()
    return deriveBoardState(tickets, currentRun?.event_log ?? [], cursorIndex)
  }, [tickets, currentRun, cursorIndex])

  // ── run simulation mutation ───────────────────────────────────────────────
  const runMutation = useMutation({
    mutationFn: () =>
      simulationApi.runProject(projectId!, {
        team_source: teamSource,
        synthetic_team_id: teamSource === 'synthetic' ? syntheticTeamId : null,
        rl_config_overrides: { temperature },
      }),
    onSuccess: (run) => {
      setRun(run)
      toast.success(`Simulation run #${run.id} ready`)
    },
    onError: (e) => toast.error(getApiErrorMessage(e)),
  })

  // ── play loop: advance cursor by speed × elapsed wall-time minutes ───────
  const lastTickRef = useRef<number | null>(null)
  useEffect(() => {
    if (!isPlaying || !currentRun) {
      lastTickRef.current = null
      return
    }
    let raf = 0
    const totalTime =
      currentRun.event_log.length > 0
        ? currentRun.event_log[currentRun.event_log.length - 1].t
        : 0

    const tick = (ts: number) => {
      if (lastTickRef.current === null) lastTickRef.current = ts
      const dt = (ts - lastTickRef.current) / 1000 // seconds
      lastTickRef.current = ts
      // 1 wall-second = `speed` simulated minutes
      const nextT = cursorTime + dt * speed
      if (nextT >= totalTime) {
        setCursorTime(totalTime)
        setPlaying(false)
        return
      }
      setCursorTime(nextT)
      raf = requestAnimationFrame(tick)
    }
    raf = requestAnimationFrame(tick)
    return () => cancelAnimationFrame(raf)
  }, [isPlaying, currentRun, speed, cursorTime, setCursorTime, setPlaying])

  // reset run when project changes
  useEffect(() => {
    setRun(null)
  }, [projectId, setRun])

  useEffect(() => {
    document.title = 'Simulation — Clarity'
  }, [])

  if (!user) return null

  return (
    <div className="flex h-full overflow-hidden">
      <SimulationConfigPanel
        projectId={projectId}
        onProjectChange={setProjectId}
        teamSource={teamSource}
        onTeamSourceChange={setTeamSource}
        syntheticTeamId={syntheticTeamId}
        onSyntheticTeamChange={setSyntheticTeamId}
        temperature={temperature}
        onTemperatureChange={setTemperature}
        onRun={() => runMutation.mutate()}
        running={runMutation.isPending}
      />

      <main className="flex flex-1 flex-col overflow-hidden bg-muted/20">
        <div className="flex h-12 shrink-0 items-center justify-between border-b border-border bg-background px-6">
          <h1 className="text-sm font-semibold">Simulation</h1>
          {currentRun && (
            <div className="text-[10px] text-muted-foreground">
              Run #{currentRun.id} · {currentRun.team_source} ·
              τ={currentRun.rl_config_snapshot?.temperature?.toFixed(2)}
            </div>
          )}
        </div>
        <div className="flex-1 overflow-hidden">
          {!projectId && (
            <EmptyHero message="Select a project from the left to load its board." />
          )}
          {projectId && !tickets && (
            <div className="flex h-full gap-3 p-4">
              {Array.from({ length: 6 }).map((_, i) => (
                <Skeleton key={i} className="h-full w-64" />
              ))}
            </div>
          )}
          {projectId && tickets && <SimulationBoard board={board} />}
        </div>
      </main>

      {currentRun ? (
        <SimulationPlaybackPanel
          run={currentRun}
          board={board}
          onReplay={resetCursor}
        />
      ) : (
        <SimulationHistoryPanel projectId={projectId} onLoadRun={setRun} />
      )}
    </div>
  )
}

function EmptyHero({ message }: { message: string }) {
  return (
    <div className="flex h-full items-center justify-center px-6">
      <p className="max-w-sm text-center text-sm text-muted-foreground">{message}</p>
    </div>
  )
}

// Re-export for handler typing
export type { SimulationRun }
