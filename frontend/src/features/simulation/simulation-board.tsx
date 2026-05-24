import { AnimatePresence, LayoutGroup, motion } from 'framer-motion'

import { Avatar, AvatarFallback } from '@/components/ui/avatar'
import { Badge } from '@/components/ui/badge'
import { cn, getInitials } from '@/lib/utils'
import { SIM_STAGES, type SimBoardEntry, type SimStage } from '@/store/simulation-store'

const STAGE_STYLES: Record<SimStage, string> = {
  BACKLOG: 'border-l-border bg-card/30',
  ASSIGNED: 'border-l-blue-500/50 bg-blue-500/[0.04]',
  IN_PROGRESS: 'border-l-amber-500/50 bg-amber-500/[0.04]',
  BLOCKED: 'border-l-red-500/50 bg-red-500/[0.05]',
  IN_REVIEW: 'border-l-purple-500/50 bg-purple-500/[0.04]',
  DONE: 'border-l-emerald-500/50 bg-emerald-500/[0.04]',
}

interface Props {
  board: Map<number, SimBoardEntry>
}

export function SimulationBoard({ board }: Props) {
  const entries = Array.from(board.values())
  const byStage = new Map<SimStage, SimBoardEntry[]>()
  for (const s of SIM_STAGES) byStage.set(s, [])
  for (const e of entries) byStage.get(e.stage)!.push(e)

  return (
    <div className="h-full overflow-auto p-4">
      <LayoutGroup>
        <div className="flex min-h-full gap-3">
          {SIM_STAGES.map((stage) => {
            const items = byStage.get(stage) ?? []
            return (
              <div
                key={stage}
                className={cn(
                  'flex w-64 shrink-0 flex-col rounded-lg border border-l-4 border-border',
                  STAGE_STYLES[stage],
                )}
              >
                <div className="flex items-center justify-between rounded-t-lg border-b border-border/60 px-3 py-2">
                  <span className="text-xs font-semibold uppercase tracking-wide">{stage}</span>
                  <Badge variant="secondary" className="h-5 px-1.5 text-[10px]">
                    {items.length}
                  </Badge>
                </div>
                <div className="flex-1 space-y-2 p-2">
                  <AnimatePresence initial={false}>
                    {items.map((entry) => (
                      <motion.div
                        key={entry.ticket.id}
                        layoutId={`sim-ticket-${entry.ticket.id}`}
                        layout
                        transition={{ duration: 0.3, type: 'tween' }}
                        initial={{ opacity: 0, y: 4 }}
                        animate={{ opacity: 1, y: 0 }}
                        exit={{ opacity: 0 }}
                        style={{ position: 'relative', zIndex: 30 }}
                        className="rounded-md border border-border bg-card p-2.5 shadow-sm"
                      >
                        <p className="line-clamp-2 text-xs font-medium leading-tight">
                          {entry.ticket.title}
                        </p>
                        <div className="mt-2 flex items-center justify-between gap-2">
                          <div className="flex flex-wrap items-center gap-1">
                            {entry.ticket.category_name && (
                              <Badge
                                variant="outline"
                                className="h-4 px-1 text-[9px]"
                                style={
                                  entry.ticket.category_color
                                    ? {
                                        borderColor: entry.ticket.category_color,
                                        color: entry.ticket.category_color,
                                        backgroundColor: `${entry.ticket.category_color}1a`,
                                      }
                                    : undefined
                                }
                              >
                                {entry.ticket.category_name}
                              </Badge>
                            )}
                            <ComplexityDots value={entry.ticket.complexity} />
                            {entry.ticket.estimated_minutes && (
                              <span className="text-[9px] text-muted-foreground">
                                {Math.round(entry.ticket.estimated_minutes / 60)}h
                              </span>
                            )}
                          </div>
                          {entry.worker_name && (
                            <Avatar className="h-5 w-5">
                              <AvatarFallback className="text-[8px]">
                                {getInitials(entry.worker_name)}
                              </AvatarFallback>
                            </Avatar>
                          )}
                        </div>
                      </motion.div>
                    ))}
                  </AnimatePresence>
                  {items.length === 0 && (
                    <div className="rounded border border-dashed border-border/40 p-3 text-center text-[10px] text-muted-foreground">
                      empty
                    </div>
                  )}
                </div>
              </div>
            )
          })}
        </div>
      </LayoutGroup>
    </div>
  )
}

function ComplexityDots({ value }: { value: number }) {
  return (
    <span className="flex items-center gap-[1px]" title={`Complexity ${value}/5`}>
      {[1, 2, 3, 4, 5].map((i) => (
        <span
          key={i}
          className={cn(
            'h-1 w-1 rounded-full',
            i <= value ? 'bg-foreground/70' : 'bg-foreground/15',
          )}
        />
      ))}
    </span>
  )
}
