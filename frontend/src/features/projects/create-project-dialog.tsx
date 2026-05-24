import { useMutation, useQueryClient } from '@tanstack/react-query'
import { Loader2, Sparkles } from 'lucide-react'
import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { toast } from 'sonner'

import { projectsApi } from '@/api/projects'
import type { TaskGenerationConfig } from '@/api/task-generation'
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
import { Switch } from '@/components/ui/switch'
import { Textarea } from '@/components/ui/textarea'
import { GenerationConfigPanel } from '@/features/projects/generation-config-panel'
import { usePermissions } from '@/hooks/use-permissions'
import { getApiErrorMessage } from '@/lib/utils'
import { useGenerationStore } from '@/store/generation-store'

interface Props {
  open: boolean
  onOpenChange: (open: boolean) => void
}

const DEFAULT_GEN_CONFIG: TaskGenerationConfig = {
  complexity_profile: 'medium',
  total_hours_min: 80,
  total_hours_max: 140,
  task_count: 15,
}

export function CreateProjectDialog({ open, onOpenChange }: Props) {
  const [name, setName] = useState('')
  const [description, setDescription] = useState('')
  const [genEnabled, setGenEnabled] = useState(false)
  const [genConfig, setGenConfig] = useState<TaskGenerationConfig>(DEFAULT_GEN_CONFIG)
  const queryClient = useQueryClient()
  const navigate = useNavigate()
  const { can } = usePermissions()
  const canGenerate = can('simulation:run')
  const scheduleGeneration = useGenerationStore((s) => s.schedule)

  const mutation = useMutation({
    mutationFn: () => projectsApi.create({ name, description: description || undefined }),
    onSuccess: (project) => {
      queryClient.invalidateQueries({ queryKey: ['projects'] })
      toast.success(`Project "${project.name}" created`)
      if (genEnabled && canGenerate) {
        scheduleGeneration({ projectId: project.id, config: genConfig })
      }
      onOpenChange(false)
      setName('')
      setDescription('')
      setGenEnabled(false)
      setGenConfig(DEFAULT_GEN_CONFIG)
      navigate(`/projects/${project.id}/board`)
    },
    onError: (err) => toast.error(getApiErrorMessage(err)),
  })

  const onSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    if (!name.trim()) return
    mutation.mutate()
  }

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-lg">
        <DialogHeader>
          <DialogTitle>Create new project</DialogTitle>
          <DialogDescription>
            We'll set up default stages — Backlog, To Do, In Progress, In Review, Done.
          </DialogDescription>
        </DialogHeader>
        <form onSubmit={onSubmit} className="space-y-4">
          <div className="space-y-2">
            <Label htmlFor="name">Name</Label>
            <Input
              id="name"
              required
              maxLength={255}
              value={name}
              onChange={(e) => setName(e.target.value)}
              placeholder="My team's first board"
              autoFocus
            />
          </div>
          <div className="space-y-2">
            <Label htmlFor="description">Description (optional)</Label>
            <Textarea
              id="description"
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              placeholder="What is this project for?"
              rows={3}
            />
          </div>

          {canGenerate && (
            <div className="space-y-3 rounded-lg border border-border bg-card p-3">
              <div className="flex items-center justify-between">
                <div className="flex items-start gap-2">
                  <Sparkles className="mt-0.5 h-4 w-4 text-accent-foreground" />
                  <div>
                    <Label htmlFor="gen-toggle" className="text-sm font-medium">
                      Generate with AI
                    </Label>
                    <p className="text-xs text-muted-foreground">
                      Auto-fill your backlog with tickets shaped to the project.
                    </p>
                  </div>
                </div>
                <Switch
                  id="gen-toggle"
                  checked={genEnabled}
                  onCheckedChange={setGenEnabled}
                />
              </div>
              {genEnabled && (
                <GenerationConfigPanel value={genConfig} onChange={setGenConfig} />
              )}
            </div>
          )}

          <DialogFooter>
            <Button type="button" variant="outline" onClick={() => onOpenChange(false)}>
              Cancel
            </Button>
            <Button type="submit" disabled={mutation.isPending || !name.trim()}>
              {mutation.isPending && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
              {genEnabled && canGenerate ? 'Create & generate' : 'Create'}
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  )
}
