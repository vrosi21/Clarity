import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { Trash2 } from 'lucide-react'
import { useEffect, useState } from 'react'
import { toast } from 'sonner'

import { categoriesApi } from '@/api/categories'
import { membersApi } from '@/api/members'
import { ticketsApi, type TicketUpdatePayload } from '@/api/tickets'
import { DurationInput } from '@/components/common/duration-input'
import { Avatar, AvatarFallback } from '@/components/ui/avatar'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'
import {
  Sheet,
  SheetContent,
  SheetDescription,
  SheetHeader,
  SheetTitle,
} from '@/components/ui/sheet'
import { Separator } from '@/components/ui/separator'
import { Skeleton } from '@/components/ui/skeleton'
import { Textarea } from '@/components/ui/textarea'
import { CommentThread } from '@/features/ticket/comment-thread'
import { cn, formatRelative, getApiErrorMessage, getInitials } from '@/lib/utils'
import { PRIORITIES, PRIORITY_LABEL, type Priority, type Stage } from '@/types'

const PRIORITY_BADGE: Record<Priority, string> = {
  p1: 'border-red-500/40 bg-red-500/10 text-red-700 dark:text-red-300',
  p2: 'border-orange-500/40 bg-orange-500/10 text-orange-700 dark:text-orange-300',
  p3: 'border-yellow-500/40 bg-yellow-500/10 text-yellow-700 dark:text-yellow-300',
  p4: 'border-blue-500/40 bg-blue-500/10 text-blue-700 dark:text-blue-300',
  p5: 'border-zinc-500/30 bg-zinc-500/10 text-zinc-600 dark:text-zinc-400',
}

interface Props {
  projectId: number
  ticketId: number | null
  stages: Stage[]
  onOpenChange: (open: boolean) => void
}

export function TicketSheet({ projectId, ticketId, stages, onOpenChange }: Props) {
  const open = ticketId !== null
  const queryClient = useQueryClient()

  const { data: ticket, isPending } = useQuery({
    queryKey: ['ticket', ticketId],
    queryFn: () => ticketsApi.get(projectId, ticketId!),
    enabled: ticketId !== null,
  })
  const { data: categories } = useQuery({
    queryKey: ['categories'],
    queryFn: categoriesApi.list,
    staleTime: 60_000 * 60,
  })
  const { data: members } = useQuery({
    queryKey: ['members', projectId],
    queryFn: () => membersApi.list(projectId),
  })

  const [title, setTitle] = useState('')
  const [description, setDescription] = useState('')

  useEffect(() => {
    if (ticket) {
      setTitle(ticket.title)
      setDescription(ticket.description ?? '')
    }
  }, [ticket])

  const updateMutation = useMutation({
    mutationFn: (payload: TicketUpdatePayload) =>
      ticketsApi.update(projectId, ticketId!, payload),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['ticket', ticketId] })
      queryClient.invalidateQueries({ queryKey: ['tickets', projectId] })
    },
    onError: (err) => toast.error(getApiErrorMessage(err)),
  })

  const deleteMutation = useMutation({
    mutationFn: () => ticketsApi.remove(projectId, ticketId!),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['tickets', projectId] })
      toast.success('Ticket deleted')
      onOpenChange(false)
    },
    onError: (err) => toast.error(getApiErrorMessage(err)),
  })

  const handleTitleBlur = () => {
    if (!ticket || title === ticket.title) return
    if (!title.trim()) {
      setTitle(ticket.title)
      return
    }
    updateMutation.mutate({ title })
  }

  const handleDescriptionBlur = () => {
    if (!ticket || description === (ticket.description ?? '')) return
    updateMutation.mutate({ description: description || null })
  }

  const stage = stages.find((s) => s.id === ticket?.stage_id)

  return (
    <Sheet open={open} onOpenChange={onOpenChange}>
      <SheetContent>
        {isPending && (
          <div className="space-y-4">
            <Skeleton className="h-7 w-2/3" />
            <Skeleton className="h-4 w-1/3" />
            <Skeleton className="h-32 w-full" />
          </div>
        )}

        {ticket && (
          <div className="flex h-full flex-col">
            <SheetHeader className="space-y-1">
              <Input
                value={title}
                onChange={(e) => setTitle(e.target.value)}
                onBlur={handleTitleBlur}
                className="h-auto border-none p-0 text-xl font-semibold shadow-none focus-visible:ring-0"
              />
              <SheetTitle className="sr-only">{ticket.title}</SheetTitle>
              <SheetDescription>
                Created {formatRelative(ticket.created_at)} • Last updated{' '}
                {formatRelative(ticket.updated_at)}
              </SheetDescription>
            </SheetHeader>

            <div className="flex-1 space-y-6 overflow-y-auto py-6 pr-2">
              {/* Metadata grid */}
              <div className="grid grid-cols-2 gap-4">
                <div className="space-y-1.5">
                  <Label className="text-xs uppercase tracking-wide text-muted-foreground">
                    Stage
                  </Label>
                  <Select
                    value={String(ticket.stage_id)}
                    onValueChange={(v) =>
                      ticketsApi
                        .move(projectId, ticket.id, Number(v))
                        .then(() => {
                          queryClient.invalidateQueries({ queryKey: ['tickets', projectId] })
                          queryClient.invalidateQueries({ queryKey: ['ticket', ticket.id] })
                          toast.success('Ticket moved')
                        })
                        .catch((err) => toast.error(getApiErrorMessage(err)))
                    }
                  >
                    <SelectTrigger>
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                      {stages.map((s) => (
                        <SelectItem key={s.id} value={String(s.id)}>
                          {s.name}
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                </div>

                <div className="space-y-1.5">
                  <Label className="text-xs uppercase tracking-wide text-muted-foreground">
                    Priority
                  </Label>
                  <Select
                    value={ticket.priority}
                    onValueChange={(v) => updateMutation.mutate({ priority: v as Priority })}
                  >
                    <SelectTrigger>
                      <SelectValue>
                        <Badge
                          variant="outline"
                          className={cn('text-xs', PRIORITY_BADGE[ticket.priority])}
                        >
                          {PRIORITY_LABEL[ticket.priority]}
                        </Badge>
                      </SelectValue>
                    </SelectTrigger>
                    <SelectContent>
                      {PRIORITIES.map((p) => (
                        <SelectItem key={p} value={p}>
                          {PRIORITY_LABEL[p]}
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                </div>

                <div className="space-y-1.5">
                  <Label className="text-xs uppercase tracking-wide text-muted-foreground">
                    Complexity
                  </Label>
                  <Select
                    value={String(ticket.complexity)}
                    onValueChange={(v) => updateMutation.mutate({ complexity: Number(v) })}
                  >
                    <SelectTrigger>
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                      {[1, 2, 3, 4, 5].map((c) => (
                        <SelectItem key={c} value={String(c)}>
                          {c} / 5
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                </div>

                <div className="space-y-1.5">
                  <Label className="text-xs uppercase tracking-wide text-muted-foreground">
                    Category
                  </Label>
                  <Select
                    value={ticket.category_id ? String(ticket.category_id) : 'none'}
                    onValueChange={(v) =>
                      updateMutation.mutate({
                        category_id: v === 'none' ? null : Number(v),
                      })
                    }
                  >
                    <SelectTrigger>
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="none">No category</SelectItem>
                      {categories?.map((c) => (
                        <SelectItem key={c.id} value={String(c.id)}>
                          {c.name}
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                </div>

                <div className="col-span-2 space-y-1.5">
                  <Label className="text-xs uppercase tracking-wide text-muted-foreground">
                    Assignee
                  </Label>
                  <div className="flex items-center gap-2">
                    {ticket.assignee_username && (
                      <Avatar className="h-7 w-7">
                        <AvatarFallback className="text-xs">
                          {getInitials(ticket.assignee_username)}
                        </AvatarFallback>
                      </Avatar>
                    )}
                    <Select
                      value={ticket.assignee_id ? String(ticket.assignee_id) : 'none'}
                      onValueChange={(v) =>
                        updateMutation.mutate({
                          assignee_id: v === 'none' ? null : Number(v),
                        })
                      }
                    >
                      <SelectTrigger className="flex-1">
                        <SelectValue />
                      </SelectTrigger>
                      <SelectContent>
                        <SelectItem value="none">Unassigned</SelectItem>
                        {members?.map((m) => (
                          <SelectItem key={m.user_id} value={String(m.user_id)}>
                            {m.username}
                          </SelectItem>
                        ))}
                      </SelectContent>
                    </Select>
                  </div>
                </div>

                <div className="col-span-2 space-y-1.5">
                  <Label
                    className="text-xs uppercase tracking-wide text-muted-foreground"
                    htmlFor="estimated"
                  >
                    Estimate
                  </Label>
                  <DurationInput
                    id="estimated"
                    value={ticket.estimated_minutes}
                    onChange={(val) => {
                      if (val !== ticket.estimated_minutes) {
                        updateMutation.mutate({ estimated_minutes: val })
                      }
                    }}
                  />
                </div>
              </div>

              <Separator />

              {/* Description */}
              <div className="space-y-2">
                <Label
                  className="text-xs uppercase tracking-wide text-muted-foreground"
                  htmlFor="description"
                >
                  Description
                </Label>
                <Textarea
                  id="description"
                  rows={6}
                  value={description}
                  onChange={(e) => setDescription(e.target.value)}
                  onBlur={handleDescriptionBlur}
                  placeholder="Add details, links, anything that helps."
                />
              </div>

              <Separator />

              {/* Comments */}
              <CommentThread ticketId={ticket.id} />
            </div>

            <div className="flex items-center justify-between border-t border-border pt-4">
              <span className="text-xs text-muted-foreground">
                {stage ? `In ${stage.name}` : ''}
              </span>
              <Button
                variant="ghost"
                size="sm"
                className="text-destructive hover:bg-destructive/10 hover:text-destructive"
                onClick={() => {
                  if (confirm('Delete this ticket?')) deleteMutation.mutate()
                }}
                disabled={deleteMutation.isPending}
              >
                <Trash2 className="h-4 w-4" />
                Delete
              </Button>
            </div>
          </div>
        )}
      </SheetContent>
    </Sheet>
  )
}
