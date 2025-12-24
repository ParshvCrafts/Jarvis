import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { Eye, EyeOff, LogIn, Loader2 } from 'lucide-react'
import { useAuth } from '../contexts/AuthContext'
import { useToast } from '../contexts/ToastContext'

export default function Login() {
  const navigate = useNavigate()
  const { login, isLoading } = useAuth()
  const toast = useToast()
  
  const [username, setUsername] = useState('')
  const [password, setPassword] = useState('')
  const [showPassword, setShowPassword] = useState(false)
  const [error, setError] = useState('')
  
  const handleSubmit = async (e) => {
    e.preventDefault()
    setError('')
    
    if (!username || !password) {
      setError('Please enter username and password')
      return
    }
    
    const result = await login(username, password)
    
    if (result.success) {
      toast.success('Welcome to JARVIS')
      navigate('/', { replace: true })
    } else {
      setError(result.error)
      toast.error(result.error)
    }
  }
  
  return (
    <div className="min-h-screen bg-jarvis-bg flex flex-col items-center justify-center p-6">
      {/* Logo */}
      <div className="mb-8 flex flex-col items-center">
        <div className="w-20 h-20 rounded-full bg-gradient-to-br from-jarvis-primary to-jarvis-secondary flex items-center justify-center mb-4">
          <span className="text-3xl font-bold text-jarvis-bg">J</span>
        </div>
        <h1 className="text-2xl font-bold text-jarvis-text">JARVIS</h1>
        <p className="text-jarvis-muted text-sm mt-1">AI Assistant</p>
      </div>
      
      {/* Login form */}
      <form onSubmit={handleSubmit} className="w-full max-w-sm space-y-4">
        {/* Username */}
        <div>
          <label className="block text-sm font-medium text-jarvis-muted mb-1.5">
            Username
          </label>
          <input
            type="text"
            value={username}
            onChange={(e) => setUsername(e.target.value)}
            placeholder="Enter username"
            autoComplete="username"
            className="w-full px-4 py-3 bg-jarvis-card border border-jarvis-border rounded-lg
                     text-jarvis-text placeholder-jarvis-muted/50
                     focus:outline-none focus:border-jarvis-primary focus:ring-1 focus:ring-jarvis-primary
                     transition-colors"
          />
        </div>
        
        {/* Password */}
        <div>
          <label className="block text-sm font-medium text-jarvis-muted mb-1.5">
            Password
          </label>
          <div className="relative">
            <input
              type={showPassword ? 'text' : 'password'}
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              placeholder="Enter password"
              autoComplete="current-password"
              className="w-full px-4 py-3 pr-12 bg-jarvis-card border border-jarvis-border rounded-lg
                       text-jarvis-text placeholder-jarvis-muted/50
                       focus:outline-none focus:border-jarvis-primary focus:ring-1 focus:ring-jarvis-primary
                       transition-colors"
            />
            <button
              type="button"
              onClick={() => setShowPassword(!showPassword)}
              className="absolute right-3 top-1/2 -translate-y-1/2 p-1 text-jarvis-muted hover:text-jarvis-text"
            >
              {showPassword ? <EyeOff className="w-5 h-5" /> : <Eye className="w-5 h-5" />}
            </button>
          </div>
        </div>
        
        {/* Error message */}
        {error && (
          <p className="text-jarvis-error text-sm">{error}</p>
        )}
        
        {/* Submit button */}
        <button
          type="submit"
          disabled={isLoading}
          className="w-full py-3 px-4 bg-jarvis-primary text-jarvis-bg font-semibold rounded-lg
                   hover:bg-jarvis-primary/90 active:bg-jarvis-primary/80
                   disabled:opacity-50 disabled:cursor-not-allowed
                   flex items-center justify-center gap-2 transition-colors"
        >
          {isLoading ? (
            <>
              <Loader2 className="w-5 h-5 animate-spin" />
              Signing in...
            </>
          ) : (
            <>
              <LogIn className="w-5 h-5" />
              Sign In
            </>
          )}
        </button>
      </form>
      
      {/* Default credentials hint */}
      <p className="mt-6 text-xs text-jarvis-muted text-center">
        Default: admin / jarvis
      </p>
    </div>
  )
}
