import { clsx, type ClassValue } from 'clsx'
import { twMerge } from 'tailwind-merge'

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs))
}

export function getInitials(name: string): string {
  return name
    .split(/\s+/)
    .filter(Boolean)
    .slice(0, 2)
    .map((s) => s[0]?.toUpperCase() ?? '')
    .join('')
}

export function formatDate(iso: string): string {
  const d = new Date(iso)
  return d.toLocaleDateString(undefined, { month: 'short', day: 'numeric', year: 'numeric' })
}

export function formatRelative(iso: string): string {
  const ms = Date.now() - new Date(iso).getTime()
  const min = Math.floor(ms / 60_000)
  if (min < 1) return 'just now'
  if (min < 60) return `${min}m ago`
  const hrs = Math.floor(min / 60)
  if (hrs < 24) return `${hrs}h ago`
  const days = Math.floor(hrs / 24)
  if (days < 30) return `${days}d ago`
  return formatDate(iso)
}

// 1d = 8h = 480 min (one work day)
export function parseDuration(raw: string): number | null {
  const s = raw.trim()
  if (!s) return null
  // Plain integer → minutes
  if (/^\d+$/.test(s)) {
    const n = parseInt(s, 10)
    return n > 0 ? n : null
  }
  let total = 0
  let found = false
  const re = /(\d+(?:\.\d+)?)\s*([dhm])/gi
  let m: RegExpExecArray | null
  while ((m = re.exec(s)) !== null) {
    const n = parseFloat(m[1])
    const unit = m[2].toLowerCase()
    if (unit === 'd') total += n * 480
    else if (unit === 'h') total += n * 60
    else if (unit === 'm') total += n
    found = true
  }
  if (!found) return null
  const rounded = Math.round(total)
  return rounded > 0 ? rounded : null
}

export function formatDuration(minutes: number | null | undefined): string {
  if (!minutes || minutes <= 0) return ''
  const d = Math.floor(minutes / 480)
  const rem = minutes % 480
  const h = Math.floor(rem / 60)
  const m = rem % 60
  return [d ? `${d}d` : '', h ? `${h}h` : '', m ? `${m}m` : ''].filter(Boolean).join(' ')
}

export function getApiErrorMessage(err: unknown): string {
  type AxiosLike = { response?: { data?: { detail?: string } }; message?: string }
  const e = err as AxiosLike
  return e?.response?.data?.detail ?? e?.message ?? 'Something went wrong'
}
