import { useQueryClient } from '@tanstack/react-query'
import { Loader2, Sparkles } from 'lucide-react'
import { useEffect, useRef, useState } from 'react'

import { streamGenerateTasks } from '@/api/task-generation'
import { Skeleton } from '@/components/ui/skeleton'
import { useGenerationStore } from '@/store/generation-store'

interface Props {
  projectId: number
}

/**
 * Drives the AI-generation SSE stream for a single project.
 * Renders an overlay above the backlog column with skeleton cards
 * that fade-up into place at 180ms stagger.
 */
export function GenerationOverlay({ projectId }: Props) {
  const queryClient = useQueryClient()
  const status = useGenerationStore((s) => s.status)
  const diffusion = useGenerationStore((s) => s.diffusion)
  const tickets = useGenerationStore((s) => s.tickets)
  const targetCount = useGenerationStore((s) => s.targetCount)
  const errorMessage = useGenerationStore((s) => s.errorMessage)
  const reset = useGenerationStore((s) => s.reset)
  const consumePending = useGenerationStore((s) => s.consumePending)
  const start = useGenerationStore((s) => s.start)
  const setDiffusion = useGenerationStore((s) => s.setDiffusion)
  const appendBatch = useGenerationStore((s) => s.appendBatch)
  const finish = useGenerationStore((s) => s.finish)
  const fail = useGenerationStore((s) => s.fail)

  const launchedRef = useRef(false)
  const [dismissing, setDismissing] = useState(false)

  // Pick up a pending request scheduled by the create-project dialog.
  useEffect(() => {
    if (launchedRef.current) return
    const pending = consumePending()
    if (!pending || pending.projectId !== projectId) return
    launchedRef.current = true

    start(projectId, pending.config.task_count)

    const ctrl = new AbortController()
    streamGenerateTasks(projectId, pending.config, {
      onDiffusion: (plan) => setDiffusion(plan),
      onBatch: (_idx, batch) => {
        appendBatch(batch)
        queryClient.invalidateQueries({ queryKey: ['tickets', projectId] })
      },
      onDone: () => {
        finish()
        queryClient.invalidateQueries({ queryKey: ['tickets', projectId] })
      },
      onError: (msg) => fail(msg),
    }, ctrl.signal).catch((e) => {
      if (e?.name !== 'AbortError') fail(String(e?.message ?? e))
    })

    return () => ctrl.abort()
  }, [
    projectId, consumePending, start, setDiffusion, appendBatch,
    finish, fail, queryClient,
  ])

  // Auto-dismiss when done.
  useEffect(() => {
    if (status !== 'done') return
    const t = setTimeout(() => {
      setDismissing(true)
      setTimeout(() => reset(), 400)
    }, 800)
    return () => clearTimeout(t)
  }, [status, reset])

  if (status === 'idle') return null

  const placeholderCount = Math.max(0, targetCount - tickets.length)
  const skeletons = Array.from({ length: Math.min(placeholderCount, 6) })

  return (
    <div
      className={
        'pointer-events-none absolute inset-x-0 top-0 z-30 px-3 pt-3 transition-opacity duration-300 ' +
        (dismissing ? 'opacity-0' : 'opacity-100')
      }
    >
      <div className="pointer-events-auto rounded-lg border border-accent/40 bg-background/95 p-3 shadow-md backdrop-blur">
        <div className="flex items-center gap-2 text-sm font-medium">
          {status === 'error' ? (
            <span className="text-destructive">Generation failed</span>
          ) : status === 'done' ? (
            <>
              <Sparkles className="h-4 w-4 text-accent-foreground" />
              Generated {tickets.length} tickets
            </>
          ) : (
            <>
              <Loader2 className="h-4 w-4 animate-spin text-accent-foreground" />
              {status === 'analysing'
                ? 'Analysing project structure...'
                : `Generating tickets... ${tickets.length}/${targetCount}`}
            </>
          )}
        </div>

        {status === 'error' && errorMessage && (
          <p className="mt-1 text-xs text-muted-foreground">{errorMessage}</p>
        )}

        {diffusion.length > 0 && status !== 'error' && (
          <div className="mt-2 flex flex-wrap gap-1.5">
            {diffusion.map((d) => (
              <span
                key={d.category_id}
                className="inline-flex items-center gap-1 rounded-full border px-2 py-0.5 text-[10px] font-medium"
                style={{ borderColor: d.color, color: d.color }}
                title={d.description}
              >
                <span className="h-1.5 w-1.5 rounded-full" style={{ backgroundColor: d.color }} />
                {d.category_name}
              </span>
            ))}
          </div>
        )}

        {(status === 'generating' || status === 'analysing') && skeletons.length > 0 && (
          <div className="mt-3 space-y-2">
            {skeletons.map((_, i) => (
              <div
                key={i}
                className="animate-fade-up rounded-md border border-border bg-card p-3"
                style={{ animationDelay: `${i * 180}ms` }}
              >
                <Skeleton className="h-3 w-3/4" />
                <div className="mt-2 flex items-center gap-1.5">
                  <Skeleton className="h-3 w-10" />
                  <Skeleton className="h-3 w-14" />
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  )
}
