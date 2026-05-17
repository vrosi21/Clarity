import { ArrowRight, Boxes, GitBranch, KanbanSquare, Sparkles, Users } from 'lucide-react'
import { Link } from 'react-router-dom'

import { Button } from '@/components/ui/button'
import { Card, CardContent } from '@/components/ui/card'
import { useAuthStore } from '@/store/auth-store'

const FEATURES = [
  {
    icon: KanbanSquare,
    title: 'Kanban boards',
    body: 'Drag tickets through stages your team controls. Built-in safety rules stop tickets jumping past review.',
  },
  {
    icon: Users,
    title: 'Team roles',
    body: 'Owner, admin, member, viewer — every action is permission-checked at the API.',
  },
  {
    icon: GitBranch,
    title: 'Stage workflows',
    body: 'Configure as many normal stages as you want between start and final — Clarity enforces the FSM.',
  },
  {
    icon: Boxes,
    title: 'Categories & priorities',
    body: 'Tag every ticket with a discipline and a priority — filter and group however you work.',
  },
] as const

export function HomePage() {
  const token = useAuthStore((s) => s.token)
  const isLoggedIn = !!token

  return (
    <div className="min-h-screen bg-background">
      {/* Top bar */}
      <header className="sticky top-0 z-30 border-b border-border bg-background/80 backdrop-blur">
        <div className="mx-auto flex h-14 max-w-6xl items-center justify-between px-6">
          <Link to="/" className="flex items-center gap-2">
            <Sparkles className="h-5 w-5 text-accent" />
            <span className="text-base font-semibold tracking-tight">Clarity</span>
          </Link>
          <nav className="flex items-center gap-2">
            {isLoggedIn ? (
              <Button asChild>
                <Link to="/projects">
                  Open workspace <ArrowRight className="h-4 w-4" />
                </Link>
              </Button>
            ) : (
              <>
                <Button variant="ghost" asChild>
                  <Link to="/login">Sign in</Link>
                </Button>
                <Button asChild>
                  <Link to="/register">Get started</Link>
                </Button>
              </>
            )}
          </nav>
        </div>
      </header>

      {/* Hero */}
      <section className="mx-auto max-w-6xl px-6 py-24 text-center">
        <div className="mb-6 inline-flex items-center gap-2 rounded-full border border-border bg-card px-4 py-1.5 text-xs">
          <Sparkles className="h-3.5 w-3.5 text-accent" />
          <span>Task tracking with formal-model rigour</span>
        </div>
        <h1 className="text-balance text-5xl font-semibold tracking-tight sm:text-6xl">
          Run agile boards <br />
          <span className="text-accent">your team can trust.</span>
        </h1>
        <p className="mx-auto mt-6 max-w-xl text-balance text-base text-muted-foreground sm:text-lg">
          Clarity is a Kanban tracker built around an explicit ticket lifecycle. Move work through
          stages with confidence — every transition is checked against a formal state machine.
        </p>
        <div className="mt-10 flex flex-col items-center justify-center gap-3 sm:flex-row">
          {isLoggedIn ? (
            <Button size="lg" asChild>
              <Link to="/projects">
                Open your projects <ArrowRight className="h-4 w-4" />
              </Link>
            </Button>
          ) : (
            <>
              <Button size="lg" asChild>
                <Link to="/register">
                  Get started — it's free <ArrowRight className="h-4 w-4" />
                </Link>
              </Button>
              <Button size="lg" variant="outline" asChild>
                <Link to="/login">Sign in</Link>
              </Button>
            </>
          )}
        </div>
      </section>

      {/* Feature grid */}
      <section className="mx-auto max-w-6xl px-6 pb-24">
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
          {FEATURES.map(({ icon: Icon, title, body }) => (
            <Card key={title}>
              <CardContent className="space-y-3 pt-6">
                <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-accent/15">
                  <Icon className="h-5 w-5 text-accent" />
                </div>
                <h3 className="text-base font-semibold leading-tight">{title}</h3>
                <p className="text-sm text-muted-foreground">{body}</p>
              </CardContent>
            </Card>
          ))}
        </div>
      </section>

      {/* Footer */}
      <footer className="border-t border-border">
        <div className="mx-auto flex max-w-6xl items-center justify-between px-6 py-6 text-sm text-muted-foreground">
          <span>© {new Date().getFullYear()} Clarity</span>
          <span>Built with FastAPI + React</span>
        </div>
      </footer>
    </div>
  )
}
