import { createContext, useContext, useState, useCallback } from 'react'
import { X, CheckCircle, AlertCircle, Info, AlertTriangle } from 'lucide-react'

const ToastContext = createContext(null)

const TOAST_DURATION = 4000

const icons = {
  success: CheckCircle,
  error: AlertCircle,
  info: Info,
  warning: AlertTriangle,
}

const colors = {
  success: 'bg-green-500/20 border-green-500 text-green-400',
  error: 'bg-red-500/20 border-red-500 text-red-400',
  info: 'bg-blue-500/20 border-blue-500 text-blue-400',
  warning: 'bg-yellow-500/20 border-yellow-500 text-yellow-400',
}

export function ToastProvider({ children }) {
  const [toasts, setToasts] = useState([])
  
  const addToast = useCallback((message, type = 'info', duration = TOAST_DURATION) => {
    const id = Date.now() + Math.random()
    
    setToasts(prev => [...prev, { id, message, type }])
    
    if (duration > 0) {
      setTimeout(() => {
        removeToast(id)
      }, duration)
    }
    
    return id
  }, [])
  
  const removeToast = useCallback((id) => {
    setToasts(prev => prev.filter(t => t.id !== id))
  }, [])
  
  const toast = {
    success: (message, duration) => addToast(message, 'success', duration),
    error: (message, duration) => addToast(message, 'error', duration),
    info: (message, duration) => addToast(message, 'info', duration),
    warning: (message, duration) => addToast(message, 'warning', duration),
  }
  
  return (
    <ToastContext.Provider value={toast}>
      {children}
      
      {/* Toast container */}
      <div className="fixed bottom-20 left-4 right-4 z-50 flex flex-col gap-2 pointer-events-none">
        {toasts.map(({ id, message, type }) => {
          const Icon = icons[type]
          return (
            <div
              key={id}
              className={`
                flex items-center gap-3 p-3 rounded-lg border
                pointer-events-auto animate-slide-up
                ${colors[type]}
              `}
            >
              <Icon className="w-5 h-5 flex-shrink-0" />
              <p className="flex-1 text-sm">{message}</p>
              <button
                onClick={() => removeToast(id)}
                className="p-1 hover:bg-white/10 rounded"
              >
                <X className="w-4 h-4" />
              </button>
            </div>
          )
        })}
      </div>
    </ToastContext.Provider>
  )
}

export function useToast() {
  const context = useContext(ToastContext)
  if (!context) {
    throw new Error('useToast must be used within ToastProvider')
  }
  return context
}
