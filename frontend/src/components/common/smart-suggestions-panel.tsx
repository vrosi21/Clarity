/**
 * Smart suggestions panel — single source: LangChain/Grok via /tickets/suggest.
 *
 * Returns: category (single best match + confidence), story points with
 * reasoning tooltip, tags (existing + new proposals), and ranked workers.
 *
 * autoAccept=true  → top suggestions applied automatically; all controls locked.
 * autoAccept=false → manual select; suggested options are visually highlighted.
 */
import { Check, Lock, Loader2, Plus, Sparkles, WifiOff, X, Zap } from 'lucide-react'
import { useEffect, useRef, useState } from 'react'
import { toast } from 'sonner'

import { Avatar, AvatarFallback } from '@/components/ui/avatar'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Switch } from '@/components/ui/switch'
import { Tooltip, TooltipContent, TooltipProvider, TooltipTrigger } from '@/components/ui/tooltip'
import { cn, getInitials } from '@/lib/utils'
import type { Category, SuggestResponse } from '@/types'

const STORY_POINT_LABELS: Record<number, string> = {
  1: 'Trivial',
  2: 'Small',
  3: 'Medium',
  4: 'Large',
  5: 'X-Large',
}
const STORY_POINT_VALUES = [1, 2, 3, 4, 5] as const

type TagBubbleState = 'suggested' | 'accepted' | 'rejected'

function confidenceColor(c: number) {
  if (c >= 0.7) return 'bg-green-500/20 text-green-700 dark:text-green-400'
  if (c >= 0.45) return 'bg-yellow-500/20 text-yellow-700 dark:text-yellow-400'
  return 'bg-muted text-muted-foreground'
}

/**
 * Guard against the LLM producing sentence fragments as new_suggestion.
 * A valid category name is short (<=2 words), not starting with a stop word,
 * and doesn't look like a sentence fragment.
 */
const STOP_WORDS = new Set([
  'the', 'a', 'an', 'is', 'be', 'to', 'of', 'for', 'in', 'on', 'at',
  'with', 'and', 'or', 'but', 'so', 'if', 'as', 'it', 'by', 'via',
  'this', 'that', 'these', 'those', 'we', 'you', 'they', 'he', 'she',
  'make', 'sure', 'all', 'ensure', 'update', 'fix', 'add', 'get', 'set',
  'check', 'sync', 'run', 'use', 'build', 'create', 'change', 'show',
  'move', 'remove', 'delete', 'apply', 'allow', 'enable', 'support',
  'evaluate', 'assess', 'review', 'verify', 'test', 'implement', 'render',
  'please', 'just', 'also', 'too', 'now', 'not', 'no', 'new', 'old',
  'up', 'out', 'do', 'did', 'has', 'have',
])

function isValidCategoryName(name: string | null | undefined): boolean {
  if (!name) return false
  const trimmed = name.trim()
  if (trimmed.length < 2 || trimmed.length > 40) return false
  const words = trimmed.toLowerCase().split(/\s+/)
  if (words.length > 2) return false
  if (STOP_WORDS.has(words[0])) return false
  if (/[.!?,;]/.test(trimmed)) return false
  return true
}

interface Props {
  suggestData?: SuggestResponse | null
  suggestLoading?: boolean
  /** Non-empty title means we've had a chance to call the suggest endpoint. */
  titleNonEmpty?: boolean
  autoAccept: boolean
  onAutoAcceptChange: (v: boolean) => void
  allCategories: Category[]
  selectedCategoryIds: number[]
  onToggleCategory: (id: number) => void
  /** Replace the entire selection — used by auto-accept to override user picks. */
  onResetCategories?: (ids: number[]) => void
  selectedStoryPoints: number
  onSelectStoryPoints: (v: number) => void
  selectedWorkerId: number | null
  onSelectWorker: (id: number | null) => void
  canManageCategories?: boolean
  onCreateCategory?: (name: string) => Promise<void>
  /** Confidence threshold for auto-accept (0–1). */
  threshold?: number
  selectedTagNames?: string[]
  onTagAccept?: (name: string) => void
  onTagReject?: (name: string) => void
  onNewTagConfirm?: (name: string) => Promise<void>
}

export function SmartSuggestionsPanel({
  suggestData,
  suggestLoading = false,
  titleNonEmpty = false,
  autoAccept,
  onAutoAcceptChange,
  allCategories,
  selectedCategoryIds,
  onToggleCategory,
  onResetCategories,
  selectedStoryPoints,
  onSelectStoryPoints,
  selectedWorkerId,
  onSelectWorker,
  canManageCategories = false,
  onCreateCategory,
  threshold = 0.7,
  selectedTagNames = [],
  onTagAccept,
  onTagReject,
  onNewTagConfirm,
}: Props) {
  const [showNewInput, setShowNewInput] = useState(false)
  const [newName, setNewName] = useState('')
  const [creating, setCreating] = useState(false)
  const [createdCategoryNames, setCreatedCategoryNames] = useState<Set<string>>(new Set())
  const [rejectedTags, setRejectedTags] = useState<Set<string>>(new Set())
  const [showNewTagInput, setShowNewTagInput] = useState(false)
  const [newTagName, setNewTagName] = useState('')
  const [creatingTag, setCreatingTag] = useState(false)
  const inputRef = useRef<HTMLInputElement>(null)
  const tagInputRef = useRef<HTMLInputElement>(null)

  // Single matched category from Grok + its confidence
  const suggestedCategoryId = suggestData?.category?.match_id ?? null
  const suggestedCategoryConfidence = suggestData?.category?.confidence ?? 0

  // Story points from Grok
  const recommendedSp = suggestData?.complexity?.score ?? null
  const spReasoning = suggestData?.complexity?.reasoning ?? null

  // New category proposals — validate before showing
  const llmNewCategory = (() => {
    const n = suggestData?.category?.new_suggestion
    if (!isValidCategoryName(n)) return null
    if (createdCategoryNames.has(n!.toLowerCase())) return null
    return n!
  })()

  const isUnavailable = titleNonEmpty && !suggestLoading && suggestData === null

  const workers = suggestData?.workers ?? []

  // Auto-accept
  useEffect(() => {
    if (!autoAccept || !suggestData) return

    // Category
    if (suggestedCategoryId !== null) {
      if (onResetCategories) {
        onResetCategories([suggestedCategoryId])
      } else if (!selectedCategoryIds.includes(suggestedCategoryId)) {
        onToggleCategory(suggestedCategoryId)
      }
    }

    // Story points
    if (recommendedSp !== null) onSelectStoryPoints(recommendedSp)

    // Worker
    if (workers.length > 0) onSelectWorker(workers[0].user_id)

    // Tags
    suggestData.tags?.suggested_tags?.forEach((name) => {
      if (!rejectedTags.has(name) && !selectedTagNames.includes(name)) {
        onTagAccept?.(name)
      }
    })
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [autoAccept, suggestData])

  useEffect(() => {
    if (isUnavailable && autoAccept) handleAutoAcceptChange(false)
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [isUnavailable])

  useEffect(() => {
    if (showNewInput) inputRef.current?.focus()
  }, [showNewInput])

  useEffect(() => {
    if (showNewTagInput) tagInputRef.current?.focus()
  }, [showNewTagInput])

  const handleAutoAcceptChange = (v: boolean) => {
    if (v) setRejectedTags(new Set())
    onAutoAcceptChange(v)
  }

  const handleCreateSubmit = async (nameOverride?: string) => {
    const name = (nameOverride ?? newName).trim()
    if (!name || !onCreateCategory) return
    setCreating(true)
    try {
      await onCreateCategory(name)
      setCreatedCategoryNames((s) => new Set(s).add(name.toLowerCase()))
      setNewName('')
      setShowNewInput(false)
    } catch (err: any) {
      const status = err?.response?.status
      if (status === 409) {
        setCreatedCategoryNames((s) => new Set(s).add(name.toLowerCase()))
        setNewName('')
        setShowNewInput(false)
        toast.info(`Category "${name}" already exists`)
      } else {
        toast.error(err?.response?.data?.detail ?? `Failed to create category "${name}"`)
      }
    } finally {
      setCreating(false)
    }
  }

  const handleCreateTagSubmit = async () => {
    const name = newTagName.trim()
    if (!name || !onNewTagConfirm) return
    setCreatingTag(true)
    try {
      await onNewTagConfirm(name)
      setNewTagName('')
      setShowNewTagInput(false)
    } catch (err: any) {
      const status = err?.response?.status
      if (status === 409) {
        toast.info(`Tag "${name}" already exists`)
        setNewTagName('')
        setShowNewTagInput(false)
      } else {
        toast.error(err?.response?.data?.detail ?? `Failed to create tag "${name}"`)
      }
    } finally {
      setCreatingTag(false)
    }
  }

  const handleTagClick = (name: string) => {
    if (selectedTagNames.includes(name)) {
      onTagReject?.(name)
      setRejectedTags((s) => new Set(s).add(name))
    } else {
      setRejectedTags((s) => { const next = new Set(s); next.delete(name); return next })
      onTagAccept?.(name)
    }
  }

  const hasTags =
    (suggestData?.tags?.suggested_tags?.length ?? 0) > 0 ||
    (suggestData?.tags?.new_suggestions?.length ?? 0) > 0

  return (
    <TooltipProvider>
      <div className="rounded-lg border border-border bg-muted/30 p-3 space-y-3">

        {/* Header */}
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-1.5 text-sm font-medium text-muted-foreground">
            <Sparkles className="h-3.5 w-3.5" />
            Smart suggestions
            {suggestLoading && <Loader2 className="h-3 w-3 animate-spin ml-1" />}
          </div>
          <div className="flex items-center gap-2">
            {autoAccept && !isUnavailable && <Lock className="h-3 w-3 text-muted-foreground" aria-hidden />}
            <Label
              htmlFor="auto-accept"
              className={cn('text-xs', isUnavailable ? 'text-muted-foreground/50' : 'text-muted-foreground')}
            >
              Auto-accept
            </Label>
            <Switch
              id="auto-accept"
              checked={autoAccept && !isUnavailable}
              disabled={isUnavailable}
              onCheckedChange={handleAutoAcceptChange}
              className="scale-75"
            />
          </div>
        </div>

        {/* Unavailable banner */}
        {isUnavailable && (
          <div className="flex items-center gap-1.5 rounded-md bg-muted/60 px-3 py-2 text-xs text-muted-foreground">
            <WifiOff className="h-3.5 w-3.5 shrink-0" />
            Smart suggestions unavailable — check your API key and server connection.
          </div>
        )}

        {/* Categories */}
        <div className="space-y-1.5">
          <p className="text-xs font-medium text-muted-foreground">
            Categories
            {!autoAccept && (
              <span className="ml-1 font-normal opacity-60">— select all that apply</span>
            )}
            {!autoAccept && selectedCategoryIds.length > 1 && (
              <span className="ml-1 font-normal opacity-60">(primary: first selected)</span>
            )}
          </p>
          <div className={cn('flex flex-wrap gap-1.5', autoAccept && 'pointer-events-none')}>
            {allCategories.length === 0 && (
              <span className="text-xs text-muted-foreground">No categories yet.</span>
            )}
            {allCategories.map((c) => {
              const isSelected = selectedCategoryIds.includes(c.id)
              const isPrimary = selectedCategoryIds[0] === c.id
              const isRecommended = c.id === suggestedCategoryId
              const confidence = isRecommended ? suggestedCategoryConfidence : undefined
              return (
                <button
                  key={c.id}
                  type="button"
                  disabled={autoAccept}
                  onClick={() => onToggleCategory(c.id)}
                  className={cn(
                    'inline-flex items-center gap-1 rounded-full px-2.5 py-0.5 text-xs font-medium border transition-all',
                    isRecommended
                      ? confidenceColor(suggestedCategoryConfidence)
                      : 'border-border bg-background/60 text-muted-foreground hover:bg-muted',
                    isSelected && 'ring-2 ring-primary ring-offset-1',
                    isPrimary && 'font-semibold',
                    autoAccept && 'opacity-60 cursor-default',
                  )}
                >
                  {c.name}
                  {isRecommended && confidence !== undefined && (
                    <span className="opacity-60">{Math.round(confidence * 100)}%</span>
                  )}
                  {isPrimary && selectedCategoryIds.length > 1 && (
                    <span className="text-[9px] uppercase tracking-wide opacity-70">primary</span>
                  )}
                </button>
              )
            })}

            {/* LLM-suggested new category */}
            {canManageCategories && !autoAccept && llmNewCategory && (
              <button
                type="button"
                disabled={creating}
                title="AI-suggested. Click to create and apply."
                onClick={() => handleCreateSubmit(llmNewCategory)}
                className="inline-flex items-center gap-1 rounded-full border border-dashed border-primary/50 px-2.5 py-0.5 text-xs font-medium text-primary/80 hover:border-primary hover:text-primary disabled:opacity-50 transition-all"
              >
                {creating ? <Loader2 className="h-3 w-3 animate-spin" /> : <Sparkles className="h-3 w-3" />}
                {`Create "${llmNewCategory}"`}
              </button>
            )}

            {canManageCategories && !autoAccept && !showNewInput && (
              <button
                type="button"
                onClick={() => { setNewName(''); setShowNewInput(true) }}
                className="inline-flex items-center gap-1 rounded-full border border-dashed border-muted-foreground/40 px-2.5 py-0.5 text-xs text-muted-foreground hover:border-muted-foreground hover:text-foreground transition-all"
              >
                <Plus className="h-3 w-3" />
                New category
              </button>
            )}

            {canManageCategories && !autoAccept && showNewInput && (
              <div className="flex items-center gap-1">
                <Input
                  ref={inputRef}
                  value={newName}
                  onChange={(e) => setNewName(e.target.value)}
                  onKeyDown={(e) => {
                    if (e.key === 'Enter') { e.preventDefault(); handleCreateSubmit() }
                    if (e.key === 'Escape') { setShowNewInput(false); setNewName('') }
                  }}
                  placeholder="category name"
                  className="h-6 w-32 rounded-full px-2.5 py-0 text-xs"
                  disabled={creating}
                  maxLength={64}
                />
                <button
                  type="button"
                  disabled={creating || !newName.trim()}
                  onClick={() => handleCreateSubmit()}
                  className="inline-flex items-center rounded-full bg-primary/10 px-2 py-0.5 text-xs font-medium text-primary hover:bg-primary/20 disabled:opacity-50 transition-all"
                >
                  {creating ? <Loader2 className="h-3 w-3 animate-spin" /> : 'Add'}
                </button>
                <button
                  type="button"
                  onClick={() => { setShowNewInput(false); setNewName('') }}
                  className="text-muted-foreground hover:text-foreground"
                >
                  <X className="h-3.5 w-3.5" />
                </button>
              </div>
            )}
          </div>
        </div>

        {/* Story points */}
        <div className="space-y-1.5">
          <p className="text-xs font-medium text-muted-foreground">Story points</p>
          <div className={cn('flex flex-wrap gap-1.5', autoAccept && 'pointer-events-none')}>
            {STORY_POINT_VALUES.map((v) => {
              const isSelected = selectedStoryPoints === v
              const isRecommended = recommendedSp === v
              const bgClass = isRecommended && isSelected
                ? confidenceColor(0.9)
                : isSelected
                  ? 'border-primary/60 bg-primary/10 text-foreground'
                  : 'border-border bg-background/60 text-muted-foreground hover:bg-muted'
              return (
                <Tooltip key={v}>
                  <TooltipTrigger asChild>
                    <button
                      type="button"
                      disabled={autoAccept}
                      onClick={() => onSelectStoryPoints(v)}
                      className={cn(
                        'inline-flex items-center gap-1.5 rounded-full px-2.5 py-0.5 text-xs font-medium border transition-all',
                        bgClass,
                        isSelected && 'ring-2 ring-primary ring-offset-1',
                        autoAccept && 'opacity-60 cursor-default',
                      )}
                    >
                      {isSelected && (
                        autoAccept ? <Zap className="h-3 w-3" /> : <Check className="h-3 w-3" />
                      )}
                      {v}
                      <span className="opacity-70">{STORY_POINT_LABELS[v]}</span>
                      {isRecommended && !isSelected && (
                        <Sparkles className="h-2.5 w-2.5 opacity-40" />
                      )}
                      {isRecommended && isSelected && (
                        <Sparkles className="h-2.5 w-2.5 opacity-70" />
                      )}
                    </button>
                  </TooltipTrigger>
                  {isRecommended && spReasoning && (
                    <TooltipContent side="bottom" className="text-xs max-w-xs">
                      {spReasoning}
                    </TooltipContent>
                  )}
                </Tooltip>
              )
            })}
          </div>
        </div>

        {/* Tags */}
        {(hasTags || (onNewTagConfirm && !autoAccept)) && (
          <div className="space-y-1.5">
            <p className="text-xs font-medium text-muted-foreground">Tags</p>
            <div className={cn('flex flex-wrap gap-1.5', autoAccept && 'pointer-events-none')}>
              {suggestData?.tags?.suggested_tags?.map((name) => {
                const isActive = selectedTagNames.includes(name)
                const isRejected = rejectedTags.has(name)
                const state: TagBubbleState = isActive ? 'accepted' : isRejected ? 'rejected' : 'suggested'
                return (
                  <TagChip
                    key={name}
                    label={name}
                    state={state}
                    autoApplied={autoAccept && isActive}
                    disabled={autoAccept}
                    onClick={() => handleTagClick(name)}
                  />
                )
              })}
              {suggestData?.tags?.new_suggestions?.map((name) => {
                const isAccepted = selectedTagNames.includes(name)
                return (
                  <TagChip
                    key={`new:${name}`}
                    label={name}
                    state={isAccepted ? 'accepted' : 'suggested'}
                    isNew={!isAccepted}
                    disabled={autoAccept}
                    onClick={() => {
                      if (isAccepted) {
                        onTagReject?.(name)
                      } else {
                        onNewTagConfirm?.(name).catch(() => {})
                      }
                    }}
                  />
                )
              })}
              {onNewTagConfirm && !autoAccept && !showNewTagInput && (
                <button
                  type="button"
                  onClick={() => { setNewTagName(''); setShowNewTagInput(true) }}
                  className="inline-flex items-center gap-1 rounded-full border border-dashed border-muted-foreground/40 px-2.5 py-0.5 text-xs text-muted-foreground hover:border-muted-foreground hover:text-foreground transition-all"
                >
                  <Plus className="h-3 w-3" />
                  New tag
                </button>
              )}
              {onNewTagConfirm && !autoAccept && showNewTagInput && (
                <div className="flex items-center gap-1">
                  <Input
                    ref={tagInputRef}
                    value={newTagName}
                    onChange={(e) => setNewTagName(e.target.value)}
                    onKeyDown={(e) => {
                      if (e.key === 'Enter') { e.preventDefault(); handleCreateTagSubmit() }
                      if (e.key === 'Escape') { setShowNewTagInput(false); setNewTagName('') }
                    }}
                    placeholder="tag name"
                    className="h-6 w-28 rounded-full px-2.5 py-0 text-xs"
                    disabled={creatingTag}
                    maxLength={32}
                  />
                  <button
                    type="button"
                    disabled={creatingTag || !newTagName.trim()}
                    onClick={handleCreateTagSubmit}
                    className="inline-flex items-center rounded-full bg-primary/10 px-2 py-0.5 text-xs font-medium text-primary hover:bg-primary/20 disabled:opacity-50 transition-all"
                  >
                    {creatingTag ? <Loader2 className="h-3 w-3 animate-spin" /> : 'Add'}
                  </button>
                  <button
                    type="button"
                    onClick={() => { setShowNewTagInput(false); setNewTagName('') }}
                    className="text-muted-foreground hover:text-foreground"
                  >
                    <X className="h-3.5 w-3.5" />
                  </button>
                </div>
              )}
            </div>
          </div>
        )}

        {/* Workers */}
        {workers.length > 0 && (
          <div className="space-y-1.5">
            <p className="text-xs font-medium text-muted-foreground">Suggested assignees</p>
            <div className={cn('flex flex-col gap-1.5', autoAccept && 'pointer-events-none')}>
              {workers.slice(0, 5).map((w) => {
                const isSelected = selectedWorkerId === w.user_id
                return (
                  <button
                    key={w.user_id}
                    type="button"
                    disabled={autoAccept}
                    onClick={() => onSelectWorker(isSelected ? null : w.user_id)}
                    className={cn(
                      'flex items-center gap-2.5 rounded-lg border px-2.5 py-1.5 text-left transition-all',
                      isSelected
                        ? 'border-primary/40 bg-primary/5 ring-1 ring-primary'
                        : 'border-border bg-background/60 hover:bg-muted',
                      autoAccept && 'opacity-60 cursor-default',
                    )}
                  >
                    <Avatar className="h-6 w-6 shrink-0">
                      <AvatarFallback className="text-[10px]">
                        {getInitials(w.username)}
                      </AvatarFallback>
                    </Avatar>
                    <span className="text-xs font-medium flex-1">{w.username}</span>
                    <div className="flex items-center gap-1 flex-wrap justify-end">
                      {w.reasons.map((r) => (
                        <span
                          key={r}
                          className="rounded-full bg-muted px-1.5 py-0.5 text-[10px] text-muted-foreground"
                        >
                          {r}
                        </span>
                      ))}
                    </div>
                    <div className="w-14 shrink-0">
                      <div className="h-1 rounded-full bg-muted overflow-hidden">
                        <div
                          className="h-full rounded-full bg-primary/60"
                          style={{ width: `${Math.round(w.score * 100)}%` }}
                        />
                      </div>
                      <span className="text-[10px] text-muted-foreground">
                        {Math.round(w.score * 100)}%
                      </span>
                    </div>
                    {autoAccept && isSelected && <Zap className="h-3 w-3 text-primary shrink-0" />}
                  </button>
                )
              })}
            </div>
          </div>
        )}
      </div>
    </TooltipProvider>
  )
}

// ── Tag chip sub-component ────────────────────────────────────────────────────

interface TagChipProps {
  label: string
  state: TagBubbleState
  isNew?: boolean
  autoApplied?: boolean
  disabled?: boolean
  onClick: () => void
}

function TagChip({ label, state, isNew = false, autoApplied = false, disabled = false, onClick }: TagChipProps) {
  return (
    <button
      type="button"
      disabled={disabled}
      onClick={onClick}
      className={cn(
        'inline-flex items-center gap-1 rounded-full px-2.5 py-0.5 text-xs font-medium border transition-all',
        state === 'accepted'
          ? 'border-primary/40 bg-primary/10 text-primary ring-1 ring-primary/30'
          : state === 'rejected'
            ? 'border-border bg-muted/40 text-muted-foreground/50 line-through'
            : 'border-border bg-background/60 text-muted-foreground hover:bg-muted',
        disabled && 'cursor-default opacity-60',
      )}
    >
      {autoApplied && <Zap className="h-2.5 w-2.5" />}
      {isNew && state !== 'accepted' && <Plus className="h-2.5 w-2.5" />}
      {state === 'accepted' && !autoApplied && <Check className="h-2.5 w-2.5" />}
      {label}
    </button>
  )
}
