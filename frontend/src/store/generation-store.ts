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
  tickets: GeneratedTicket[]
  targetCount: number
  errorMessage: string | null

  schedule: (req: PendingRequest) => void
  consumePending: () => PendingRequest | null

  start: (projectId: number, targetCount: number) => void
  setDiffusion: (plan: DiffusionPlanItem[]) => void
  appendBatch: (tickets: GeneratedTicket[]) => void
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
      errorMessage: null,
    }),
  setDiffusion: (plan) => set({ diffusion: plan, status: 'generating' }),
  appendBatch: (tickets) =>
    set((s) => ({ tickets: [...s.tickets, ...tickets] })),
  finish: () => set({ status: 'done' }),
  fail: (message) => set({ status: 'error', errorMessage: message }),
  reset: () =>
    set({
      pending: null,
      status: 'idle',
      projectId: null,
      diffusion: [],
      tickets: [],
      targetCount: 0,
      errorMessage: null,
    }),
}))
