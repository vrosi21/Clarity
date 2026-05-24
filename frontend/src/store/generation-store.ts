import { create } from 'zustand'

import type {
  DiffusionPlanItem,
  GeneratedTicket,
  TaskGenerationConfig,
} from '@/api/task-generation'

export type GenerationStatus = 'idle' | 'analysing' | 'generating' | 'done' | 'error'

interface PendingRequest {
  projectId: number
  config: TaskGenerationConfig
}

interface GenerationState {
  pending: PendingRequest | null
  status: GenerationStatus
  projectId: number | null
  diffusion: DiffusionPlanItem[]
  /** All tickets received from SSE so far (any reveal state). */
  tickets: GeneratedTicket[]
  /** How many of `tickets` are currently shown on the backlog column. */
  visibleCount: number
  targetCount: number
  errorMessage: string | null

  schedule: (req: PendingRequest) => void
  consumePending: () => PendingRequest | null

  start: (projectId: number, targetCount: number) => void
  setDiffusion: (plan: DiffusionPlanItem[]) => void
  appendBatch: (tickets: GeneratedTicket[]) => void
  revealOne: () => void
  finish: () => void
  fail: (message: string) => void
  reset: () => void
}

export const useGenerationStore = create<GenerationState>((set, get) => ({
  pending: null,
  status: 'idle',
  projectId: null,
  diffusion: [],
  tickets: [],
  visibleCount: 0,
  targetCount: 0,
  errorMessage: null,

  schedule: (req) => set({ pending: req }),
  consumePending: () => {
    const p = get().pending
    set({ pending: null })
    return p
  },

  start: (projectId, targetCount) =>
    set({
      status: 'analysing',
      projectId,
      targetCount,
      diffusion: [],
      tickets: [],
      visibleCount: 0,
      errorMessage: null,
    }),
  setDiffusion: (plan) => set({ diffusion: plan, status: 'generating' }),
  appendBatch: (newOnes) =>
    set((s) => ({ tickets: [...s.tickets, ...newOnes] })),
  revealOne: () =>
    set((s) => {
      if (s.visibleCount >= s.tickets.length) return {}
      return { visibleCount: s.visibleCount + 1 }
    }),
  finish: () => set({ status: 'done' }),
  fail: (message) => set({ status: 'error', errorMessage: message }),
  reset: () =>
    set({
      pending: null,
      status: 'idle',
      projectId: null,
      diffusion: [],
      tickets: [],
      visibleCount: 0,
      targetCount: 0,
      errorMessage: null,
    }),
}))
