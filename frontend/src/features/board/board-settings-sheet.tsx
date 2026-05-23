/**
 * Board settings sheet — gear button in board header opens this.
 *
 * Sections:
 *   1. Recommendations — confidence threshold for auto-accept (localStorage, per project)
 *   2. Categories       — list all global categories; admins can delete
 */
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { Trash2 } from 'lucide-react'
import { toast } from 'sonner'

import { categoriesApi } from '@/api/categories'
import { Button } from '@/components/ui/button'
import { Label } from '@/components/ui/label'
import { Separator } from '@/components/ui/separator'
import {
  Sheet,
  SheetContent,
  SheetHeader,
  SheetTitle,
} from '@/components/ui/sheet'
import { Skeleton } from '@/components/ui/skeleton'
import { useRecommenderSettings } from '@/hooks/use-recommender-settings'
import { useAuthStore } from '@/store/auth-store'

interface Props {
  open: boolean
  onOpenChange: (open: boolean) => void
  projectId: number
}

export function BoardSettingsSheet({ open, onOpenChange, projectId }: Props) {
  const qc = useQueryClient()
  const user = useAuthStore((s) => s.user)
  const canManageCategories = !!user?.org_role?.permissions?.includes('categories:manage')

  const { settings, update } = useRecommenderSettings(projectId)

  const { data: categories, isPending } = useQuery({
    queryKey: ['categories'],
    queryFn: categoriesApi.list,
    staleTime: 60_000 * 10,
    enabled: open,
  })

  const deleteCat = useMutation({
    mutationFn: (id: number) => categoriesApi.delete(id),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['categories'] })
      toast.success('Category deleted')
    },
    onError: (err: any) =>
      toast.error(err?.response?.data?.detail ?? 'Failed to delete category'),
  })

  return (
    <Sheet open={open} onOpenChange={onOpenChange}>
      <SheetContent className="w-80 sm:max-w-sm">
        <SheetHeader>
          <SheetTitle>Board settings</SheetTitle>
        </SheetHeader>

        <div className="mt-6 space-y-6">
          {/* ── Recommendations ── */}
          <section className="space-y-3">
            <h3 className="text-sm font-medium">Recommendations</h3>
            <div className="space-y-2">
              <div className="flex items-center justify-between text-xs">
                <Label>Auto-accept confidence threshold</Label>
                <span className="tabular-nums font-medium">
                  {Math.round(settings.threshold * 100)}%
                </span>
              </div>
              <input
                type="range"
                min={0}
                max={1}
                step={0.05}
                value={settings.threshold}
                onChange={(e) => update({ threshold: Number(e.target.value) })}
                className="w-full accent-primary"
                aria-label="Auto-accept confidence threshold"
              />
              <p className="text-[11px] text-muted-foreground">
                Suggestions above this confidence are auto-applied when Auto-accept is on.
              </p>
            </div>
          </section>

          <Separator />

          {/* ── Categories ── */}
          <section className="space-y-3">
            <div className="flex items-center justify-between">
              <h3 className="text-sm font-medium">Categories</h3>
              {!canManageCategories && (
                <span className="text-[11px] text-muted-foreground">Admin only</span>
              )}
            </div>

            {isPending ? (
              <div className="space-y-2">
                {Array.from({ length: 4 }).map((_, i) => (
                  <Skeleton key={i} className="h-8 w-full" />
                ))}
              </div>
            ) : (
              <ul className="space-y-1">
                {categories?.map((c) => (
                  <li
                    key={c.id}
                    className="flex items-center justify-between rounded-md px-2 py-1.5 text-sm hover:bg-muted/40"
                  >
                    <span className="font-medium">{c.name}</span>
                    {canManageCategories && (
                      <Button
                        variant="ghost"
                        size="icon"
                        className="h-7 w-7 text-muted-foreground hover:text-destructive hover:bg-destructive/10"
                        disabled={deleteCat.isPending}
                        onClick={() => {
                          if (
                            confirm(
                              `Delete category "${c.name}"? This will remove it from all tickets.`,
                            )
                          ) {
                            deleteCat.mutate(c.id)
                          }
                        }}
                      >
                        <Trash2 className="h-3.5 w-3.5" />
                      </Button>
                    )}
                  </li>
                ))}
                {categories?.length === 0 && (
                  <p className="text-xs text-muted-foreground">No categories yet.</p>
                )}
              </ul>
            )}
          </section>
        </div>
      </SheetContent>
    </Sheet>
  )
}
