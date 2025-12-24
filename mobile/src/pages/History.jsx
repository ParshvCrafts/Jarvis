import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { 
  Search, Clock, RefreshCw, ChevronRight, 
  Loader2, MessageSquare, Zap
} from 'lucide-react'
import { api } from '../services/api'
import { useToast } from '../contexts/ToastContext'

export default function History() {
  const toast = useToast()
  const [searchQuery, setSearchQuery] = useState('')
  const [page, setPage] = useState(1)
  const pageSize = 20
  
  // Fetch command history
  const { data, isLoading, error, refetch, isRefetching } = useQuery({
    queryKey: ['history', page],
    queryFn: () => api.commands.history(page, pageSize),
  })
  
  // Filter commands by search
  const filteredCommands = data?.commands?.filter(cmd => 
    searchQuery === '' || 
    cmd.text.toLowerCase().includes(searchQuery.toLowerCase()) ||
    cmd.response.toLowerCase().includes(searchQuery.toLowerCase())
  ) || []
  
  // Re-run command
  const handleRerun = async (text) => {
    try {
      toast.info(`Sending: "${text}"`)
      await api.commands.send(text)
      toast.success('Command sent')
      refetch()
    } catch (error) {
      toast.error(error.message)
    }
  }
  
  const totalPages = Math.ceil((data?.total || 0) / pageSize)
  
  return (
    <div className="h-full flex flex-col">
      {/* Search bar */}
      <div className="p-4 bg-jarvis-card border-b border-jarvis-border">
        <div className="relative">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-5 h-5 text-jarvis-muted" />
          <input
            type="text"
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            placeholder="Search commands..."
            className="w-full pl-10 pr-4 py-2.5 bg-jarvis-bg border border-jarvis-border rounded-lg
                     text-sm text-jarvis-text placeholder-jarvis-muted/50
                     focus:outline-none focus:border-jarvis-primary"
          />
        </div>
      </div>
      
      {/* Command list */}
      <div className="flex-1 overflow-y-auto">
        {isLoading ? (
          <div className="h-full flex items-center justify-center">
            <Loader2 className="w-8 h-8 animate-spin text-jarvis-primary" />
          </div>
        ) : error ? (
          <div className="h-full flex flex-col items-center justify-center p-8 text-center">
            <p className="text-jarvis-error mb-4">{error.message}</p>
            <button
              onClick={() => refetch()}
              className="px-4 py-2 bg-jarvis-primary text-jarvis-bg rounded-lg"
            >
              Retry
            </button>
          </div>
        ) : filteredCommands.length === 0 ? (
          <div className="h-full flex flex-col items-center justify-center p-8 text-center">
            <Zap className="w-12 h-12 text-jarvis-muted/50 mb-4" />
            <h3 className="text-lg font-medium text-jarvis-text mb-2">
              {searchQuery ? 'No matching commands' : 'No command history'}
            </h3>
            <p className="text-sm text-jarvis-muted">
              {searchQuery ? 'Try a different search term' : 'Your commands will appear here'}
            </p>
          </div>
        ) : (
          <div className="divide-y divide-jarvis-border">
            {filteredCommands.map((cmd) => (
              <button
                key={cmd.command_id}
                onClick={() => handleRerun(cmd.text)}
                className="w-full p-4 text-left hover:bg-jarvis-card/50 transition-colors"
              >
                <div className="flex items-start gap-3">
                  <MessageSquare className="w-5 h-5 text-jarvis-primary mt-0.5 flex-shrink-0" />
                  <div className="flex-1 min-w-0">
                    <p className="text-sm font-medium text-jarvis-text line-clamp-2">
                      {cmd.text}
                    </p>
                    <p className="text-xs text-jarvis-muted mt-1 line-clamp-2">
                      {cmd.response}
                    </p>
                    <div className="flex items-center gap-3 mt-2 text-xs text-jarvis-muted">
                      <span className="flex items-center gap-1">
                        <Clock className="w-3 h-3" />
                        {new Date(cmd.timestamp).toLocaleString()}
                      </span>
                      <span>{cmd.processing_time_ms?.toFixed(0)}ms</span>
                      <span className="capitalize">{cmd.source}</span>
                    </div>
                  </div>
                  <ChevronRight className="w-5 h-5 text-jarvis-muted flex-shrink-0" />
                </div>
              </button>
            ))}
          </div>
        )}
      </div>
      
      {/* Pagination */}
      {totalPages > 1 && (
        <div className="p-4 bg-jarvis-card border-t border-jarvis-border flex items-center justify-between">
          <button
            onClick={() => setPage(p => Math.max(1, p - 1))}
            disabled={page === 1 || isRefetching}
            className="px-4 py-2 text-sm bg-jarvis-bg border border-jarvis-border rounded-lg
                     disabled:opacity-50 disabled:cursor-not-allowed"
          >
            Previous
          </button>
          
          <span className="text-sm text-jarvis-muted">
            Page {page} of {totalPages}
          </span>
          
          <button
            onClick={() => setPage(p => Math.min(totalPages, p + 1))}
            disabled={page === totalPages || isRefetching}
            className="px-4 py-2 text-sm bg-jarvis-bg border border-jarvis-border rounded-lg
                     disabled:opacity-50 disabled:cursor-not-allowed"
          >
            Next
          </button>
        </div>
      )}
    </div>
  )
}
