import { WifiOff, CloudOff, RefreshCw } from 'lucide-react'
import { useOffline } from '../hooks/useOffline'

/**
 * Offline indicator banner shown when the app is offline.
 */
export default function OfflineIndicator() {
  const { isOnline, pendingCount, syncPendingCommands } = useOffline()
  
  if (isOnline && pendingCount === 0) return null
  
  return (
    <div className="bg-jarvis-warning/20 border-b border-jarvis-warning/30 px-4 py-2">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          {!isOnline ? (
            <>
              <WifiOff className="w-4 h-4 text-jarvis-warning" />
              <span className="text-sm text-jarvis-warning">
                You're offline
              </span>
            </>
          ) : (
            <>
              <CloudOff className="w-4 h-4 text-jarvis-warning" />
              <span className="text-sm text-jarvis-warning">
                {pendingCount} command{pendingCount !== 1 ? 's' : ''} pending
              </span>
            </>
          )}
        </div>
        
        {isOnline && pendingCount > 0 && (
          <button
            onClick={syncPendingCommands}
            className="flex items-center gap-1 text-xs text-jarvis-warning hover:underline"
          >
            <RefreshCw className="w-3 h-3" />
            Sync now
          </button>
        )}
      </div>
    </div>
  )
}
