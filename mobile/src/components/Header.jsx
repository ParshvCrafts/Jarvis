import { useNavigate } from 'react-router-dom'
import { ChevronLeft, Wifi, WifiOff, AlertCircle } from 'lucide-react'

export default function Header({ title, showBack = false, connectionStatus = 'disconnected' }) {
  const navigate = useNavigate()
  
  const statusColors = {
    connected: 'text-jarvis-secondary',
    disconnected: 'text-jarvis-muted',
    error: 'text-jarvis-error',
  }
  
  const StatusIcon = connectionStatus === 'connected' ? Wifi : 
                     connectionStatus === 'error' ? AlertCircle : WifiOff
  
  return (
    <header className="safe-top bg-jarvis-card border-b border-jarvis-border">
      <div className="flex items-center justify-between h-14 px-4">
        {/* Left side - back button or logo */}
        <div className="flex items-center gap-2 w-20">
          {showBack ? (
            <button
              onClick={() => navigate(-1)}
              className="p-2 -ml-2 rounded-lg hover:bg-jarvis-border/50 active:bg-jarvis-border transition-colors"
            >
              <ChevronLeft className="w-6 h-6" />
            </button>
          ) : (
            <div className="flex items-center gap-2">
              <div className="w-8 h-8 rounded-full bg-gradient-to-br from-jarvis-primary to-jarvis-secondary flex items-center justify-center">
                <span className="text-xs font-bold text-jarvis-bg">J</span>
              </div>
            </div>
          )}
        </div>
        
        {/* Center - title */}
        <h1 className="text-lg font-semibold text-jarvis-text">
          {title}
        </h1>
        
        {/* Right side - connection status */}
        <div className="flex items-center justify-end w-20">
          <div className={`flex items-center gap-1.5 ${statusColors[connectionStatus]}`}>
            <StatusIcon className="w-4 h-4" />
            <span className="text-xs capitalize hidden sm:inline">
              {connectionStatus}
            </span>
          </div>
        </div>
      </div>
    </header>
  )
}
