/**
 * Worker profile sheet.
 *
 * Bio text → LangChain skill extractor → skill bubbles + proficiency chips.
 * Admin can accept/reject both. On save:
 *   1. PATCH /admin/users/{id}  — persists bio, triggers NLP embedding refresh
 *   2. POST  /users/me/skills/apply — writes accepted WorkerSkillProfile rows
 *      so per-category proficiency (the 50 % weight in worker scoring) is set.
 */
import { useMutation, useQueryClient } from '@tanstack/react-query'
import { useEffect, useState } from 'react'
import { toast } from 'sonner'
import { Loader2, Wand2 } from 'lucide-react'

import { adminApi } from '@/api/admin'
import { BubbleChip } from '@/components/common/bubble-chip'
import { Button } from '@/components/ui/button'
import { Label } from '@/components/ui/label'
import {
  Sheet,
  SheetContent,
  SheetFooter,
  SheetHeader,
  SheetTitle,
} from '@/components/ui/sheet'
import { Textarea } from '@/components/ui/textarea'
import type { CategoryProficiency, SkillSuggestResponse, UserDetail } from '@/types'

interface Props {
  user: UserDetail | null
  onClose: () => void
}

const BIO_DEBOUNCE_MS = 800

export function WorkerProfileSheet({ user, onClose }: Props) {
  const qc = useQueryClient()
  const [bio, setBio] = useState('')
  const [suggestion, setSuggestion] = useState<SkillSuggestResponse | null>(null)
  const [rejectedSkills, setRejectedSkills] = useState<Set<string>>(new Set())
  // Track which category proficiency chips have been rejected by the admin.
  const [rejectedCategories, setRejectedCategories] = useState<Set<string>>(new Set())
  const [extracting, setExtracting] = useState(false)

  useEffect(() => {
    if (user) {
      setBio(user.bio ?? '')
      setSuggestion(null)
      setRejectedSkills(new Set())
      setRejectedCategories(new Set())
    }
  }, [user])

  // Auto-trigger suggestion after typing pause.
  useEffect(() => {
    if (!user || !bio.trim()) {
      setSuggestion(null)
      return
    }
    const handle = setTimeout(async () => {
      setExtracting(true)
      try {
        const res = await adminApi.suggestSkills(bio)
        setSuggestion(res)
        // Reset rejections when new suggestions arrive.
        setRejectedSkills(new Set())
        setRejectedCategories(new Set())
      } catch {
        // Silent — Ollama may be down. Bio is still saveable manually.
      } finally {
        setExtracting(false)
      }
    }, BIO_DEBOUNCE_MS)
    return () => clearTimeout(handle)
  }, [bio, user])

  const save = useMutation({
    mutationFn: async () => {
      // 1. Save bio (triggers NLP embedding refresh in the backend).
      await adminApi.updateUser(user!.id, { bio: bio.trim() || null })

      // 2. Persist accepted proficiency scores so the worker scorer has real data.
      const accepted: CategoryProficiency[] = (suggestion?.category_proficiencies ?? [])
        .filter((cp) => !rejectedCategories.has(cp.category))
      if (accepted.length > 0) {
        await adminApi.applySkills(accepted)
      }
    },
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['admin', 'users'] })
      qc.invalidateQueries({ queryKey: ['admin', 'user', user!.id] })
      toast.success('Worker profile saved')
      onClose()
    },
    onError: (err: any) =>
      toast.error(err?.response?.data?.detail ?? 'Failed to save'),
  })

  const toggleSkill = (name: string) => {
    setRejectedSkills((prev) => {
      const next = new Set(prev)
      if (next.has(name)) next.delete(name)
      else next.add(name)
      return next
    })
  }

  const toggleCategory = (name: string) => {
    setRejectedCategories((prev) => {
      const next = new Set(prev)
      if (next.has(name)) next.delete(name)
      else next.add(name)
      return next
    })
  }

  return (
    <Sheet open={!!user} onOpenChange={(v) => !v && onClose()}>
      <SheetContent className="w-[28rem] sm:max-w-[28rem]">
        <SheetHeader>
          <SheetTitle>Worker profile — {user?.username}</SheetTitle>
        </SheetHeader>

        <div className="mt-4 space-y-5 overflow-y-auto">
          <div className="space-y-2">
            <Label htmlFor="bio">Bio / Skills description</Label>
            <Textarea
              id="bio"
              rows={6}
              value={bio}
              onChange={(e) => setBio(e.target.value)}
              placeholder='e.g. "Senior Python developer. Strong FastAPI, PostgreSQL, Kubernetes. 8 yrs experience."'
            />
            <p className="text-[11px] text-muted-foreground">
              The bio is encoded into a semantic embedding and per-category proficiency
              scores are extracted — both feed directly into the assignment engine.
            </p>
          </div>

          {/* Skill bubbles */}
          <div className="space-y-2">
            <div className="flex items-center justify-between">
              <Label className="text-sm">Detected skills</Label>
              <span className="inline-flex items-center gap-1 text-[11px] text-muted-foreground">
                {extracting ? (
                  <>
                    <Loader2 className="h-3 w-3 animate-spin" /> Extracting…
                  </>
                ) : (
                  <>
                    <Wand2 className="h-3 w-3" /> Auto-updates as you type
                  </>
                )}
              </span>
            </div>

            {!suggestion?.skills?.length && !extracting && (
              <p className="text-xs text-muted-foreground">
                Skills extracted from your bio will appear here.
              </p>
            )}

            <div className="flex flex-wrap gap-1.5">
              {suggestion?.skills?.map((name) => (
                <BubbleChip
                  key={name}
                  label={name}
                  state={rejectedSkills.has(name) ? 'rejected' : 'accepted'}
                  onClick={() => toggleSkill(name)}
                />
              ))}
            </div>
          </div>

          {/* Category proficiency chips — these are what actually get saved */}
          {!!suggestion?.category_proficiencies?.length && (
            <div className="space-y-2">
              <div className="space-y-0.5">
                <Label className="text-sm">Category proficiency scores</Label>
                <p className="text-[11px] text-muted-foreground">
                  These will be written to the worker's profile on save. Click to reject any
                  that look wrong.
                </p>
              </div>
              <div className="flex flex-wrap gap-1.5">
                {suggestion.category_proficiencies.map((cp) => (
                  <BubbleChip
                    key={cp.category}
                    label={`${cp.category} ${Math.round(cp.proficiency * 100)}%`}
                    state={rejectedCategories.has(cp.category) ? 'rejected' : 'accepted'}
                    onClick={() => toggleCategory(cp.category)}
                  />
                ))}
              </div>
            </div>
          )}

          {suggestion?.primary_category && (
            <div className="space-y-1">
              <Label className="text-xs uppercase tracking-wide text-muted-foreground">
                Primary category
              </Label>
              <div>
                <BubbleChip
                  label={suggestion.primary_category}
                  state="accepted"
                  onClick={() => {}}
                  disabled
                />
              </div>
            </div>
          )}

          {suggestion?.seniority_hint && (
            <div className="space-y-1">
              <Label className="text-xs uppercase tracking-wide text-muted-foreground">
                Detected seniority
              </Label>
              <div>
                <BubbleChip
                  label={suggestion.seniority_hint}
                  state="accepted"
                  onClick={() => {}}
                  disabled
                />
              </div>
            </div>
          )}
        </div>

        <SheetFooter className="mt-6">
          <Button variant="outline" onClick={onClose}>
            Cancel
          </Button>
          <Button disabled={save.isPending} onClick={() => save.mutate()}>
            {save.isPending && <Loader2 className="h-4 w-4 animate-spin" />}
            Save
          </Button>
        </SheetFooter>
      </SheetContent>
    </Sheet>
  )
}
