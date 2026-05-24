import { useAuthStore } from '@/store/auth-store'

export type ComplexityProfile = 'simple' | 'medium' | 'complex'

export interface TaskGenerationConfig {
  complexity_profile: ComplexityProfile
  total_hours_min: number
  total_hours_max: number
  task_count: number
}

export interface DiffusionPlanItem {
  category_id: number
  category_name: string
  weight: number
  description: string
  is_new: boolean
  color: string
}

export interface GeneratedTicket {
  id: number
  project_id: number
  stage_id: number
  title: string
  description: string | null
  priority: string
  complexity: number
  category_id: number | null
  category_name: string | null
  category_color: string | null
  estimated_minutes: number | null
}

export type GenerationEvent =
  | { type: 'diffusion'; data: { plan: DiffusionPlanItem[] } }
  | { type: 'batch'; data: { batch_index: number; tickets: GeneratedTicket[] } }
  | { type: 'done'; data: { total: number } }
  | { type: 'error'; data: { message: string } }

export interface GenerationHandlers {
  onDiffusion?: (plan: DiffusionPlanItem[]) => void
  onBatch?: (batch_index: number, tickets: GeneratedTicket[]) => void
  onDone?: (total: number) => void
  onError?: (message: string) => void
}

/**
 * Stream POST /projects/{id}/generate-tasks via fetch streaming + manual SSE parsing.
 * EventSource only supports GET; we need POST so we read the raw response stream.
 */
export async function streamGenerateTasks(
  projectId: number,
  config: TaskGenerationConfig,
  handlers: GenerationHandlers,
  signal?: AbortSignal,
): Promise<void> {
  console.log('[streamGenerateTasks] fetch start', projectId, config)
  const token = useAuthStore.getState().token
  let res: Response
  try {
    res = await fetch(`/api/v1/projects/${projectId}/generate-tasks`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        Accept: 'text/event-stream',
        ...(token ? { Authorization: `Bearer ${token}` } : {}),
      },
      body: JSON.stringify({ generation_config: config }),
      signal,
    })
  } catch (e) {
    console.error('[streamGenerateTasks] fetch threw', e)
    handlers.onError?.(String((e as Error)?.message ?? e))
    return
  }
  console.log('[streamGenerateTasks] response', res.status, res.headers.get('content-type'))

  if (!res.ok || !res.body) {
    handlers.onError?.(`HTTP ${res.status}`)
    return
  }

  const reader = res.body.getReader()
  const decoder = new TextDecoder()
  let buffer = ''

  while (true) {
    const { value, done } = await reader.read()
    if (done) break
    buffer += decoder.decode(value, { stream: true })

    let sep
    while ((sep = buffer.indexOf('\n\n')) >= 0) {
      const chunk = buffer.slice(0, sep)
      buffer = buffer.slice(sep + 2)
      const dataLine = chunk
        .split('\n')
        .find((l) => l.startsWith('data:'))
      if (!dataLine) continue
      const json = dataLine.slice(5).trim()
      try {
        const evt = JSON.parse(json) as GenerationEvent
        dispatch(evt, handlers)
      } catch {
        // ignore malformed event
      }
    }
  }
}

function dispatch(evt: GenerationEvent, h: GenerationHandlers) {
  if (evt.type === 'diffusion') h.onDiffusion?.(evt.data.plan)
  else if (evt.type === 'batch') h.onBatch?.(evt.data.batch_index, evt.data.tickets)
  else if (evt.type === 'done') h.onDone?.(evt.data.total)
  else if (evt.type === 'error') h.onError?.(evt.data.message)
}
