import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { Loader2, Plus, Tag, Trash2 } from 'lucide-react'
import { useState } from 'react'
import { toast } from 'sonner'

import { categoriesApi } from '@/api/categories'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Textarea } from '@/components/ui/textarea'
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
  AlertDialogTrigger,
} from '@/components/ui/alert-dialog'
import { getApiErrorMessage } from '@/lib/utils'
import type { Category } from '@/types'

export function CategoriesPage() {
  const queryClient = useQueryClient()
  const [name, setName] = useState('')
  const [description, setDescription] = useState('')

  const { data: categories = [], isLoading } = useQuery<Category[]>({
    queryKey: ['categories'],
    queryFn: categoriesApi.list,
    staleTime: 30_000,
  })

  const createMutation = useMutation({
    mutationFn: () => categoriesApi.create(name.trim(), description.trim()),
    onSuccess: (cat) => {
      queryClient.invalidateQueries({ queryKey: ['categories'] })
      toast.success(`Category "${cat.name}" created`)
      setName('')
      setDescription('')
    },
    onError: (err) => toast.error(getApiErrorMessage(err)),
  })

  const deleteMutation = useMutation({
    mutationFn: (id: number) => categoriesApi.delete(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['categories'] })
      toast.success('Category deleted')
    },
    onError: (err) => toast.error(getApiErrorMessage(err)),
  })

  return (
    <div className="max-w-2xl space-y-8">
      <div>
        <h1 className="text-2xl font-semibold">Categories</h1>
        <p className="mt-1 text-sm text-muted-foreground">
          Global task categories used across all projects for skill matching and RL assignment.
          Canonical categories are pre-seeded; custom categories can be added here.
        </p>
      </div>

      {/* Create form */}
      <div className="rounded-lg border border-border p-4 space-y-4">
        <h2 className="text-sm font-semibold">New category</h2>
        <div className="space-y-3">
          <div className="space-y-1.5">
            <Label htmlFor="cat-name">Name</Label>
            <Input
              id="cat-name"
              placeholder="e.g. blockchain, legal, hr"
              value={name}
              onChange={(e) => setName(e.target.value.toLowerCase())}
              maxLength={64}
            />
            <p className="text-xs text-muted-foreground">
              Lowercase only. Will be used in NLP matching and RL state vectors.
            </p>
          </div>
          <div className="space-y-1.5">
            <Label htmlFor="cat-desc">Description <span className="text-muted-foreground font-normal">(optional)</span></Label>
            <Textarea
              id="cat-desc"
              placeholder="Describe what tasks belong to this category — improves NLP matching quality."
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              rows={2}
              maxLength={255}
            />
          </div>
          <Button
            onClick={() => createMutation.mutate()}
            disabled={!name.trim() || createMutation.isPending}
            size="sm"
          >
            {createMutation.isPending
              ? <Loader2 className="h-4 w-4 animate-spin" />
              : <Plus className="h-4 w-4" />
            }
            Create category
          </Button>
        </div>
      </div>

      {/* Category list */}
      <div className="space-y-2">
        <h2 className="text-sm font-semibold text-muted-foreground uppercase tracking-wide">
          All categories ({categories.length})
        </h2>
        {isLoading && (
          <div className="flex items-center gap-2 text-sm text-muted-foreground py-4">
            <Loader2 className="h-4 w-4 animate-spin" /> Loading…
          </div>
        )}
        {!isLoading && categories.length === 0 && (
          <p className="text-sm text-muted-foreground py-4">No categories yet.</p>
        )}
        <ul className="divide-y divide-border rounded-lg border border-border">
          {categories.map((cat) => (
            <CategoryRow
              key={cat.id}
              category={cat}
              onDelete={() => deleteMutation.mutate(cat.id)}
              isDeleting={deleteMutation.isPending && deleteMutation.variables === cat.id}
            />
          ))}
        </ul>
      </div>
    </div>
  )
}

function CategoryRow({
  category,
  onDelete,
  isDeleting,
}: {
  category: Category
  onDelete: () => void
  isDeleting: boolean
}) {
  return (
    <li className="flex items-center gap-3 px-4 py-3">
      <Tag className="h-4 w-4 shrink-0 text-muted-foreground" />
      <div className="flex-1 min-w-0">
        <span className="text-sm font-medium">{category.name}</span>
        {category.description && (
          <p className="text-xs text-muted-foreground truncate">{category.description}</p>
        )}
      </div>
      <AlertDialog>
        <AlertDialogTrigger asChild>
          <Button variant="ghost" size="icon" className="h-7 w-7 shrink-0 text-muted-foreground hover:text-destructive">
            {isDeleting
              ? <Loader2 className="h-3.5 w-3.5 animate-spin" />
              : <Trash2 className="h-3.5 w-3.5" />
            }
          </Button>
        </AlertDialogTrigger>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>Delete "{category.name}"?</AlertDialogTitle>
            <AlertDialogDescription>
              This removes the category globally. Tickets already assigned to it will retain the
              reference, but it will no longer appear in dropdowns or NLP matching.
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel>Cancel</AlertDialogCancel>
            <AlertDialogAction
              onClick={onDelete}
              className="bg-destructive text-destructive-foreground hover:bg-destructive/90"
            >
              Delete
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </li>
  )
}
