import { Component } from 'react'
import { AlertTriangle, RefreshCw } from 'lucide-react'

/**
 * Error Boundary component to catch React errors.
 * Prevents the entire app from crashing on component errors.
 */
export default class ErrorBoundary extends Component {
  constructor(props) {
    super(props)
    this.state = { hasError: false, error: null, errorInfo: null }
  }

  static getDerivedStateFromError(error) {
    return { hasError: true, error }
  }

  componentDidCatch(error, errorInfo) {
    console.error('ErrorBoundary caught an error:', error, errorInfo)
    this.setState({ errorInfo })
    
    // Could send to error tracking service here
  }

  handleRetry = () => {
    this.setState({ hasError: false, error: null, errorInfo: null })
  }

  render() {
    if (this.state.hasError) {
      return (
        <div className="min-h-screen bg-jarvis-bg flex items-center justify-center p-4">
          <div className="max-w-md w-full bg-jarvis-card rounded-2xl border border-jarvis-border p-6 text-center">
            <div className="w-16 h-16 mx-auto mb-4 rounded-full bg-jarvis-error/20 flex items-center justify-center">
              <AlertTriangle className="w-8 h-8 text-jarvis-error" />
            </div>
            
            <h2 className="text-xl font-semibold text-jarvis-text mb-2">
              Something went wrong
            </h2>
            
            <p className="text-jarvis-muted mb-4">
              An unexpected error occurred. Please try again.
            </p>
            
            {this.props.showDetails && this.state.error && (
              <div className="mb-4 p-3 bg-jarvis-bg rounded-lg text-left">
                <p className="text-xs text-jarvis-error font-mono break-all">
                  {this.state.error.toString()}
                </p>
              </div>
            )}
            
            <button
              onClick={this.handleRetry}
              className="inline-flex items-center gap-2 px-6 py-3 bg-jarvis-primary text-jarvis-bg rounded-lg font-medium hover:opacity-90"
            >
              <RefreshCw className="w-4 h-4" />
              Try Again
            </button>
          </div>
        </div>
      )
    }

    return this.props.children
  }
}
