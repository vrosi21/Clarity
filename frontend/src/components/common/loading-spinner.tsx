import { Loader2 } from 'lucide-react'

import { cn } from '@/lib/utils'

export function LoadingSpinner({ className }: { className?: string }) {
  return (
    <div className={cn('flex h-full w-full items-center justify-center p-8', className)}>
      <Loader2 className="h-6 w-6 animate-spin text-muted-foreground" />
    </div>
  )
}
