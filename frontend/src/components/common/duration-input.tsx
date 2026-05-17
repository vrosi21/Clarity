import { useEffect, useState } from 'react'

import { Input } from '@/components/ui/input'
import { cn, formatDuration, parseDuration } from '@/lib/utils'

interface Props {
  id?: string
  value: number | null
  onChange: (minutes: number | null) => void
  placeholder?: string
  className?: string
}

export function DurationInput({ id, value, onChange, placeholder = 'e.g. 1d 2h 30m', className }: Props) {
  const [text, setText] = useState(() => formatDuration(value))
  const [focused, setFocused] = useState(false)
  const [invalid, setInvalid] = useState(false)

  // Sync when the external value changes (e.g. after a successful save)
  useEffect(() => {
    if (!focused) setText(formatDuration(value))
  }, [value, focused])

  const commit = () => {
    setFocused(false)
    const trimmed = text.trim()
    if (!trimmed) {
      onChange(null)
      setText('')
      return
    }
    const parsed = parseDuration(trimmed)
    if (parsed !== null) {
      onChange(parsed)
      setText(formatDuration(parsed))
      setInvalid(false)
    } else {
      setInvalid(true)
      setTimeout(() => {
        setInvalid(false)
        setText(formatDuration(value))
      }, 900)
    }
  }

  return (
    <Input
      id={id}
      value={text}
      onChange={(e) => { setText(e.target.value); setInvalid(false) }}
      onFocus={() => setFocused(true)}
      onBlur={commit}
      onKeyDown={(e) => { if (e.key === 'Enter') e.currentTarget.blur() }}
      placeholder={placeholder}
      className={cn(invalid && 'border-destructive focus-visible:ring-destructive', className)}
    />
  )
}
