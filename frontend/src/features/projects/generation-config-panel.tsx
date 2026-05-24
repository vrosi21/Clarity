import { Label } from '@/components/ui/label'
import { Slider } from '@/components/ui/slider'
import { cn } from '@/lib/utils'
import type { ComplexityProfile, TaskGenerationConfig } from '@/api/task-generation'

interface Props {
  value: TaskGenerationConfig
  onChange: (next: TaskGenerationConfig) => void
}

const TASK_STOPS = [5, 10, 15, 20, 25, 30]
const COMPLEXITY_STOPS = [1, 2, 3, 4, 5] as const
const COMPLEXITY_LABEL: Record<number, string> = {
  1: 'Trivial',
  2: 'Light',
  3: 'Medium',
  4: 'Heavy',
  5: 'Hardcore',
}

/** complexity 1–5 → profile + per-task hour range. */
function complexityToProfile(c: number): {
  profile: ComplexityProfile
  hoursPerTaskMin: number
  hoursPerTaskMax: number
} {
  if (c <= 2) return { profile: 'simple', hoursPerTaskMin: 4 + (c - 1) * 2, hoursPerTaskMax: 6 + (c - 1) * 4 }
  if (c === 3) return { profile: 'medium', hoursPerTaskMin: 10, hoursPerTaskMax: 14 }
  return { profile: 'complex', hoursPerTaskMin: 12 + (c - 4) * 6, hoursPerTaskMax: 18 + (c - 4) * 10 }
}

function deriveConfig(taskCount: number, complexity: number): TaskGenerationConfig {
  const { profile, hoursPerTaskMin, hoursPerTaskMax } = complexityToProfile(complexity)
  return {
    complexity_profile: profile,
    total_hours_min: Math.round(taskCount * hoursPerTaskMin),
    total_hours_max: Math.round(taskCount * hoursPerTaskMax),
    task_count: taskCount,
  }
}

function inferComplexity(cfg: TaskGenerationConfig): number {
  // Best-effort reverse from saved config.
  const avg = (cfg.total_hours_min + cfg.total_hours_max) / 2 / Math.max(cfg.task_count, 1)
  if (avg <= 6) return 1
  if (avg <= 9) return 2
  if (avg <= 13) return 3
  if (avg <= 19) return 4
  return 5
}

export function GenerationConfigPanel({ value, onChange }: Props) {
  const taskCount = value.task_count
  const complexity = inferComplexity(value)

  const setTaskCount = (n: number) => onChange(deriveConfig(n, complexity))
  const setComplexity = (c: number) => onChange(deriveConfig(taskCount, c))

  return (
    <div className="space-y-4 border-t border-border/60 pt-3">
      <StopSlider
        label="Number of tickets"
        value={taskCount}
        stops={TASK_STOPS}
        onChange={setTaskCount}
        format={(v) => `${v} tickets`}
      />
      <StopSlider
        label="Complexity"
        value={complexity}
        stops={[1, 2, 3, 4, 5]}
        onChange={setComplexity}
        format={(v) => COMPLEXITY_LABEL[v] ?? String(v)}
      />
      <p className="text-[10px] text-muted-foreground">
        Higher complexity → larger tickets, more story points on average.
      </p>
    </div>
  )
}

interface StopSliderProps {
  label: string
  value: number
  stops: readonly number[]
  onChange: (v: number) => void
  format: (v: number) => string
}

function StopSlider({ label, value, stops, onChange, format }: StopSliderProps) {
  return (
    <div className="space-y-2">
      <div className="flex items-center justify-between">
        <Label className="text-xs">{label}</Label>
        <span className="font-mono text-[10px] text-muted-foreground">{format(value)}</span>
      </div>
      <Slider
        min={0}
        max={stops.length - 1}
        step={1}
        value={stops.indexOf(value) >= 0 ? stops.indexOf(value) : 0}
        onChange={(idx) => onChange(stops[idx])}
        aria-label={label}
      />
      <div className="flex justify-between px-0.5 text-[9px] text-muted-foreground">
        {stops.map((s) => (
          <span
            key={s}
            className={cn(
              'tabular-nums',
              s === value ? 'font-semibold text-foreground' : '',
            )}
          >
            {s}
          </span>
        ))}
      </div>
    </div>
  )
}
