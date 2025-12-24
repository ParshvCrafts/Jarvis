import { createContext, useContext, useState, useEffect, useCallback } from 'react'
import { api } from '../services/api'

const AuthContext = createContext(null)

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null)
  const [isLoading, setIsLoading] = useState(true)
  const [accessToken, setAccessToken] = useState(null)
  
  // Check for existing session on mount
  useEffect(() => {
    const checkAuth = async () => {
      const storedToken = sessionStorage.getItem('accessToken')
      const storedRefresh = localStorage.getItem('refreshToken')
      
      if (storedToken) {
        setAccessToken(storedToken)
        api.setToken(storedToken)
        
        try {
          // Verify token by fetching status
          await api.status.get()
          setUser({ authenticated: true })
        } catch (error) {
          // Token invalid, try refresh
          if (storedRefresh) {
            try {
              const result = await api.auth.refreshToken(storedRefresh)
              setAccessToken(result.access_token)
              sessionStorage.setItem('accessToken', result.access_token)
              localStorage.setItem('refreshToken', result.refresh_token)
              api.setToken(result.access_token)
              setUser({ authenticated: true })
            } catch {
              // Refresh failed, clear tokens
              clearTokens()
            }
          } else {
            clearTokens()
          }
        }
      }
      
      setIsLoading(false)
    }
    
    checkAuth()
  }, [])
  
  const clearTokens = () => {
    sessionStorage.removeItem('accessToken')
    localStorage.removeItem('refreshToken')
    api.setToken(null)
    setAccessToken(null)
    setUser(null)
  }
  
  const login = useCallback(async (username, password, deviceName = 'Mobile App') => {
    setIsLoading(true)
    
    try {
      const result = await api.auth.login(username, password, deviceName, 'web')
      
      setAccessToken(result.access_token)
      sessionStorage.setItem('accessToken', result.access_token)
      localStorage.setItem('refreshToken', result.refresh_token)
      api.setToken(result.access_token)
      
      setUser({
        authenticated: true,
        userId: result.user_id,
        deviceId: result.device_id,
      })
      
      return { success: true }
    } catch (error) {
      return { 
        success: false, 
        error: error.message || 'Login failed' 
      }
    } finally {
      setIsLoading(false)
    }
  }, [])
  
  const logout = useCallback(async () => {
    try {
      await api.auth.logout()
    } catch {
      // Ignore logout errors
    }
    
    clearTokens()
  }, [])
  
  const refreshToken = useCallback(async () => {
    const storedRefresh = localStorage.getItem('refreshToken')
    
    if (!storedRefresh) {
      clearTokens()
      return false
    }
    
    try {
      const result = await api.auth.refreshToken(storedRefresh)
      setAccessToken(result.access_token)
      sessionStorage.setItem('accessToken', result.access_token)
      localStorage.setItem('refreshToken', result.refresh_token)
      api.setToken(result.access_token)
      return true
    } catch {
      clearTokens()
      return false
    }
  }, [])
  
  const value = {
    user,
    isAuthenticated: !!user,
    isLoading,
    accessToken,
    login,
    logout,
    refreshToken,
  }
  
  return (
    <AuthContext.Provider value={value}>
      {children}
    </AuthContext.Provider>
  )
}

export function useAuth() {
  const context = useContext(AuthContext)
  if (!context) {
    throw new Error('useAuth must be used within AuthProvider')
  }
  return context
}
