import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { Loader2 } from 'lucide-react'
import { useState } from 'react'
import { toast } from 'sonner'

import { categoriesApi } from '@/api/categories'
import { membersApi } from '@/api/members'
import { ticketsApi } from '@/api/tickets'
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
import { getApiErrorMessage } from '@/lib/utils'
import { PRIORITIES, PRIORITY_LABEL, type Priority } from '@/types'

const COMPLEXITY_OPTIONS = [1, 2, 3, 4, 5] as const

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
  const [complexity, setComplexity] = useState(3)
  const [estimated, setEstimated] = useState<number | null>(null)
  const [categoryId, setCategoryId] = useState<string>('none')
  const [assigneeId, setAssigneeId] = useState<string>('none')
  const queryClient = useQueryClient()

  const { data: categories } = useQuery({
    queryKey: ['categories'],
    queryFn: categoriesApi.list,
    staleTime: 60_000 * 60,
  })
  const { data: members } = useQuery({
    queryKey: ['members', projectId],
    queryFn: () => membersApi.list(projectId),
  })

  const reset = () => {
    setTitle('')
    setDescription('')
    setPriority('p3')
    setComplexity(3)
    setEstimated(null)
    setCategoryId('none')
    setAssigneeId('none')
  }

  const mutation = useMutation({
    mutationFn: () =>
      ticketsApi.create(projectId, {
        title,
        description: description || undefined,
        priority,
        complexity,
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
              <Label>Complexity</Label>
              <Select value={String(complexity)} onValueChange={(v) => setComplexity(Number(v))}>
                <SelectTrigger>
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  {COMPLEXITY_OPTIONS.map((c) => (
                    <SelectItem key={c} value={String(c)}>
                      {c} / 5
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
          </div>

          <div className="grid grid-cols-2 gap-4">
            <div className="space-y-2">
              <Label htmlFor="estimated">Estimate (optional)</Label>
              <DurationInput
                id="estimated"
                value={estimated}
                onChange={setEstimated}
              />
            </div>
            <div className="space-y-2">
              <Label>Category</Label>
              <Select value={categoryId} onValueChange={setCategoryId}>
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
          </div>

          <div className="space-y-2">
            <Label>Assignee</Label>
            <Select value={assigneeId} onValueChange={setAssigneeId}>
              <SelectTrigger>
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

          <DialogFooter>
            <Button type="button" variant="outline" onClick={() => onOpenChange(false)}>
              Cancel
            </Button>
            <Button type="submit" disabled={mutation.isPending || !title.trim()}>
              {mutation.isPending && <Loader2 className="h-4 w-4 animate-spin" />}
              Create ticket
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  )
}
