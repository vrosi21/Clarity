import { ChevronLeft, ChevronRight, Pause, Play, RotateCcw } from 'lucide-react'
import { useMemo } from 'react'

import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Label } from '@/components/ui/label'
import { ScrollArea } from '@/components/ui/scroll-area'
import { Slider } from '@/components/ui/slider'
import { cn } from '@/lib/utils'
import { useSimulationStore, type SimBoardEntry } from '@/store/simulation-store'
import type { SimulationEvent, SimulationRun } from '@/types'

interface Props {
  run: SimulationRun
  board: Map<number, SimBoardEntry>
  onReplay: () => void
}

const TYPE_BADGE: Record<string, string> = {
  assigned: 'bg-blue-500/15 text-blue-700 dark:text-blue-300 border-blue-500/30',
  stage_changed: 'bg-zinc-500/10 text-zinc-700 dark:text-zinc-300 border-zinc-500/30',
  completed: 'bg-emerald-500/15 text-emerald-700 dark:text-emerald-300 border-emerald-500/30',
  blocked: 'bg-red-500/15 text-red-700 dark:text-red-300 border-red-500/30',
  rejected: 'bg-orange-500/15 text-orange-700 dark:text-orange-300 border-orange-500/30',
}

export function SimulationPlaybackPanel({ run, board, onReplay }: Props) {
  const isPlaying = useSimulationStore((s) => s.isPlaying)
  const speed = useSimulationStore((s) => s.speed)
  const cursorTime = useSimulationStore((s) => s.cursorTime)
  const cursorIndex = useSimulationStore((s) => s.cursorEventIndex)
  const setPlaying = useSimulationStore((s) => s.setPlaying)
  const setSpeed = useSimulationStore((s) => s.setSpeed)
  const setCursorTime = useSimulationStore((s) => s.setCursorTime)
  const step = useSimulationStore((s) => s.step)

  const totalTime = useMemo(
    () => (run.event_log.length ? run.event_log[run.event_log.length - 1].t : 1),
    [run],
  )

  const visibleEvents = run.event_log.slice(0, cursorIndex).slice(-30).reverse()
  const ended = cursorIndex >= run.event_log.length

  const completedCount = useMemo(
    () => Array.from(board.values()).filter((b) => b.stage === 'DONE').length,
    [board],
  )
  const blockedNowCount = useMemo(
    () => Array.from(board.values()).filter((b) => b.stage === 'BLOCKED').length,
    [board],
  )
  // Rejection is transient (ticket bounces back to IN_PROGRESS), so count
  // rejection events seen up to the cursor rather than current board state.
  const rejectedSoFar = useMemo(
    () => run.event_log.slice(0, cursorIndex).filter((e) => e.type === 'rejected').length,
    [run, cursorIndex],
  )
  const workerLoad = useMemo(() => {
    const map = new Map<string, number>()
    for (const b of board.values()) {
      if (b.worker_name && b.stage !== 'DONE') {
        map.set(b.worker_name, (map.get(b.worker_name) ?? 0) + 1)
      }
    }
    return Array.from(map.entries()).sort((a, b) => b[1] - a[1])
  }, [board])

  return (
    <aside className="flex h-full w-[300px] shrink-0 flex-col border-l border-border bg-card">
      <div className="border-b border-border px-4 py-3">
        <h2 className="text-sm font-semibold">Playback</h2>
        <p className="mt-0.5 text-[10px] text-muted-foreground">
          t = {cursorTime.toFixed(1)} min / {totalTime.toFixed(0)} min
        </p>
      </div>

      {/* Timeline scrubber */}
      <div className="border-b border-border px-4 py-3">
        <div className="relative h-6">
          <Slider
            min={0}
            max={totalTime}
            step={0.1}
            value={cursorTime}
            onChange={setCursorTime}
            aria-label="Timeline"
            className="absolute inset-x-0 top-2.5"
          />
          <div className="pointer-events-none absolute inset-x-0 top-0 h-1 overflow-hidden">
            {run.event_log.map((e, i) => (
              <span
                key={i}
                className="absolute top-0 h-1 w-px bg-foreground/30"
                style={{ left: `${(e.t / totalTime) * 100}%` }}
              />
            ))}
          </div>
        </div>
        <div className="mt-3 flex items-center justify-center gap-1">
          <Button variant="ghost" size="icon" onClick={() => step(-1)} aria-label="Previous event">
            <ChevronLeft className="h-4 w-4" />
          </Button>
          {ended ? (
            <Button variant="default" size="icon" onClick={onReplay} aria-label="Replay">
              <RotateCcw className="h-4 w-4" />
            </Button>
          ) : (
            <Button
              variant="default"
              size="icon"
              onClick={() => setPlaying(!isPlaying)}
              aria-label={isPlaying ? 'Pause' : 'Play'}
            >
              {isPlaying ? <Pause className="h-4 w-4" /> : <Play className="h-4 w-4" />}
            </Button>
          )}
          <Button variant="ghost" size="icon" onClick={() => step(1)} aria-label="Next event">
            <ChevronRight className="h-4 w-4" />
          </Button>
        </div>
        <div className="mt-3 space-y-1">
          <div className="flex items-center justify-between">
            <Label className="text-[10px] uppercase">Speed</Label>
            <span className="font-mono text-[10px]">{speed.toFixed(1)}×</span>
          </div>
          <Slider min={0.5} max={10} step={0.5} value={speed} onChange={setSpeed} aria-label="Speed" />
        </div>
      </div>

      {/* Live stats */}
      <div className="border-b border-border px-4 py-3 space-y-2">
        <h3 className="text-[11px] font-semibold uppercase tracking-wide text-muted-foreground">
          Live stats
        </h3>
        <div className="grid grid-cols-2 gap-2 text-xs">
          <Stat label="Completed" value={`${completedCount}/${board.size}`} />
          <Stat label="Blocked now" value={String(blockedNowCount)} />
          <Stat label="Rejected" value={String(rejectedSoFar)} />
        </div>
        {workerLoad.length > 0 && (
          <div className="space-y-1 pt-2">
            <p className="text-[10px] uppercase text-muted-foreground">Worker load</p>
            {workerLoad.slice(0, 5).map(([name, count]) => (
              <div key={name} className="flex items-center gap-2">
                <span className="w-20 truncate text-[10px]">{name}</span>
                <div className="h-1 flex-1 overflow-hidden rounded-full bg-muted">
                  <div
                    className="h-full rounded-full bg-amber-500/70"
                    style={{ width: `${Math.min(100, count * 20)}%` }}
                  />
                </div>
                <span className="w-4 text-right font-mono text-[10px]">{count}</span>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Event feed */}
      <div className="flex-1 overflow-hidden">
        <div className="border-b border-border px-4 py-2">
          <h3 className="text-[11px] font-semibold uppercase tracking-wide text-muted-foreground">
            Event feed ({cursorIndex}/{run.event_log.length})
          </h3>
        </div>
        <ScrollArea className="h-full px-3 py-2">
          <ul className="space-y-1.5 pb-6">
            {visibleEvents.map((ev, i) => (
              <EventRow key={`${ev.t}-${i}`} event={ev} />
            ))}
            {visibleEvents.length === 0 && (
              <p className="px-2 text-xs text-muted-foreground">No events yet.</p>
            )}
          </ul>
        </ScrollArea>
      </div>

      {ended && run.summary && Object.keys(run.summary).length > 0 && (
        <SummaryFooter summary={run.summary as Record<string, number>} />
      )}
    </aside>
  )
}

function EventRow({ event }: { event: SimulationEvent }) {
  const text = describe(event)
  return (
    <li className="rounded border border-border/60 bg-background/40 px-2 py-1.5 text-[11px]">
      <div className="flex items-center justify-between gap-2">
        <Badge variant="outline" className={cn('h-4 px-1 text-[9px]', TYPE_BADGE[event.type])}>
          {event.type}
        </Badge>
        <span className="font-mono text-[9px] text-muted-foreground">
          t={event.t.toFixed(1)}
        </span>
      </div>
      <p className="mt-1 line-clamp-2 leading-tight">{text}</p>
    </li>
  )
}

function describe(e: SimulationEvent): string {
  switch (e.type) {
    case 'assigned':
      return `${e.worker_name} assigned to "${e.ticket_title}"`
    case 'completed':
      return `${e.worker_name} completed "${e.ticket_title}"`
    case 'blocked':
      return `"${e.ticket_title}" blocked while assigned to ${e.worker_name}`
    case 'rejected':
      return `"${e.ticket_title}" rejected from review — ${e.worker_name} reworks`
    case 'stage_changed':
      return `"${e.ticket_title}" moved ${e.from_stage} → ${e.to_stage}`
    default:
      return e.ticket_title
  }
}

function Stat({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded border border-border/60 bg-background/40 px-2 py-1.5">
      <div className="text-[9px] uppercase text-muted-foreground">{label}</div>
      <div className="font-mono text-sm font-medium">{value}</div>
    </div>
  )
}

function SummaryFooter({ summary }: { summary: Record<string, number> }) {
  return (
    <div className="border-t border-border bg-emerald-500/[0.04] px-4 py-3">
      <h3 className="text-[11px] font-semibold uppercase tracking-wide text-emerald-700 dark:text-emerald-300">
        Run complete
      </h3>
      <div className="mt-2 grid grid-cols-2 gap-2 text-xs">
        <Stat label="Total time" value={`${summary.total_time?.toFixed(0) ?? '–'} min`} />
        <Stat
          label="Avg efficiency"
          value={summary.avg_efficiency ? summary.avg_efficiency.toFixed(2) : '–'}
        />
        <Stat label="Tasks" value={String(summary.n_tasks ?? 0)} />
        <Stat label="Blocked" value={String(summary.n_blocked ?? 0)} />
        <Stat label="Rejected" value={String(summary.n_rejected ?? 0)} />
      </div>
    </div>
  )
}
