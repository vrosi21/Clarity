import { Component, type ReactNode } from 'react'

import { Button } from '@/components/ui/button'

interface State {
  err: Error | null
}

export class ErrorBoundary extends Component<{ children: ReactNode }, State> {
  state: State = { err: null }

  static getDerivedStateFromError(err: Error) {
    return { err }
  }

  componentDidCatch(err: Error) {
    // Could pipe to a logging service here.
    console.error('Unhandled UI error:', err)
  }

  render() {
    if (this.state.err) {
      return (
        <div className="flex h-full items-center justify-center p-8">
          <div className="max-w-md text-center">
            <h2 className="mb-2 text-lg font-semibold">Something went wrong</h2>
            <p className="mb-4 text-sm text-muted-foreground">
              {this.state.err.message ?? 'Unexpected error.'}
            </p>
            <Button onClick={() => this.setState({ err: null })}>Try again</Button>
          </div>
        </div>
      )
    }
    return this.props.children
  }
}
