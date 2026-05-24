import { Loader2, Sparkles } from 'lucide-react'
import { useEffect, useState } from 'react'

import { useGenerationStore } from '@/store/generation-store'

interface Props {
  projectId: number
}

/**
 * Compact status pill rendered in the board header area. Skeletons + revealed
 * ticket cards live inside the BACKLOG BoardColumn now — this component just
 * shows generation progress + the category diffusion chips.
 */
export function GenerationOverlay({ projectId }: Props) {
  const status = useGenerationStore((s) => s.status)
  const storeProjectId = useGenerationStore((s) => s.projectId)
  const diffusion = useGenerationStore((s) => s.diffusion)
  const visibleCount = useGenerationStore((s) => s.visibleCount)
  const targetCount = useGenerationStore((s) => s.targetCount)
  const errorMessage = useGenerationStore((s) => s.errorMessage)
  const reset = useGenerationStore((s) => s.reset)

  const [dismissing, setDismissing] = useState(false)

  useEffect(() => {
    if (status !== 'done') return
    let inner: ReturnType<typeof setTimeout> | null = null
    const outer = setTimeout(() => {
      setDismissing(true)
      inner = setTimeout(() => reset(), 400)
    }, 1000)
    return () => {
      clearTimeout(outer)
      if (inner) clearTimeout(inner)
    }
  }, [status, reset])

  useEffect(() => {
    if (status !== 'done') setDismissing(false)
  }, [status])

  if (status === 'idle' || storeProjectId !== projectId) return null

  return (
    <div
      className={
        'pointer-events-none absolute right-3 top-3 z-30 max-w-md transition-opacity duration-300 ' +
        (dismissing ? 'opacity-0' : 'opacity-100')
      }
    >
      <div className="pointer-events-auto rounded-full border border-accent/40 bg-background/95 px-3 py-1.5 shadow-md backdrop-blur">
        <div className="flex items-center gap-2 text-xs">
          {status === 'error' ? (
            <>
              <span className="font-medium text-destructive">Generation failed</span>
              {errorMessage && (
                <span className="truncate text-muted-foreground">· {errorMessage}</span>
              )}
            </>
          ) : status === 'done' ? (
            <>
              <Sparkles className="h-3.5 w-3.5 text-accent-foreground" />
              <span className="font-medium">Generated {targetCount} tickets</span>
            </>
          ) : (
            <>
              <Loader2 className="h-3.5 w-3.5 animate-spin text-accent-foreground" />
              <span className="font-medium">
                {status === 'analysing'
                  ? 'Analysing project…'
                  : `Generating ${visibleCount}/${targetCount}`}
              </span>
              {diffusion.length > 0 && (
                <div className="ml-1 flex items-center gap-1">
                  {diffusion.slice(0, 5).map((d) => (
                    <span
                      key={d.category_id}
                      className="h-1.5 w-1.5 rounded-full"
                      style={{ backgroundColor: d.color }}
                      title={d.category_name}
                    />
                  ))}
                </div>
              )}
            </>
          )}
        </div>
      </div>
    </div>
  )
}
