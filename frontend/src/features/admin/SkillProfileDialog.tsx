import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { useEffect, useState } from 'react'
import { toast } from 'sonner'

import { adminApi } from '@/api/admin'
import { categoriesApi } from '@/api/categories'
import { Button } from '@/components/ui/button'
import { Sheet, SheetContent, SheetFooter, SheetHeader, SheetTitle } from '@/components/ui/sheet'
import type { SkillProfile, UserDetail } from '@/types'

interface Props {
  user: UserDetail | null
  onClose: () => void
}

export function SkillProfileDialog({ user, onClose }: Props) {
  const qc = useQueryClient()
  const [skills, setSkills] = useState<Record<number, number>>({})

  const { data: categories } = useQuery({
    queryKey: ['categories'],
    queryFn: categoriesApi.list,
  })

  const { data: existing } = useQuery({
    queryKey: ['admin', 'user', user?.id, 'skills'],
    queryFn: () => adminApi.getSkills(user!.id),
    enabled: !!user,
  })

  useEffect(() => {
    if (existing) {
      const map: Record<number, number> = {}
      existing.forEach((s: SkillProfile) => {
        map[s.category_id] = s.proficiency
      })
      setSkills(map)
    }
  }, [existing])

  const mutation = useMutation({
    mutationFn: (entries: SkillProfile[]) => adminApi.setSkills(user!.id, entries),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['admin', 'users'] })
      toast.success('Skills saved')
      onClose()
    },
    onError: () => toast.error('Failed to save skills'),
  })

  const handleSave = () => {
    const entries: SkillProfile[] = Object.entries(skills).map(([id, proficiency]) => ({
      category_id: Number(id),
      proficiency,
    }))
    mutation.mutate(entries)
  }

  return (
    <Sheet open={!!user} onOpenChange={(v) => !v && onClose()}>
      <SheetContent className="w-96">
        <SheetHeader>
          <SheetTitle>Skills — {user?.username}</SheetTitle>
        </SheetHeader>
        <div className="mt-4 space-y-4 overflow-y-auto">
          {categories?.map((cat) => (
            <div key={cat.id}>
              <div className="flex justify-between text-sm">
                <span className="font-medium">{cat.name}</span>
                <span className="text-muted-foreground">
                  {((skills[cat.id] ?? 0) * 100).toFixed(0)}%
                </span>
              </div>
              <input
                type="range"
                min={0}
                max={1}
                step={0.05}
                value={skills[cat.id] ?? 0}
                onChange={(e) =>
                  setSkills((prev) => ({ ...prev, [cat.id]: parseFloat(e.target.value) }))
                }
                className="mt-1 w-full accent-primary"
              />
            </div>
          ))}
        </div>
        <SheetFooter className="mt-6">
          <Button variant="outline" onClick={onClose}>
            Cancel
          </Button>
          <Button onClick={handleSave} disabled={mutation.isPending}>
            Save
          </Button>
        </SheetFooter>
      </SheetContent>
    </Sheet>
  )
}
