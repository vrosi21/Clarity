import { useQuery } from '@tanstack/react-query'
import { ArrowRight, FolderKanban, Plus, Search, Sparkles, X } from 'lucide-react'
import { useEffect, useMemo, useState } from 'react'
import { Link } from 'react-router-dom'

import { projectsApi } from '@/api/projects'
import { Button } from '@/components/ui/button'
import { Card, CardContent } from '@/components/ui/card'
import { Input } from '@/components/ui/input'
import { Skeleton } from '@/components/ui/skeleton'
import { CreateProjectDialog } from '@/features/projects/create-project-dialog'
import { cn, formatDate } from '@/lib/utils'
import type { Project } from '@/types'

// Deterministic accent tint per project so the grid reads as distinct cards.
const TINTS = [
  'bg-violet-500/15 text-violet-500',
  'bg-sky-500/15 text-sky-500',
  'bg-emerald-500/15 text-emerald-500',
  'bg-amber-500/15 text-amber-500',
  'bg-rose-500/15 text-rose-500',
  'bg-cyan-500/15 text-cyan-500',
]

function tintFor(id: number) {
  return TINTS[id % TINTS.length]
}

function ProjectCard({ project }: { project: Project }) {
  const initials = project.name.slice(0, 2).toUpperCase()
  return (
    <Link
      to={`/projects/${project.id}`}
      className="group flex flex-col rounded-xl border border-border bg-card p-5 transition-all hover:border-accent/50 hover:shadow-sm"
    >
      <div className="flex items-start gap-3">
        <div
          className={cn(
            'flex h-10 w-10 shrink-0 items-center justify-center rounded-lg text-sm font-semibold',
            tintFor(project.id),
          )}
        >
          {initials}
        </div>
        <div className="min-w-0 flex-1">
          <h3 className="truncate font-semibold leading-tight">{project.name}</h3>
          <p className="mt-0.5 text-xs text-muted-foreground">
            Created {formatDate(project.created_at)}
          </p>
        </div>
      </div>
      <p className="mt-3 line-clamp-2 flex-1 text-sm text-muted-foreground">
        {project.description || <em className="text-muted-foreground/60">No description</em>}
      </p>
      <div className="mt-4 flex items-center gap-1 text-sm font-medium text-accent opacity-0 transition-opacity group-hover:opacity-100">
        Open board <ArrowRight className="h-4 w-4" />
      </div>
    </Link>
  )
}

export function ProjectsPage() {
  const [createOpen, setCreateOpen] = useState(false)
  const [query, setQuery] = useState('')
  const { data: projects, isPending, isError } = useQuery({
    queryKey: ['projects'],
    queryFn: projectsApi.list,
  })

  useEffect(() => {
    document.title = 'Projects — Clarity'
  }, [])

  const filtered = useMemo(() => {
    if (!projects) return []
    const q = query.trim().toLowerCase()
    if (!q) return projects
    return projects.filter(
      (p) =>
        p.name.toLowerCase().includes(q) ||
        (p.description ?? '').toLowerCase().includes(q),
    )
  }, [projects, query])

  const total = projects?.length ?? 0

  return (
    <div className="h-full overflow-y-auto">
      <div className="mx-auto max-w-6xl px-6 py-8">
        {/* Header */}
        <div className="mb-6 flex flex-wrap items-center justify-between gap-4">
          <div>
            <h1 className="text-2xl font-semibold tracking-tight">Projects</h1>
            <p className="text-sm text-muted-foreground">
              {total} project{total === 1 ? '' : 's'}
            </p>
          </div>
          <Button onClick={() => setCreateOpen(true)}>
            <Plus className="h-4 w-4" />
            New project
          </Button>
        </div>

        {/* Search */}
        {total > 0 && (
          <div className="relative mb-6 max-w-sm">
            <Search className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
            <Input
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              placeholder="Search projects…"
              className="pl-9 pr-9"
            />
            {query && (
              <button
                onClick={() => setQuery('')}
                aria-label="Clear search"
                className="absolute right-2 top-1/2 -translate-y-1/2 rounded-md p-1 text-muted-foreground hover:bg-accent/10 hover:text-foreground"
              >
                <X className="h-3.5 w-3.5" />
              </button>
            )}
          </div>
        )}

        {/* Loading */}
        {isPending && (
          <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
            {Array.from({ length: 6 }).map((_, i) => (
              <Skeleton key={i} className="h-40 w-full rounded-xl" />
            ))}
          </div>
        )}

        {/* Error */}
        {isError && (
          <Card>
            <CardContent className="py-8 text-center text-sm text-muted-foreground">
              Couldn't load projects. Make sure the API is running and refresh the page.
            </CardContent>
          </Card>
        )}

        {/* Empty (no projects at all) */}
        {!isPending && !isError && total === 0 && (
          <Card className="border-dashed">
            <CardContent className="flex flex-col items-center gap-4 py-16 text-center">
              <div className="flex h-12 w-12 items-center justify-center rounded-full bg-accent/15">
                <Sparkles className="h-5 w-5 text-accent" />
              </div>
              <div>
                <h3 className="mb-1 font-semibold">No projects yet</h3>
                <p className="text-sm text-muted-foreground">
                  Create one to get a Kanban board with default stages.
                </p>
              </div>
              <Button onClick={() => setCreateOpen(true)}>
                <Plus className="h-4 w-4" />
                Create your first project
              </Button>
            </CardContent>
          </Card>
        )}

        {/* No search results */}
        {!isPending && total > 0 && filtered.length === 0 && (
          <div className="flex flex-col items-center gap-3 py-16 text-center">
            <div className="flex h-12 w-12 items-center justify-center rounded-full bg-muted">
              <FolderKanban className="h-5 w-5 text-muted-foreground" />
            </div>
            <p className="text-sm text-muted-foreground">
              No projects match “{query}”.
            </p>
            <Button variant="ghost" size="sm" onClick={() => setQuery('')}>
              Clear search
            </Button>
          </div>
        )}

        {/* Grid */}
        {!isPending && filtered.length > 0 && (
          <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
            {filtered.map((p) => (
              <ProjectCard key={p.id} project={p} />
            ))}
          </div>
        )}
      </div>

      <CreateProjectDialog open={createOpen} onOpenChange={setCreateOpen} />
    </div>
  )
}
