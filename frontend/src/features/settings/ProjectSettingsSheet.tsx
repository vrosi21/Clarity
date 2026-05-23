import {
  Sheet,
  SheetContent,
  SheetHeader,
  SheetTitle,
} from '@/components/ui/sheet'

import { ProjectSettingsPanel } from './ProjectSettingsPanel'

interface Props {
  open: boolean
  onOpenChange: (open: boolean) => void
  projectId: number
  projectName?: string
}

export function ProjectSettingsSheet({ open, onOpenChange, projectId, projectName }: Props) {
  return (
    <Sheet open={open} onOpenChange={onOpenChange}>
      <SheetContent className="w-[600px] sm:max-w-[600px] overflow-y-auto">
        <SheetHeader>
          <SheetTitle>
            {projectName ? `${projectName} — Settings` : 'Project Settings'}
          </SheetTitle>
        </SheetHeader>
        <div className="mt-5">
          <ProjectSettingsPanel projectId={projectId} compact />
        </div>
      </SheetContent>
    </Sheet>
  )
}
