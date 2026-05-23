import { useParams } from 'react-router-dom'

import { Skeleton } from '@/components/ui/skeleton'
import { useQuery } from '@tanstack/react-query'
import { projectsApi } from '@/api/projects'

import { ProjectSettingsPanel } from './ProjectSettingsPanel'

export function ProjectSettingsPage() {
  const { projectId } = useParams<{ projectId: string }>()
  const id = Number(projectId)

  const { data: project } = useQuery({
    queryKey: ['project', id],
    queryFn: () => projectsApi.get(id),
    enabled: !Number.isNaN(id),
  })

  if (Number.isNaN(id)) {
    return <div className="p-8 text-sm text-muted-foreground">Invalid project ID.</div>
  }

  return (
    <div className="h-full overflow-y-auto">
      <div className="mx-auto max-w-4xl px-6 py-8">
        <h1 className="text-2xl font-semibold mb-6">
          {project?.name ?? <Skeleton className="inline-block h-6 w-40" />} — Settings
        </h1>
        <ProjectSettingsPanel projectId={id} />
      </div>
    </div>
  )
}
