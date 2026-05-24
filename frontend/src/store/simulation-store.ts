import { create } from 'zustand'

import type { SimulationEvent, SimulationRun, Ticket } from '@/types'

export const SIM_STAGES = [
  'BACKLOG',
  'ASSIGNED',
  'IN_PROGRESS',
  'BLOCKED',
  'IN_REVIEW',
  'DONE',
] as const
export type SimStage = (typeof SIM_STAGES)[number]

export interface SimBoardEntry {
  ticket: Ticket
  stage: SimStage
  worker_id: number | null
  worker_name: string | null
}

interface SimulationState {
  currentRun: SimulationRun | null
  cursorEventIndex: number
  isPlaying: boolean
  speed: number
  /** sim-time position (minutes). while playing, advances at speed×real time. */
  cursorTime: number

  setRun: (run: SimulationRun | null) => void
  reset: () => void
  setCursorIndex: (i: number) => void
  setCursorTime: (t: number) => void
  step: (dir: 1 | -1) => void
  setPlaying: (p: boolean) => void
  setSpeed: (s: number) => void
}

export const useSimulationStore = create<SimulationState>((set, get) => ({
  currentRun: null,
  cursorEventIndex: 0,
  isPlaying: false,
  speed: 1,
  cursorTime: 0,

  setRun: (run) => set({ currentRun: run, cursorEventIndex: 0, cursorTime: 0, isPlaying: false }),
  reset: () => set({ cursorEventIndex: 0, cursorTime: 0, isPlaying: false }),
  setCursorIndex: (i) => {
    const run = get().currentRun
    if (!run) return set({ cursorEventIndex: i })
    const clamped = Math.max(0, Math.min(i, run.event_log.length))
    const t = clamped === 0 ? 0 : run.event_log[Math.min(clamped, run.event_log.length) - 1]?.t ?? 0
    set({ cursorEventIndex: clamped, cursorTime: t })
  },
  setCursorTime: (t) => {
    const run = get().currentRun
    if (!run) return set({ cursorTime: t })
    let idx = 0
    while (idx < run.event_log.length && run.event_log[idx].t <= t) idx++
    set({ cursorTime: t, cursorEventIndex: idx })
  },
  step: (dir) => {
    const { cursorEventIndex, currentRun } = get()
    if (!currentRun) return
    const next = Math.max(0, Math.min(currentRun.event_log.length, cursorEventIndex + dir))
    const t = next === 0 ? 0 : currentRun.event_log[next - 1]?.t ?? 0
    set({ cursorEventIndex: next, cursorTime: t })
  },
  setPlaying: (p) => set({ isPlaying: p }),
  setSpeed: (s) => set({ speed: s }),
}))

/** Pure derivation: replay events [0..cursorIndex) over initial tickets. */
export function deriveBoardState(
  tickets: Ticket[],
  events: SimulationEvent[],
  cursorIndex: number,
): Map<number, SimBoardEntry> {
  const map = new Map<number, SimBoardEntry>()
  for (const t of tickets) {
    map.set(t.id, { ticket: t, stage: 'BACKLOG', worker_id: null, worker_name: null })
  }
  for (let i = 0; i < cursorIndex && i < events.length; i++) {
    const ev = events[i]
    const entry = map.get(ev.ticket_id)
    if (!entry) continue
    if (ev.to_stage && (SIM_STAGES as readonly string[]).includes(ev.to_stage)) {
      entry.stage = ev.to_stage as SimStage
    }
    if (ev.type === 'assigned') {
      entry.worker_id = ev.worker_id
      entry.worker_name = ev.worker_name
    }
  }
  return map
}
