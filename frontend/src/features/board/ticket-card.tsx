import { useMutation, useQueryClient } from '@tanstack/react-query'
import { ArrowRight, MoreHorizontal } from 'lucide-react'
import { toast } from 'sonner'

import { ticketsApi } from '@/api/tickets'
import { Avatar, AvatarFallback } from '@/components/ui/avatar'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu'
import { cn, getApiErrorMessage, getInitials } from '@/lib/utils'
import type { Stage, Ticket } from '@/types'

const PRIORITY_STYLES: Record<string, string> = {
  p1: 'border-red-500/40 bg-red-500/10 text-red-700 dark:text-red-300',
  p2: 'border-orange-500/40 bg-orange-500/10 text-orange-700 dark:text-orange-300',
  p3: 'border-yellow-500/40 bg-yellow-500/10 text-yellow-700 dark:text-yellow-300',
  p4: 'border-blue-500/40 bg-blue-500/10 text-blue-700 dark:text-blue-300',
  p5: 'border-zinc-500/30 bg-zinc-500/10 text-zinc-600 dark:text-zinc-400',
}
const PRIORITY_LABEL: Record<string, string> = { p1: 'P1', p2: 'P2', p3: 'P3', p4: 'P4', p5: 'P5' }

function ComplexityDots({ value }: { value: number }) {
  return (
    <div className="flex items-center gap-0.5" title={`Complexity ${value}/5`}>
      {[1, 2, 3, 4, 5].map((i) => (
        <span
          key={i}
          className={cn(
            'h-1.5 w-1.5 rounded-full',
            i <= value ? 'bg-foreground/70' : 'bg-foreground/15',
          )}
        />
      ))}
    </div>
  )
}

interface Props {
  projectId: number
  ticket: Ticket
  stages: Stage[]
  onClick: () => void
}

export function TicketCard({ projectId, ticket, stages, onClick }: Props) {
  const queryClient = useQueryClient()

  const moveMutation = useMutation({
    mutationFn: (stageId: number) => ticketsApi.move(projectId, ticket.id, stageId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['tickets', projectId] })
      toast.success('Ticket moved')
    },
    onError: (err) => toast.error(getApiErrorMessage(err)),
  })

  const otherStages = stages.filter((s) => s.id !== ticket.stage_id)

  return (
    <div
      onClick={onClick}
      className="group cursor-pointer rounded-lg border border-border bg-card p-3 shadow-sm transition-colors hover:border-accent/40 hover:bg-accent/5"
    >
      <div className="flex items-start justify-between gap-2">
        <p className="line-clamp-2 flex-1 text-sm font-medium leading-tight">{ticket.title}</p>
        <DropdownMenu>
          <DropdownMenuTrigger asChild>
            <Button
              variant="ghost"
              size="icon"
              className="-mr-1 h-7 w-7 opacity-0 transition-opacity group-hover:opacity-100 data-[state=open]:opacity-100"
              onClick={(e) => e.stopPropagation()}
              aria-label="Ticket actions"
            >
              <MoreHorizontal className="h-4 w-4" />
            </Button>
          </DropdownMenuTrigger>
          <DropdownMenuContent align="end" className="w-48" onClick={(e) => e.stopPropagation()}>
            <DropdownMenuLabel>Move to...</DropdownMenuLabel>
            <DropdownMenuSeparator />
            {otherStages.length === 0 && (
              <DropdownMenuItem disabled>No other stages</DropdownMenuItem>
            )}
            {otherStages.map((s) => (
              <DropdownMenuItem
                key={s.id}
                onSelect={() => moveMutation.mutate(s.id)}
                disabled={moveMutation.isPending}
              >
                <ArrowRight className="h-4 w-4" />
                {s.name}
              </DropdownMenuItem>
            ))}
          </DropdownMenuContent>
        </DropdownMenu>
      </div>

      {ticket.description && (
        <p className="mt-1 line-clamp-2 text-xs text-muted-foreground">{ticket.description}</p>
      )}

      <div className="mt-3 flex flex-wrap items-center gap-1.5">
        <Badge variant="outline" className={cn('text-xs', PRIORITY_STYLES[ticket.priority])}>
          {PRIORITY_LABEL[ticket.priority]}
        </Badge>
        {ticket.category_name && (
          <Badge
            variant="outline"
            className="gap-1 text-xs"
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
            <span
              className="h-1.5 w-1.5 rounded-full"
              style={{ backgroundColor: ticket.category_color ?? 'currentColor' }}
            />
            {ticket.category_name}
          </Badge>
        )}
      </div>

      <div className="mt-3 flex items-center justify-between">
        <ComplexityDots value={ticket.complexity} />
        {ticket.assignee_username ? (
          <Avatar className="h-6 w-6">
            <AvatarFallback className="text-[10px]">
              {getInitials(ticket.assignee_username)}
            </AvatarFallback>
          </Avatar>
        ) : (
          <span className="text-xs text-muted-foreground">Unassigned</span>
        )}
      </div>
    </div>
  )
}
