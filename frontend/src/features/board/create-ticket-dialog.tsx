import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { Loader2 } from 'lucide-react'
import { useState } from 'react'
import { toast } from 'sonner'

import { categoriesApi } from '@/api/categories'
import { ticketsApi } from '@/api/tickets'
import { SmartSuggestionsPanel } from '@/components/common/smart-suggestions-panel'
import { Button } from '@/components/ui/button'
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'
import { Textarea } from '@/components/ui/textarea'
import { DurationInput } from '@/components/common/duration-input'
import { useRecommenderSettings } from '@/hooks/use-recommender-settings'
import { useLlmSuggestions } from '@/hooks/use-llm-suggestions'
import { tagsApi } from '@/api/tags'
import { getApiErrorMessage } from '@/lib/utils'
import { PRIORITIES, PRIORITY_LABEL, type Priority } from '@/types'
import { useAuthStore } from '@/store/auth-store'

interface Props {
  open: boolean
  onOpenChange: (open: boolean) => void
  projectId: number
  defaultStageId: number
}

export function CreateTicketDialog({ open, onOpenChange, projectId, defaultStageId }: Props) {
  const [title, setTitle] = useState('')
  const [description, setDescription] = useState('')
  const [priority, setPriority] = useState<Priority>('p3')
  const [storyPoints, setStoryPoints] = useState(3)
  const [estimated, setEstimated] = useState<number | null>(null)
  const [categoryId, setCategoryId] = useState<string>('none')
  const [panelCategoryIds, setPanelCategoryIds] = useState<number[]>([])
  const [assigneeId, setAssigneeId] = useState<string>('none')
  const [selectedTagNames, setSelectedTagNames] = useState<string[]>([])
  const { settings: recSettings, update: updateRecSettings } = useRecommenderSettings(projectId)
  const queryClient = useQueryClient()
  const user = useAuthStore((s) => s.user)
  const canManageCategories = !!user?.org_role?.permissions?.includes('categories:manage')

  const { data: categories } = useQuery({
    queryKey: ['categories'],
    queryFn: categoriesApi.list,
    staleTime: 60_000 * 60,
  })

  const { suggestData, suggestLoading } = useLlmSuggestions({
    projectId,
    title,
    description,
    categoryIds: panelCategoryIds,
    complexity: storyPoints,
    enabled: open,
  })

  const reset = () => {
    setTitle('')
    setDescription('')
    setPriority('p3')
    setStoryPoints(3)
    setEstimated(null)
    setCategoryId('none')
    setPanelCategoryIds([])
    setAssigneeId('none')
    setSelectedTagNames([])
  }

  const handleToggleCategory = (id: number) => {
    setPanelCategoryIds((prev) => {
      if (prev.includes(id)) {
        const next = prev.filter((x) => x !== id)
        if (prev[0] === id) setCategoryId(next.length > 0 ? String(next[0]) : 'none')
        return next
      } else {
        if (prev.length === 0) setCategoryId(String(id))
        return [...prev, id]
      }
    })
  }

  const handleSelectStoryPoints = (v: number) => setStoryPoints(v)

  const handleCreateCategory = async (name: string) => {
    const cat = await categoriesApi.create(name)
    queryClient.invalidateQueries({ queryKey: ['categories'] })
    setPanelCategoryIds((prev) => {
      if (prev.length === 0) setCategoryId(String(cat.id))
      return prev.includes(cat.id) ? prev : [...prev, cat.id]
    })
    toast.success(`Category "${cat.name}" created`)
  }

  const handleSelectWorker = (id: number | null) =>
    setAssigneeId(id === null ? 'none' : String(id))

  const mutation = useMutation({
    mutationFn: () =>
      ticketsApi.create(projectId, {
        title,
        description: description || undefined,
        priority,
        complexity: storyPoints,
        stage_id: defaultStageId,
        category_id: categoryId === 'none' ? null : Number(categoryId),
        assignee_id: assigneeId === 'none' ? null : Number(assigneeId),
        estimated_minutes: estimated,
      }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['tickets', projectId] })
      toast.success('Ticket created')
      reset()
      onOpenChange(false)
    },
    onError: (err) => toast.error(getApiErrorMessage(err)),
  })

  const onSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    if (!title.trim()) return
    mutation.mutate()
  }

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-2xl">
        <DialogHeader>
          <DialogTitle>New ticket</DialogTitle>
          <DialogDescription>Describe the work; assign it later if you'd like.</DialogDescription>
        </DialogHeader>
        <form onSubmit={onSubmit} className="space-y-4">
          <div className="space-y-2">
            <Label htmlFor="title">Title</Label>
            <Input
              id="title"
              required
              maxLength={255}
              value={title}
              onChange={(e) => setTitle(e.target.value)}
              autoFocus
              placeholder="What needs to happen?"
            />
          </div>
          <div className="space-y-2">
            <Label htmlFor="description">Description</Label>
            <Textarea
              id="description"
              rows={4}
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              placeholder="Add details, links, anything that helps."
            />
          </div>

          <SmartSuggestionsPanel
            suggestData={suggestData}
            suggestLoading={suggestLoading}
            titleNonEmpty={title.trim().length > 0}
            autoAccept={recSettings.auto_accept}
            threshold={recSettings.threshold}
            onAutoAcceptChange={(v) => updateRecSettings({ auto_accept: v })}
            allCategories={categories ?? []}
            selectedCategoryIds={panelCategoryIds}
            onToggleCategory={handleToggleCategory}
            onResetCategories={(ids) => {
              setPanelCategoryIds(ids)
              setCategoryId(ids.length > 0 ? String(ids[0]) : 'none')
            }}
            selectedStoryPoints={storyPoints}
            onSelectStoryPoints={handleSelectStoryPoints}
            selectedWorkerId={assigneeId === 'none' ? null : Number(assigneeId)}
            onSelectWorker={handleSelectWorker}
            canManageCategories={canManageCategories}
            onCreateCategory={handleCreateCategory}
            selectedTagNames={selectedTagNames}
            onTagAccept={(name) =>
              setSelectedTagNames((prev) => prev.includes(name) ? prev : [...prev, name])
            }
            onTagReject={(name) =>
              setSelectedTagNames((prev) => prev.filter((t) => t !== name))
            }
            onNewTagConfirm={async (name) => {
              try {
                await tagsApi.create(name)
                setSelectedTagNames((prev) => prev.includes(name) ? prev : [...prev, name])
                toast.success(`Tag "${name}" created`)
              } catch (e: any) {
                toast.error(e?.response?.data?.detail ?? 'Failed to create tag')
              }
            }}
          />

          <div className="grid grid-cols-2 gap-4">
            <div className="space-y-2">
              <Label>Priority</Label>
              <Select value={priority} onValueChange={(v) => setPriority(v as Priority)}>
                <SelectTrigger>
                  <SelectValue />
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
            <div className="space-y-2">
              <Label htmlFor="estimated">Estimate (optional)</Label>
              <DurationInput
                id="estimated"
                value={estimated}
                onChange={setEstimated}
              />
            </div>
          </div>

          <DialogFooter>
            <Button type="button" variant="outline" onClick={() => onOpenChange(false)}>
              Cancel
            </Button>
            <Button type="submit" disabled={mutation.isPending || !title.trim()}>
              {mutation.isPending && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
              Create ticket
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  )
}
