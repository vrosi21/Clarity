import { Plus, Sparkles } from 'lucide-react'

import { Avatar, AvatarFallback } from '@/components/ui/avatar'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Skeleton } from '@/components/ui/skeleton'
import { TicketCard } from '@/features/board/ticket-card'
import { cn } from '@/lib/utils'
import type { Stage, Ticket } from '@/types'
import type { GeneratedTicket } from '@/api/task-generation'

const STAGE_TYPE_STYLES: Record<string, string> = {
  start: 'border-l-blue-500/50 bg-blue-500/[0.04]',
  normal: 'border-l-border bg-card/30',
  final: 'border-l-emerald-500/50 bg-emerald-500/[0.04]',
}

interface Props {
  projectId: number
  stage: Stage
  tickets: Ticket[]
  allStages: Stage[]
  onCreateTicket: () => void
  onTicketClick: (ticket: Ticket) => void
  /**
   * Optional generation overlay state. Only the start/BACKLOG column should
   * receive this so generated cards stream in there.
   */
  generation?: {
    active: boolean
    visibleTickets: GeneratedTicket[]
    pendingSkeletons: number
  }
}

export function BoardColumn({
  projectId,
  stage,
  tickets,
  allStages,
  onCreateTicket,
  onTicketClick,
  generation,
}: Props) {
  const styleKey = stage.type ?? 'normal'
  const genActive = generation?.active ?? false

  // While generation is active, the store-rendered "preview" tickets cover the
  // ones already saved. Suppress fetched tickets that match a preview id to
  // avoid duplication when react-query catches up mid-stream.
  const previewIds = new Set(generation?.visibleTickets.map((t) => t.id) ?? [])
  const liveTickets = tickets.filter((t) => !previewIds.has(t.id))

  const totalCount = liveTickets.length + (generation?.visibleTickets.length ?? 0)

  return (
    <div
      className={cn(
        'flex h-full w-72 shrink-0 flex-col rounded-lg border border-l-4 border-border',
        STAGE_TYPE_STYLES[styleKey] ?? STAGE_TYPE_STYLES.normal,
      )}
    >
      <div className="flex items-center justify-between gap-2 border-b border-border/60 px-3 py-2">
        <div className="flex items-center gap-2 truncate">
          <h3 className="truncate text-sm font-semibold">{stage.name}</h3>
          <Badge variant="secondary" className="h-5 px-1.5 text-[10px]">
            {totalCount}
          </Badge>
        </div>
        <Button
          variant="ghost"
          size="icon"
          className="h-6 w-6"
          onClick={onCreateTicket}
          aria-label={`Add ticket to ${stage.name}`}
        >
          <Plus className="h-4 w-4" />
        </Button>
      </div>

      <div className="flex-1 space-y-2 overflow-y-auto p-2">
        {/* Generation preview tickets stream in here (one card pops per ~180ms). */}
        {generation?.visibleTickets.map((t, idx) => (
          <PreviewCard key={`preview-${t.id}`} ticket={t} delay={idx} />
        ))}

        {/* Skeleton placeholders for tickets still to come. */}
        {genActive &&
          generation && generation.pendingSkeletons > 0 &&
          Array.from({ length: Math.min(generation.pendingSkeletons, 6) }).map((_, i) => (
            <PendingSkeleton key={`skel-${i}`} index={i} />
          ))}

        {liveTickets.map((t) => (
          <TicketCard
            key={t.id}
            projectId={projectId}
            ticket={t}
            stages={allStages}
            onClick={() => onTicketClick(t)}
          />
        ))}

        {totalCount === 0 && !genActive && (
          <div className="rounded-md border border-dashed border-border/60 p-4 text-center text-xs text-muted-foreground">
            No tickets
          </div>
        )}
      </div>
    </div>
  )
}

function PreviewCard({ ticket, delay }: { ticket: GeneratedTicket; delay: number }) {
  return (
    <div
      className="animate-fade-up rounded-lg border border-accent/40 bg-card p-3 shadow-sm"
      style={{ animationDelay: `${Math.min(delay, 4) * 60}ms` }}
    >
      <div className="flex items-start gap-1.5">
        <Sparkles className="mt-0.5 h-3 w-3 shrink-0 text-accent-foreground" />
        <p className="line-clamp-2 flex-1 text-sm font-medium leading-tight">{ticket.title}</p>
      </div>
      <div className="mt-2 flex items-center justify-between">
        <div className="flex items-center gap-1.5">
          {ticket.category_name && (
            <Badge
              variant="outline"
              className="h-4 px-1 text-[9px]"
              style={
                ticket.category_color
                  ? {
                      borderColor: ticket.category_color,
                      color: ticket.category_color,
                      backgroundColor: `${ticket.category_color}1a`,
                    }
                  : undefined
              }
            >
              {ticket.category_name}
            </Badge>
          )}
          <ComplexityDots value={ticket.complexity} />
        </div>
        <Avatar className="h-5 w-5 opacity-60">
          <AvatarFallback className="text-[8px]">AI</AvatarFallback>
        </Avatar>
      </div>
    </div>
  )
}

function PendingSkeleton({ index }: { index: number }) {
  return (
    <div
      className="animate-pulse rounded-lg border border-border bg-card/60 p-3"
      style={{ animationDelay: `${index * 100}ms` }}
    >
      <Skeleton className="h-3 w-3/4" />
      <div className="mt-2 flex items-center gap-1.5">
        <Skeleton className="h-3 w-10" />
        <Skeleton className="h-3 w-14" />
      </div>
    </div>
  )
}

function ComplexityDots({ value }: { value: number }) {
  return (
    <span className="flex items-center gap-[1px]" title={`Complexity ${value}/5`}>
      {[1, 2, 3, 4, 5].map((i) => (
        <span
          key={i}
          className={cn(
            'h-1 w-1 rounded-full',
            i <= value ? 'bg-foreground/70' : 'bg-foreground/15',
          )}
        />
      ))}
    </span>
  )
}

