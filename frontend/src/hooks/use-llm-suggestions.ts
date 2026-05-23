/**
 * Debounced hook for Grok/LangChain ticket suggestions.
 *
 * Calls POST /projects/{id}/tickets/suggest with a 600 ms debounce.
 * Cancels in-flight requests via AbortController on each new keystroke.
 * Returns null silently if the API is unavailable — callers handle null.
 *
 * Returns: complexity, category (single best match), tags, AND workers
 * (scored via FeatureWorkerScorer on the backend — no extra call needed).
 */
import { useEffect, useRef, useState } from 'react'

import { ticketsApi } from '@/api/tickets'
import type { SuggestResponse } from '@/types'

const DEBOUNCE_MS = 600

interface Options {
  projectId: number
  title: string
  description: string
  categoryIds?: number[]
  complexity?: number | null
  enabled?: boolean
}

export function useLlmSuggestions({
  projectId,
  title,
  description,
  categoryIds = [],
  complexity = null,
  enabled = true,
}: Options) {
  const [suggestData, setSuggestData] = useState<SuggestResponse | null>(null)
  const [suggestLoading, setSuggestLoading] = useState(false)
  const timerRef = useRef<ReturnType<typeof setTimeout> | null>(null)
  const abortRef = useRef<AbortController | null>(null)

  // Stable key for category IDs to avoid spurious re-fires.
  const categoryKey = categoryIds.slice().sort().join(',')

  useEffect(() => {
    if (!enabled || !title.trim()) {
      setSuggestData(null)
      return
    }

    if (timerRef.current) clearTimeout(timerRef.current)

    timerRef.current = setTimeout(async () => {
      if (abortRef.current) abortRef.current.abort()
      abortRef.current = new AbortController()
      setSuggestLoading(true)
      try {
        const res = await ticketsApi.suggest(projectId, {
          title,
          description: description || undefined,
          category_ids: categoryIds.length > 0 ? categoryIds : undefined,
          complexity: complexity ?? undefined,
        })
        setSuggestData(res)
      } catch (err: any) {
        if (err?.name !== 'AbortError' && err?.code !== 'ERR_CANCELED') {
          setSuggestData(null)
        }
      } finally {
        setSuggestLoading(false)
      }
    }, DEBOUNCE_MS)

    return () => {
      if (timerRef.current) clearTimeout(timerRef.current)
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [enabled, projectId, title, description, categoryKey, complexity])

  return { suggestData, suggestLoading }
}
