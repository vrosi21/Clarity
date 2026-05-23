import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { Pencil, Trash2 } from 'lucide-react'
import { useEffect, useState } from 'react'
import { toast } from 'sonner'

import { categoriesApi } from '@/api/categories'
import { ticketsApi, type TicketUpdatePayload } from '@/api/tickets'
import { DurationInput } from '@/components/common/duration-input'
import { SmartSuggestionsPanel } from '@/components/common/smart-suggestions-panel'
import { tagsApi } from '@/api/tags'
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
import { useLlmSuggestions } from '@/hooks/use-llm-suggestions'
import { useRecommenderSettings } from '@/hooks/use-recommender-settings'
import { cn, formatRelative, getApiErrorMessage, getInitials } from '@/lib/utils'
import { PRIORITIES, PRIORITY_LABEL, type Priority, type Stage } from '@/types'
import { useAuthStore } from '@/store/auth-store'

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
  const user = useAuthStore((s) => s.user)
  const canManageCategories = !!user?.org_role?.permissions?.includes('categories:manage')

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
  const [title, setTitle] = useState('')
  const [description, setDescription] = useState('')
  const [editingTitle, setEditingTitle] = useState(false)
  const [editingDesc, setEditingDesc] = useState(false)
  const [panelCategoryIds, setPanelCategoryIds] = useState<number[]>([])
  const [selectedTagNames, setSelectedTagNames] = useState<string[]>([])
  const { settings: recSettings, update: updateRecSettings } = useRecommenderSettings(projectId)

  // Reset edit states when switching to a different ticket.
  useEffect(() => {
    setEditingTitle(false)
    setEditingDesc(false)
  }, [ticketId])

  // Sync from server only when not actively editing that field.
  useEffect(() => {
    if (ticket && !editingTitle) setTitle(ticket.title)
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [ticket?.title, editingTitle])

  useEffect(() => {
    if (ticket && !editingDesc) setDescription(ticket.description ?? '')
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [ticket?.description, editingDesc])

  // Sync panel category selection from server (single category_id → array).
  useEffect(() => {
    if (ticket) setPanelCategoryIds(ticket.category_id ? [ticket.category_id] : [])
  }, [ticket?.category_id])

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

  const saveTitle = () => {
    if (!ticket) return
    if (!title.trim()) { setTitle(ticket.title); setEditingTitle(false); return }
    if (title === ticket.title) { setEditingTitle(false); return }
    updateMutation.mutate({ title }, {
      onSuccess: () => setEditingTitle(false),
    })
  }

  const cancelTitle = () => {
    setTitle(ticket?.title ?? '')
    setEditingTitle(false)
  }

  const saveDesc = () => {
    if (!ticket) return
    if (description === (ticket.description ?? '')) { setEditingDesc(false); return }
    updateMutation.mutate({ description: description || null }, {
      onSuccess: () => setEditingDesc(false),
    })
  }

  const cancelDesc = () => {
    setDescription(ticket?.description ?? '')
    setEditingDesc(false)
  }

  const stage = stages.find((s) => s.id === ticket?.stage_id)

  // Use committed (saved) values — suggestions only recalculate after a save.
  const { suggestData, suggestLoading } = useLlmSuggestions({
    projectId,
    title: ticket?.title ?? '',
    description: ticket?.description ?? '',
    categoryIds: panelCategoryIds,
    complexity: ticket?.complexity ?? null,
    enabled: open,
  })

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
              <SheetTitle className="sr-only">{ticket.title}</SheetTitle>
              {editingTitle ? (
                <div className="flex items-start gap-2">
                  <Input
                    autoFocus
                    value={title}
                    onChange={(e) => setTitle(e.target.value)}
                    onKeyDown={(e) => {
                      if (e.key === 'Enter') saveTitle()
                      if (e.key === 'Escape') cancelTitle()
                    }}
                    className="h-auto border-none p-0 text-xl font-semibold shadow-none focus-visible:ring-0 flex-1"
                  />
                  <Button size="sm" onClick={saveTitle} disabled={updateMutation.isPending}>
                    Save
                  </Button>
                  <Button size="sm" variant="ghost" onClick={cancelTitle}>
                    Cancel
                  </Button>
                </div>
              ) : (
                <div className="group flex items-start gap-1.5">
                  <span className="text-xl font-semibold leading-tight flex-1">{title}</span>
                  <button
                    type="button"
                    onClick={() => setEditingTitle(true)}
                    className="mt-1 shrink-0 rounded p-0.5 text-muted-foreground opacity-0 transition-opacity group-hover:opacity-100 hover:text-foreground"
                    title="Edit title"
                  >
                    <Pencil className="h-3.5 w-3.5" />
                  </button>
                </div>
              )}
              <SheetDescription>
                Created {formatRelative(ticket.created_at)} • Last updated{' '}
                {formatRelative(ticket.updated_at)}
              </SheetDescription>
            </SheetHeader>

            <div className="flex-1 space-y-6 overflow-y-auto py-6 pl-1 pr-2">
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

                <div className="col-span-2 space-y-1.5">
                  <Label className="text-xs uppercase tracking-wide text-muted-foreground">
                    Assignee
                  </Label>
                  <div className="flex items-center gap-2">
                    {ticket.assignee_username ? (
                      <>
                        <Avatar className="h-7 w-7">
                          <AvatarFallback className="text-xs">
                            {getInitials(ticket.assignee_username)}
                          </AvatarFallback>
                        </Avatar>
                        <span className="text-sm">{ticket.assignee_username}</span>
                      </>
                    ) : (
                      <span className="text-sm text-muted-foreground">Unassigned</span>
                    )}
                    <span className="ml-auto text-xs text-muted-foreground">
                      Manage below in Smart suggestions
                    </span>
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
                <div className="flex items-center justify-between">
                  <Label className="text-xs uppercase tracking-wide text-muted-foreground">
                    Description
                  </Label>
                  {!editingDesc && (
                    <button
                      type="button"
                      onClick={() => setEditingDesc(true)}
                      className="flex items-center gap-1 text-xs text-muted-foreground hover:text-foreground"
                    >
                      <Pencil className="h-3 w-3" />
                      Edit
                    </button>
                  )}
                </div>
                {editingDesc ? (
                  <div className="space-y-2">
                    <Textarea
                      autoFocus
                      id="description"
                      rows={6}
                      value={description}
                      onChange={(e) => setDescription(e.target.value)}
                      onKeyDown={(e) => {
                        if (e.key === 'Escape') cancelDesc()
                      }}
                      placeholder="Add details, links, anything that helps."
                    />
                    <div className="flex gap-2">
                      <Button size="sm" onClick={saveDesc} disabled={updateMutation.isPending}>
                        Save
                      </Button>
                      <Button size="sm" variant="ghost" onClick={cancelDesc}>
                        Cancel
                      </Button>
                    </div>
                  </div>
                ) : (
                  <div
                    className="min-h-[40px] cursor-text rounded-md border border-transparent px-1 py-1 text-sm whitespace-pre-wrap hover:border-border"
                    onClick={() => setEditingDesc(true)}
                  >
                    {description || (
                      <span className="text-muted-foreground">No description. Click to add.</span>
                    )}
                  </div>
                )}
              </div>

              <Separator />

              {/* Smart suggestions */}
              <SmartSuggestionsPanel
                suggestData={suggestData}
                suggestLoading={suggestLoading}
                titleNonEmpty={(ticket?.title ?? '').trim().length > 0}
                autoAccept={recSettings.auto_accept}
                threshold={recSettings.threshold}
                onAutoAcceptChange={(v) => updateRecSettings({ auto_accept: v })}
                allCategories={categories ?? []}
                selectedCategoryIds={panelCategoryIds}
                onToggleCategory={(id) => {
                  const next = panelCategoryIds.includes(id)
                    ? panelCategoryIds.filter((x) => x !== id)
                    : [...panelCategoryIds, id]
                  setPanelCategoryIds(next)
                  updateMutation.mutate({ category_id: next[0] ?? null })
                }}
                onResetCategories={(ids) => {
                  setPanelCategoryIds(ids)
                  updateMutation.mutate({ category_id: ids[0] ?? null })
                }}
                selectedStoryPoints={ticket.complexity}
                onSelectStoryPoints={(v) => updateMutation.mutate({ complexity: v })}
                selectedWorkerId={ticket.assignee_id}
                onSelectWorker={(id) => updateMutation.mutate({ assignee_id: id })}
                canManageCategories={canManageCategories}
                onCreateCategory={async (name) => {
                  const cat = await categoriesApi.create(name)
                  queryClient.invalidateQueries({ queryKey: ['categories'] })
                  updateMutation.mutate({ category_id: cat.id })
                  toast.success(`Category "${cat.name}" created`)
                }}
                selectedTagNames={selectedTagNames}
                onTagAccept={(name) =>
                  setSelectedTagNames((p) => p.includes(name) ? p : [...p, name])
                }
                onTagReject={(name) =>
                  setSelectedTagNames((p) => p.filter((t) => t !== name))
                }
                onNewTagConfirm={async (name) => {
                  try {
                    await tagsApi.create(name)
                    setSelectedTagNames((p) => p.includes(name) ? p : [...p, name])
                    toast.success(`Tag "${name}" created`)
                  } catch (e: any) {
                    toast.error(e?.response?.data?.detail ?? 'Failed to create tag')
                  }
                }}
              />

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
