import { useQuery } from '@tanstack/react-query'
import { ArrowRight, Plus, Sparkles } from 'lucide-react'
import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'

import { projectsApi } from '@/api/projects'
import { Button } from '@/components/ui/button'
import {
  Card,
  CardContent,
  CardDescription,
  CardFooter,
  CardHeader,
  CardTitle,
} from '@/components/ui/card'
import { Skeleton } from '@/components/ui/skeleton'
import { CreateProjectDialog } from '@/features/projects/create-project-dialog'
import { formatDate } from '@/lib/utils'

export function ProjectsPage() {
  const [createOpen, setCreateOpen] = useState(false)
  const { data: projects, isPending, isError } = useQuery({
    queryKey: ['projects'],
    queryFn: projectsApi.list,
  })

  useEffect(() => {
    document.title = 'Projects — Clarity'
  }, [])

  return (
    <div className="h-full overflow-y-auto">
      <div className="mx-auto max-w-6xl px-6 py-8">
        <div className="mb-8 flex items-center justify-between gap-4">
          <div>
            <h1 className="text-2xl font-semibold tracking-tight">Projects</h1>
            <p className="text-sm text-muted-foreground">
              {projects?.length ?? 0} project{projects?.length === 1 ? '' : 's'}
            </p>
          </div>
          <Button onClick={() => setCreateOpen(true)}>
            <Plus className="h-4 w-4" />
            New project
          </Button>
        </div>

        {isPending && (
          <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
            {Array.from({ length: 6 }).map((_, i) => (
              <Skeleton key={i} className="h-44 w-full" />
            ))}
          </div>
        )}

        {isError && (
          <Card>
            <CardContent className="py-8 text-center text-sm text-muted-foreground">
              Couldn't load projects. Make sure the API is running and refresh the page.
            </CardContent>
          </Card>
        )}

        {!isPending && !isError && projects?.length === 0 && (
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

        {!isPending && projects && projects.length > 0 && (
          <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
            {projects.map((p) => (
              <Card key={p.id} className="flex flex-col transition-colors hover:border-accent/50">
                <CardHeader>
                  <CardTitle className="truncate">{p.name}</CardTitle>
                  <CardDescription>Created {formatDate(p.created_at)}</CardDescription>
                </CardHeader>
                <CardContent className="flex-1">
                  <p className="line-clamp-3 text-sm text-muted-foreground">
                    {p.description || <em className="text-muted-foreground/70">No description</em>}
                  </p>
                </CardContent>
                <CardFooter className="justify-end pt-0">
                  <Button variant="ghost" size="sm" asChild>
                    <Link to={`/projects/${p.id}`}>
                      Open board <ArrowRight className="h-4 w-4" />
                    </Link>
                  </Button>
                </CardFooter>
              </Card>
            ))}
          </div>
        )}
      </div>

      <CreateProjectDialog open={createOpen} onOpenChange={setCreateOpen} />
    </div>
  )
}
