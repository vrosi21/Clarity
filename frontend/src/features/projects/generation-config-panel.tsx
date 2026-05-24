import { Sparkles } from 'lucide-react'

import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { cn } from '@/lib/utils'
import type { ComplexityProfile, TaskGenerationConfig } from '@/api/task-generation'

interface Props {
  value: TaskGenerationConfig
  onChange: (next: TaskGenerationConfig) => void
}

const PROFILE_LABELS: Record<ComplexityProfile, string> = {
  simple: 'Simple',
  medium: 'Medium',
  complex: 'Complex',
}
const PROFILE_BLURB: Record<ComplexityProfile, string> = {
  simple: 'Small project, mostly 1–2 point tickets.',
  medium: 'Balanced mix, 2–3 point tickets dominate.',
  complex: 'Larger system, plenty of 3–5 point work.',
}

export function GenerationConfigPanel({ value, onChange }: Props) {
  const setProfile = (p: ComplexityProfile) => onChange({ ...value, complexity_profile: p })
  const setMin = (n: number) =>
    onChange({ ...value, total_hours_min: Math.min(n, value.total_hours_max - 10) })
  const setMax = (n: number) =>
    onChange({ ...value, total_hours_max: Math.max(n, value.total_hours_min + 10) })
  const setTaskCount = (n: number) =>
    onChange({ ...value, task_count: Math.max(5, Math.min(50, n)) })

  return (
    <div className="space-y-4 rounded-lg border border-accent/30 bg-accent/5 p-4">
      <div className="flex items-center gap-2 text-sm font-medium">
        <Sparkles className="h-4 w-4 text-accent-foreground" />
        Generation settings
      </div>

      <div className="space-y-2">
        <Label>Complexity profile</Label>
        <div className="grid grid-cols-3 gap-2">
          {(['simple', 'medium', 'complex'] as ComplexityProfile[]).map((p) => (
            <Button
              key={p}
              type="button"
              variant={value.complexity_profile === p ? 'default' : 'outline'}
              size="sm"
              onClick={() => setProfile(p)}
              className={cn(
                'h-auto flex-col items-start py-2 px-3 text-left',
              )}
            >
              <span className="text-sm font-medium">{PROFILE_LABELS[p]}</span>
              <span className="text-[10px] font-normal opacity-70">
                {PROFILE_BLURB[p]}
              </span>
            </Button>
          ))}
        </div>
      </div>

      <div className="space-y-2">
        <div className="flex items-center justify-between">
          <Label>Estimated total hours</Label>
          <span className="text-sm tabular-nums text-muted-foreground">
            {value.total_hours_min} – {value.total_hours_max} hours
          </span>
        </div>
        <div className="grid grid-cols-2 gap-3">
          <div>
            <Label className="text-xs text-muted-foreground">Min</Label>
            <input
              type="range"
              min={20}
              max={500}
              step={10}
              value={value.total_hours_min}
              onChange={(e) => setMin(Number(e.target.value))}
              className="w-full accent-primary"
            />
          </div>
          <div>
            <Label className="text-xs text-muted-foreground">Max</Label>
            <input
              type="range"
              min={20}
              max={500}
              step={10}
              value={value.total_hours_max}
              onChange={(e) => setMax(Number(e.target.value))}
              className="w-full accent-primary"
            />
          </div>
        </div>
      </div>

      <div className="space-y-2">
        <Label htmlFor="task_count">Number of tasks</Label>
        <Input
          id="task_count"
          type="number"
          min={5}
          max={50}
          value={value.task_count}
          onChange={(e) => setTaskCount(Number(e.target.value))}
        />
      </div>
    </div>
  )
}
