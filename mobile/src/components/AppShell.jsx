import { useEffect, useState } from 'react'
import { useLocation } from 'react-router-dom'
import Header from './Header'
import BottomNav from './BottomNav'
import OfflineIndicator from './OfflineIndicator'
import { useAuth } from '../contexts/AuthContext'
import { wsService } from '../services/websocket'

export default function AppShell({ children }) {
  const { accessToken } = useAuth()
  const location = useLocation()
  const [connectionStatus, setConnectionStatus] = useState('disconnected')
  
  // Connect WebSocket when authenticated
  useEffect(() => {
    if (accessToken) {
      wsService.connect(accessToken)
      
      const unsubConnected = wsService.on('connected', () => {
        setConnectionStatus('connected')
      })
      
      const unsubDisconnected = wsService.on('disconnected', () => {
        setConnectionStatus('disconnected')
      })
      
      const unsubError = wsService.on('error', () => {
        setConnectionStatus('error')
      })
      
      return () => {
        unsubConnected()
        unsubDisconnected()
        unsubError()
        wsService.disconnect()
      }
    }
  }, [accessToken])
  
  // Get page title based on route
  const getTitle = () => {
    switch (location.pathname) {
      case '/': return 'Home'
      case '/voice': return 'Voice'
      case '/devices': return 'Devices'
      case '/settings': return 'Settings'
      case '/history': return 'History'
      default: return 'JARVIS'
    }
  }
  
  // Check if we should show back button
  const showBack = ['/history'].includes(location.pathname)
  
  return (
    <div className="h-screen w-screen flex flex-col bg-jarvis-bg overflow-hidden">
      {/* Header */}
      <Header 
        title={getTitle()} 
        showBack={showBack}
        connectionStatus={connectionStatus}
      />
      
      {/* Offline indicator */}
      <OfflineIndicator />
      
      {/* Main content */}
      <main className="flex-1 overflow-y-auto overflow-x-hidden">
        {children}
      </main>
      
      {/* Bottom navigation */}
      <BottomNav />
    </div>
  )
}
