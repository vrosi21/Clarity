import { Plus } from 'lucide-react'

import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { TicketCard } from '@/features/board/ticket-card'
import { cn } from '@/lib/utils'
import type { Stage, Ticket } from '@/types'

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
}

export function BoardColumn({ projectId, stage, tickets, allStages, onCreateTicket, onTicketClick }: Props) {
  const styleKey = stage.type ?? 'normal'

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
            {tickets.length}
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
        {tickets.length === 0 && (
          <div className="rounded-md border border-dashed border-border/60 p-4 text-center text-xs text-muted-foreground">
            No tickets
          </div>
        )}
        {tickets.map((t) => (
          <TicketCard
            key={t.id}
            projectId={projectId}
            ticket={t}
            stages={allStages}
            onClick={() => onTicketClick(t)}
          />
        ))}
      </div>
    </div>
  )
}
