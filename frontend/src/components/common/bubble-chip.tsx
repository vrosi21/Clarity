/**
 * Single reusable chip for all recommender bubbles (category, tag, complexity, skills).
 *
 * Visual states map to lifecycle:
 *   suggested → user has not acted yet (outlined, clickable to accept)
 *   accepted  → applied (filled, brand-coloured, click to remove)
 *   rejected  → explicitly dismissed (greyed out, click to restore as suggested)
 *   new       → LLM proposed a name not in DB (dashed border + "New" badge)
 */
import { Check, Sparkles, X, Zap } from 'lucide-react'

import { cn } from '@/lib/utils'

export type BubbleState = 'suggested' | 'accepted' | 'rejected' | 'new'

interface Props {
  label: string
  state: BubbleState
  confidence?: number   // 0–1; rendered as "82%" badge when provided
  /** True when the chip was applied via auto-accept (lightning icon vs check). */
  autoApplied?: boolean
  disabled?: boolean
  onClick: () => void
  className?: string
}

export function BubbleChip({
  label,
  state,
  confidence,
  autoApplied,
  disabled,
  onClick,
  className,
}: Props) {
  const base =
    'inline-flex items-center gap-1 rounded-full border px-2.5 py-0.5 text-xs font-medium transition-all focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-1'

  const styles: Record<BubbleState, string> = {
    suggested:
      'border-border bg-background/60 text-foreground hover:bg-muted',
    accepted:
      'border-primary bg-primary/15 text-primary hover:bg-primary/25',
    rejected:
      'border-dashed border-border bg-muted/30 text-muted-foreground line-through opacity-70',
    new: 'border-dashed border-primary/50 text-primary/90 hover:border-primary hover:text-primary',
  }

  const Icon = () => {
    if (state === 'accepted') {
      return autoApplied ? <Zap className="h-3 w-3" /> : <Check className="h-3 w-3" />
    }
    if (state === 'rejected') return <X className="h-3 w-3" />
    if (state === 'new') return <Sparkles className="h-3 w-3" />
    return null
  }

  return (
    <button
      type="button"
      aria-pressed={state === 'accepted'}
      disabled={disabled}
      onClick={onClick}
      className={cn(
        base,
        styles[state],
        disabled && 'cursor-not-allowed opacity-50',
        className,
      )}
    >
      <Icon />
      <span>{label}</span>
      {state === 'new' && (
        <span className="rounded bg-primary/15 px-1 py-0.5 text-[9px] uppercase tracking-wide">
          New
        </span>
      )}
      {confidence !== undefined && state !== 'rejected' && (
        <span className="opacity-60">{Math.round(confidence * 100)}%</span>
      )}
    </button>
  )
}
