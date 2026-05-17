import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { Loader2, Send } from 'lucide-react'
import { useState } from 'react'
import { toast } from 'sonner'

import { commentsApi } from '@/api/comments'
import { Avatar, AvatarFallback } from '@/components/ui/avatar'
import { Button } from '@/components/ui/button'
import { Skeleton } from '@/components/ui/skeleton'
import { Textarea } from '@/components/ui/textarea'
import { formatRelative, getApiErrorMessage, getInitials } from '@/lib/utils'

interface Props {
  ticketId: number
}

export function CommentThread({ ticketId }: Props) {
  const [content, setContent] = useState('')
  const queryClient = useQueryClient()

  const { data: comments, isPending } = useQuery({
    queryKey: ['comments', ticketId],
    queryFn: () => commentsApi.list(ticketId),
  })

  const mutation = useMutation({
    mutationFn: () => commentsApi.create(ticketId, { content }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['comments', ticketId] })
      setContent('')
    },
    onError: (err) => toast.error(getApiErrorMessage(err)),
  })

  const onSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    if (!content.trim()) return
    mutation.mutate()
  }

  return (
    <div className="space-y-4">
      <h3 className="text-sm font-semibold">Comments</h3>

      {isPending && (
        <div className="space-y-3">
          <Skeleton className="h-12 w-full" />
          <Skeleton className="h-12 w-full" />
        </div>
      )}

      {!isPending && comments?.length === 0 && (
        <p className="text-sm text-muted-foreground">No comments yet.</p>
      )}

      <ul className="space-y-3">
        {comments?.map((c) => (
          <li key={c.id} className="flex gap-3">
            <Avatar className="h-7 w-7 shrink-0">
              <AvatarFallback className="text-[10px]">
                {c.username ? getInitials(c.username) : '?'}
              </AvatarFallback>
            </Avatar>
            <div className="flex-1 rounded-md border border-border bg-card/50 p-3">
              <div className="mb-1 flex items-center gap-2 text-xs text-muted-foreground">
                <span className="font-medium text-foreground">{c.username ?? 'Unknown'}</span>
                <span>•</span>
                <span>{formatRelative(c.created_at)}</span>
              </div>
              <p className="whitespace-pre-wrap text-sm">{c.content}</p>
            </div>
          </li>
        ))}
      </ul>

      <form onSubmit={onSubmit} className="space-y-2">
        <Textarea
          rows={3}
          value={content}
          onChange={(e) => setContent(e.target.value)}
          placeholder="Add a comment..."
        />
        <div className="flex justify-end">
          <Button type="submit" size="sm" disabled={mutation.isPending || !content.trim()}>
            {mutation.isPending ? <Loader2 className="h-4 w-4 animate-spin" /> : <Send className="h-4 w-4" />}
            Post
          </Button>
        </div>
      </form>
    </div>
  )
}
