import { useMutation, useQueryClient } from '@tanstack/react-query'
import { useState } from 'react'
import { toast } from 'sonner'

import { simulationApi } from '@/api/simulation'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import {
  Sheet,
  SheetContent,
  SheetDescription,
  SheetHeader,
  SheetTitle,
} from '@/components/ui/sheet'
import { Slider } from '@/components/ui/slider'
import { getApiErrorMessage } from '@/lib/utils'
import type {
  Category,
  SyntheticTeam,
  SyntheticWorkerCreatePayload,
} from '@/types'

const SENIORITIES = ['junior', 'mid', 'senior', 'lead'] as const
type Seniority = (typeof SENIORITIES)[number]

const FIRST_NAMES = [
  'Alex', 'Sam', 'Jordan', 'Taylor', 'Casey', 'Robin', 'Morgan', 'Riley',
  'Quinn', 'Dakota', 'Avery', 'Drew', 'Skylar', 'Jamie', 'Reese', 'Cameron',
]
const LAST_INITIALS = ['M.', 'K.', 'P.', 'L.', 'S.', 'R.', 'T.', 'B.']

function rand(min: number, max: number) {
  return min + Math.random() * (max - min)
}
function clip(x: number, lo = 0, hi = 1) {
  return Math.max(lo, Math.min(hi, x))
}
function pickWeighted<T>(items: readonly T[], weights: number[]): T {
  const total = weights.reduce((a, b) => a + b, 0)
  let r = Math.random() * total
  for (let i = 0; i < items.length; i++) {
    r -= weights[i]
    if (r <= 0) return items[i]
  }
  return items[items.length - 1]
}

/** Redistribute so distribution sums to 100, holding index `i` at newValue. */
function redistribute(dist: number[], i: number, newValue: number): number[] {
  const clamped = clip(newValue, 0, 100)
  const others = dist.map((v, idx) => (idx === i ? 0 : v))
  const otherSum = others.reduce((a, b) => a + b, 0)
  const remaining = 100 - clamped
  const out = dist.slice()
  out[i] = clamped
  if (otherSum <= 0.0001) {
    const each = remaining / (dist.length - 1)
    for (let k = 0; k < dist.length; k++) if (k !== i) out[k] = each
  } else {
    for (let k = 0; k < dist.length; k++) {
      if (k !== i) out[k] = (others[k] / otherSum) * remaining
    }
  }
  return out
}

interface Props {
  open: boolean
  onOpenChange: (open: boolean) => void
  categories: Category[]
  onCreated?: (team: SyntheticTeam) => void
}

export function SyntheticTeamBuilder({ open, onOpenChange, categories, onCreated }: Props) {
  const queryClient = useQueryClient()

  const [name, setName] = useState('Synthetic Team')
  const [size, setSize] = useState(8)
  const [seniorityDist, setSeniorityDist] = useState<number[]>([25, 35, 30, 10]) // jr/mid/sr/lead
  const [stdDev, setStdDev] = useState(0.2)
  const [mismatch, setMismatch] = useState(0)

  const mutation = useMutation({
    mutationFn: () => {
      const workers = generateWorkers()
      return simulationApi.createTeam({
        name: name.trim() || 'Synthetic Team',
        workers,
      })
    },
    onSuccess: (team) => {
      queryClient.invalidateQueries({ queryKey: ['simulation', 'teams'] })
      toast.success(`Team "${team.name}" generated`)
      onCreated?.(team)
      onOpenChange(false)
    },
    onError: (e) => toast.error(getApiErrorMessage(e)),
  })

  function generateWorkers(): SyntheticWorkerCreatePayload[] {
    const workers: SyntheticWorkerCreatePayload[] = []
    if (!categories.length) return workers

    // Even distribution across project categories (no per-category sliders).
    const baseWeights = categories.map(() => 1)
    const effectiveWeights = baseWeights.map((w, i) => {
      if (mismatch <= 0) return w
      // Mismatch pushes weights toward inverse (rare categories chosen more often).
      const inv = 1 - w / baseWeights.length
      return w * (1 - mismatch) + inv * mismatch
    })

    for (let i = 0; i < size; i++) {
      const seniority = pickWeighted(SENIORITIES, seniorityDist) as Seniority
      const primaryCat = pickWeighted(categories, effectiveWeights)
      const primaryIdx = categories.indexOf(primaryCat)

      const baseHigh = 0.75
      const baseLow = 0.35
      const prof: Record<string, number> = {}
      for (let j = 0; j < categories.length; j++) {
        const isPrimary = j === primaryIdx
        const center = isPrimary ? baseHigh : baseLow
        const noise = (rand(-1, 1) * stdDev) / 2
        prof[categories[j].name] = clip(center + noise, 0.05, 0.99)
      }

      const seniorityBoost = { junior: 0.85, mid: 1.0, senior: 1.1, lead: 1.2 }[seniority]
      for (const k in prof) prof[k] = clip(prof[k] * seniorityBoost, 0.05, 0.99)

      const yearsByLevel = {
        junior: rand(0, 2),
        mid: rand(2, 5),
        senior: rand(5, 9),
        lead: rand(8, 15),
      }
      const first = FIRST_NAMES[Math.floor(Math.random() * FIRST_NAMES.length)]
      const last = LAST_INITIALS[Math.floor(Math.random() * LAST_INITIALS.length)]

      workers.push({
        name: `${first} ${last}`,
        seniority,
        years_experience: Math.round(yearsByLevel[seniority] * 10) / 10,
        primary_category: primaryCat.name,
        category_proficiency: prof,
        base_productivity: clip(0.85 + rand(-0.1, 0.25), 0.5, 1.4),
        burnout_threshold: 2400,
      })
    }
    return workers
  }

  return (
    <Sheet open={open} onOpenChange={onOpenChange}>
      <SheetContent side="right" className="flex flex-col sm:max-w-md">
        <SheetHeader>
          <SheetTitle>Create synthetic team</SheetTitle>
          <SheetDescription>
            Reusable team for simulation runs.
          </SheetDescription>
        </SheetHeader>

        <div className="mt-4 flex-1 space-y-5 overflow-y-auto pr-1">
          <div className="space-y-1.5">
            <Label htmlFor="team-name" className="text-xs">Name</Label>
            <Input
              id="team-name"
              value={name}
              onChange={(e) => setName(e.target.value)}
              placeholder="Synthetic Team"
            />
          </div>

          <Field label="Team size" value={`${size} workers`}>
            <Slider min={4} max={16} value={size} onChange={setSize} aria-label="Team size" />
          </Field>

          <div className="space-y-2">
            <div className="flex items-center justify-between">
              <Label className="text-xs">Seniority mix</Label>
              <span className="font-mono text-[10px] text-muted-foreground">
                ∑ {seniorityDist.reduce((a, b) => a + b, 0).toFixed(0)}%
              </span>
            </div>
            <div className="space-y-1.5">
              {SENIORITIES.map((s, i) => (
                <div key={s} className="grid grid-cols-[64px_1fr_36px] items-center gap-2">
                  <span className="truncate text-xs capitalize text-muted-foreground">{s}</span>
                  <Slider
                    min={0}
                    max={100}
                    step={1}
                    value={Math.round(seniorityDist[i])}
                    onChange={(v) => setSeniorityDist((d) => redistribute(d, i, v))}
                    aria-label={s}
                  />
                  <span className="text-right font-mono text-[10px]">
                    {seniorityDist[i].toFixed(0)}%
                  </span>
                </div>
              ))}
            </div>
          </div>

          <Field
            label="Skill variance"
            value={stdDev.toFixed(2)}
            hint="0 = clones · 1 = wide range"
          >
            <Slider min={0} max={1} step={0.01} value={stdDev} onChange={setStdDev} aria-label="Std deviation" />
          </Field>

          <Field
            label="Mismatch"
            value={mismatch.toFixed(2)}
            hint="0 = team fits project · 1 = skills skewed away"
          >
            <Slider min={0} max={1} step={0.01} value={mismatch} onChange={setMismatch} aria-label="Mismatch" />
          </Field>
        </div>

        <div className="mt-4 flex justify-end gap-2 border-t border-border pt-3">
          <Button variant="ghost" onClick={() => onOpenChange(false)}>
            Cancel
          </Button>
          <Button
            onClick={() => mutation.mutate()}
            disabled={mutation.isPending || !categories.length}
          >
            {mutation.isPending ? 'Generating…' : 'Generate team'}
          </Button>
        </div>
      </SheetContent>
    </Sheet>
  )
}

function Field({
  label,
  value,
  hint,
  children,
}: {
  label: string
  value?: string
  hint?: string
  children: React.ReactNode
}) {
  return (
    <div className="space-y-1.5">
      <div className="flex items-center justify-between">
        <Label className="text-xs">{label}</Label>
        {value && <span className="font-mono text-[10px] text-muted-foreground">{value}</span>}
      </div>
      {children}
      {hint && <p className="text-[10px] text-muted-foreground">{hint}</p>}
    </div>
  )
}
