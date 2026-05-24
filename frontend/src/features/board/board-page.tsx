import { useQuery } from '@tanstack/react-query'
import { ChevronLeft, Settings2 } from 'lucide-react'
import { useEffect, useMemo, useState } from 'react'
import { Link, useParams } from 'react-router-dom'

import { projectsApi } from '@/api/projects'
import { stagesApi } from '@/api/stages'
import { ticketsApi } from '@/api/tickets'
import { Button } from '@/components/ui/button'
import { Skeleton } from '@/components/ui/skeleton'
import { BoardColumn } from '@/features/board/board-column'
import { GenerationOverlay } from '@/features/board/generation-overlay'
import { ProjectSettingsSheet } from '@/features/settings/ProjectSettingsSheet'
import { CreateTicketDialog } from '@/features/board/create-ticket-dialog'
import { TicketSheet } from '@/features/ticket/ticket-sheet'
import type { Ticket } from '@/types'

export function BoardPage() {
  const { projectId } = useParams<{ projectId: string }>()
  const id = Number(projectId)

  const [createTicketStageId, setCreateTicketStageId] = useState<number | null>(null)
  const [openTicketId, setOpenTicketId] = useState<number | null>(null)
  const [settingsOpen, setSettingsOpen] = useState(false)

  const { data: project } = useQuery({
    queryKey: ['project', id],
    queryFn: () => projectsApi.get(id),
    enabled: !Number.isNaN(id),
  })
  const {
    data: stages,
    isPending: stagesPending,
    isError: stagesError,
  } = useQuery({
    queryKey: ['stages', id],
    queryFn: () => stagesApi.list(id),
    enabled: !Number.isNaN(id),
  })
  const { data: tickets } = useQuery({
    queryKey: ['tickets', id],
    queryFn: () => ticketsApi.list(id),
    enabled: !Number.isNaN(id),
  })

  useEffect(() => {
    document.title = project ? `${project.name} — Board — Clarity` : 'Board — Clarity'
  }, [project])

  const ticketsByStage = useMemo(() => {
    const map = new Map<number, Ticket[]>()
    if (!tickets) return map
    for (const t of tickets) {
      const arr = map.get(t.stage_id) ?? []
      arr.push(t)
      map.set(t.stage_id, arr)
    }
    return map
  }, [tickets])

  if (Number.isNaN(id)) {
    return <div className="p-8 text-sm text-muted-foreground">Invalid project ID.</div>
  }

  return (
    <div className="flex h-full flex-col overflow-hidden">
      {/* Top bar */}
      <div className="flex h-14 shrink-0 items-center justify-between gap-3 border-b border-border bg-background px-6">
        <div className="min-w-0">
          <h1 className="truncate text-lg font-semibold">
            {project?.name ?? <Skeleton className="h-5 w-40" />}
          </h1>
          {project?.description && (
            <p className="truncate text-xs text-muted-foreground">{project.description}</p>
          )}
        </div>
        <div className="flex items-center gap-1">
          <Button variant="ghost" size="icon" onClick={() => setSettingsOpen(true)} title="Board settings">
            <Settings2 className="h-4 w-4" />
          </Button>
          <Button variant="ghost" size="sm" asChild>
            <Link to={`/projects/${id}`}>
              <ChevronLeft className="h-4 w-4" />
              Dashboard
            </Link>
          </Button>
        </div>
      </div>

      {/* Board */}
      <div className="clarity-scrollbar relative flex-1 overflow-x-auto overflow-y-hidden bg-muted/20">
        <GenerationOverlay projectId={id} />
        {stagesError && (
          <div className="p-8 text-center text-sm text-muted-foreground">
            Couldn't load board. Refresh the page.
          </div>
        )}
        {stagesPending && (
          <div className="flex h-full gap-4 p-6">
            {Array.from({ length: 5 }).map((_, i) => (
              <Skeleton key={i} className="h-full w-72" />
            ))}
          </div>
        )}
        {stages && (
          <div className="flex h-full gap-4 p-6">
            {stages.map((s) => (
              <BoardColumn
                key={s.id}
                projectId={id}
                stage={s}
                allStages={stages}
                tickets={ticketsByStage.get(s.id) ?? []}
                onCreateTicket={() => setCreateTicketStageId(s.id)}
                onTicketClick={(t) => setOpenTicketId(t.id)}
              />
            ))}
          </div>
        )}
      </div>

      {createTicketStageId !== null && (
        <CreateTicketDialog
          open={createTicketStageId !== null}
          onOpenChange={(open) => !open && setCreateTicketStageId(null)}
          projectId={id}
          defaultStageId={createTicketStageId}
        />
      )}

      <TicketSheet
        projectId={id}
        ticketId={openTicketId}
        onOpenChange={(open) => !open && setOpenTicketId(null)}
        stages={stages ?? []}
      />

      <ProjectSettingsSheet
        open={settingsOpen}
        onOpenChange={setSettingsOpen}
        projectId={id}
        projectName={project?.name}
      />
    </div>
  )
}
