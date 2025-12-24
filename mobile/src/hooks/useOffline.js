import { useState, useEffect, useCallback } from 'react'

/**
 * Hook for offline detection and command queuing.
 */
export function useOffline() {
  const [isOnline, setIsOnline] = useState(navigator.onLine)
  const [pendingCommands, setPendingCommands] = useState([])
  
  // Listen for online/offline events
  useEffect(() => {
    const handleOnline = () => {
      setIsOnline(true)
      // Sync pending commands when back online
      syncPendingCommands()
    }
    
    const handleOffline = () => {
      setIsOnline(false)
    }
    
    window.addEventListener('online', handleOnline)
    window.addEventListener('offline', handleOffline)
    
    // Load pending commands from localStorage
    const stored = localStorage.getItem('pendingCommands')
    if (stored) {
      try {
        setPendingCommands(JSON.parse(stored))
      } catch (e) {
        console.error('Failed to load pending commands:', e)
      }
    }
    
    return () => {
      window.removeEventListener('online', handleOnline)
      window.removeEventListener('offline', handleOffline)
    }
  }, [])
  
  // Queue a command for later
  const queueCommand = useCallback((command) => {
    const newCommand = {
      id: Date.now(),
      text: command,
      timestamp: new Date().toISOString(),
    }
    
    setPendingCommands(prev => {
      const updated = [...prev, newCommand]
      localStorage.setItem('pendingCommands', JSON.stringify(updated))
      return updated
    })
    
    return newCommand.id
  }, [])
  
  // Remove a command from queue
  const removeCommand = useCallback((id) => {
    setPendingCommands(prev => {
      const updated = prev.filter(cmd => cmd.id !== id)
      localStorage.setItem('pendingCommands', JSON.stringify(updated))
      return updated
    })
  }, [])
  
  // Sync pending commands when online
  const syncPendingCommands = useCallback(async () => {
    const stored = localStorage.getItem('pendingCommands')
    if (!stored) return
    
    try {
      const commands = JSON.parse(stored)
      if (commands.length === 0) return
      
      console.log(`Syncing ${commands.length} pending commands...`)
      
      // Import api dynamically to avoid circular deps
      const { api } = await import('../services/api')
      
      for (const cmd of commands) {
        try {
          await api.commands.send(cmd.text)
          removeCommand(cmd.id)
        } catch (error) {
          console.error(`Failed to sync command ${cmd.id}:`, error)
        }
      }
    } catch (error) {
      console.error('Failed to sync pending commands:', error)
    }
  }, [removeCommand])
  
  return {
    isOnline,
    pendingCommands,
    queueCommand,
    removeCommand,
    syncPendingCommands,
    pendingCount: pendingCommands.length,
  }
}

/**
 * Hook for caching recent data for offline access.
 */
export function useOfflineCache(key, fetcher, options = {}) {
  const { ttl = 5 * 60 * 1000 } = options // 5 minutes default TTL
  const [data, setData] = useState(null)
  const [isLoading, setIsLoading] = useState(true)
  const [error, setError] = useState(null)
  const { isOnline } = useOffline()
  
  useEffect(() => {
    const loadData = async () => {
      setIsLoading(true)
      setError(null)
      
      // Try to get cached data first
      const cached = localStorage.getItem(`cache_${key}`)
      if (cached) {
        try {
          const { data: cachedData, timestamp } = JSON.parse(cached)
          const age = Date.now() - timestamp
          
          // Use cache if offline or within TTL
          if (!isOnline || age < ttl) {
            setData(cachedData)
            setIsLoading(false)
            
            // If online and cache is stale, fetch in background
            if (isOnline && age >= ttl) {
              fetchAndCache()
            }
            return
          }
        } catch (e) {
          console.error('Failed to parse cached data:', e)
        }
      }
      
      // Fetch fresh data if online
      if (isOnline) {
        await fetchAndCache()
      } else {
        setError(new Error('No cached data available offline'))
        setIsLoading(false)
      }
    }
    
    const fetchAndCache = async () => {
      try {
        const freshData = await fetcher()
        setData(freshData)
        
        // Cache the data
        localStorage.setItem(`cache_${key}`, JSON.stringify({
          data: freshData,
          timestamp: Date.now(),
        }))
      } catch (err) {
        setError(err)
      } finally {
        setIsLoading(false)
      }
    }
    
    loadData()
  }, [key, isOnline, ttl])
  
  return { data, isLoading, error, isOnline }
}
