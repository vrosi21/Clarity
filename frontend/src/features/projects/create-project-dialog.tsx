import { useMutation, useQueryClient } from '@tanstack/react-query'
import { Loader2, Sparkles } from 'lucide-react'
import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { toast } from 'sonner'

import { projectsApi } from '@/api/projects'
import { streamGenerateTasks, type TaskGenerationConfig } from '@/api/task-generation'
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

// Defaults match Tasks=15 + Complexity=3 (Medium) in GenerationConfigPanel.
const DEFAULT_GEN_CONFIG: TaskGenerationConfig = {
  complexity_profile: 'medium',
  total_hours_min: 150,
  total_hours_max: 210,
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
  const startGen = useGenerationStore((s) => s.start)
  const setDiffusion = useGenerationStore((s) => s.setDiffusion)
  const appendBatch = useGenerationStore((s) => s.appendBatch)
  const finishGen = useGenerationStore((s) => s.finish)
  const failGen = useGenerationStore((s) => s.fail)

  const mutation = useMutation({
    mutationFn: () => projectsApi.create({ name, description: description || undefined }),
    onSuccess: (project) => {
      queryClient.invalidateQueries({ queryKey: ['projects'] })
      toast.success(`Project "${project.name}" created`)

      console.log('[create-project] success', {
        projectId: project.id,
        genEnabled,
        canGenerate,
        config: genConfig,
      })
      if (genEnabled && canGenerate) {
        console.log('[create-project] launching streamGenerateTasks', project.id)
        // Kick the stream off here (NOT in a useEffect) so React strict-mode
        // double-mount can't abort the fetch before it leaves the browser.
        startGen(project.id, genConfig.task_count)
        streamGenerateTasks(
          project.id,
          genConfig,
          {
            onDiffusion: (plan) => setDiffusion(plan),
            // Don't invalidate per batch — the BoardPage reveal pump drains
            // tickets from the store at a controlled cadence (one per ~180ms).
            // It invalidates the tickets query only after the final reveal so
            // server-fetched cards replace the preview cards in one swap.
            onBatch: (_i, tickets) => appendBatch(tickets),
            onDone: () => finishGen(),
            onError: (msg) => failGen(msg),
          },
        ).catch((e) => failGen(String(e?.message ?? e)))
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
            <div className="rounded-lg border border-border bg-card/50 p-3">
              <div className="flex items-center justify-between">
                <Label htmlFor="gen-toggle" className="flex items-center gap-2 text-sm font-medium">
                  <Sparkles className="h-4 w-4 text-accent-foreground" />
                  Generate tickets with AI
                </Label>
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
