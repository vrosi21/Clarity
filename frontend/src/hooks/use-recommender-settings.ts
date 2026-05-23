/**
 * Per-project recommender preferences (auto-accept toggle + confidence threshold).
 *
 * Backed by localStorage so the feature works end-to-end without backend changes.
 * Swap to a `projectsApi.getSettings` / `updateSettings` round-trip when the
 * server-side persistence lands — same shape, no callsite changes required.
 */
import { useCallback, useEffect, useState } from 'react'

import type { RecommenderProjectSettings } from '@/types'

const DEFAULTS: RecommenderProjectSettings = {
  auto_accept: false,
  threshold: 0.7,
}

const key = (projectId: number) => `clarity:recommender:${projectId}`

function read(projectId: number): RecommenderProjectSettings {
  try {
    const raw = localStorage.getItem(key(projectId))
    if (!raw) return DEFAULTS
    const parsed = JSON.parse(raw) as Partial<RecommenderProjectSettings>
    return {
      auto_accept: Boolean(parsed.auto_accept ?? DEFAULTS.auto_accept),
      threshold: Math.min(
        1,
        Math.max(0, Number(parsed.threshold ?? DEFAULTS.threshold)),
      ),
    }
  } catch {
    return DEFAULTS
  }
}

export function useRecommenderSettings(projectId: number) {
  const [settings, setSettings] = useState<RecommenderProjectSettings>(() =>
    read(projectId),
  )

  useEffect(() => {
    setSettings(read(projectId))
  }, [projectId])

  const update = useCallback(
    (patch: Partial<RecommenderProjectSettings>) => {
      setSettings((prev) => {
        const next = { ...prev, ...patch }
        try {
          localStorage.setItem(key(projectId), JSON.stringify(next))
        } catch {
          // localStorage may be unavailable in private modes — fail silently.
        }
        return next
      })
    },
    [projectId],
  )

  return { settings, update }
}
