import { useState, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import { 
  Mic, Sun, Cloud, Calendar, Lightbulb, Search, 
  Clock, ChevronRight, Activity, Zap, Users, Rocket, Star
} from 'lucide-react'
import { api } from '../services/api'
import { useToast } from '../contexts/ToastContext'

// Quick action buttons
const quickActions = [
  { icon: Lightbulb, label: 'Lights', command: 'turn on the lights', color: 'from-yellow-500 to-orange-500' },
  { icon: Cloud, label: 'Weather', command: "what's the weather", color: 'from-blue-500 to-cyan-500' },
  { icon: Calendar, label: 'Schedule', command: "what's on my calendar", color: 'from-purple-500 to-pink-500' },
  { icon: Search, label: 'Research', command: 'start research on', color: 'from-green-500 to-emerald-500' },
]

export default function Home() {
  const navigate = useNavigate()
  const toast = useToast()
  const [greeting, setGreeting] = useState('')
  
  // Fetch system status
  const { data: status } = useQuery({
    queryKey: ['status'],
    queryFn: () => api.status.get(),
    refetchInterval: 30000, // Refresh every 30s
  })
  
  // Fetch recent commands
  const { data: history } = useQuery({
    queryKey: ['history'],
    queryFn: () => api.commands.history(1, 5),
  })
  
  // Fetch contacts stats
  const { data: contactStats } = useQuery({
    queryKey: ['contactStats'],
    queryFn: () => api.contacts.count(),
    retry: false,
  })
  
  // Fetch quick launch stats
  const { data: quicklaunchStats } = useQuery({
    queryKey: ['quicklaunch-stats'],
    queryFn: () => api.quicklaunch.stats(),
    retry: false,
  })
  
  // Set greeting based on time
  useEffect(() => {
    const hour = new Date().getHours()
    if (hour < 12) setGreeting('Good morning')
    else if (hour < 17) setGreeting('Good afternoon')
    else setGreeting('Good evening')
  }, [])
  
  // Handle quick action
  const handleQuickAction = async (command) => {
    try {
      toast.info(`Sending: "${command}"`)
      const result = await api.commands.send(command)
      toast.success('Command sent')
      // Navigate to voice to see response
      navigate('/voice')
    } catch (error) {
      toast.error(error.message)
    }
  }
  
  return (
    <div className="p-4 space-y-6 pb-20">
      {/* Greeting */}
      <div className="pt-2">
        <h2 className="text-2xl font-bold text-jarvis-text">{greeting}</h2>
        <p className="text-jarvis-muted mt-1">How can I help you today?</p>
      </div>
      
      {/* Voice button shortcut */}
      <button
        onClick={() => navigate('/voice')}
        className="w-full p-4 bg-gradient-to-r from-jarvis-primary/20 to-jarvis-secondary/20 
                 border border-jarvis-primary/30 rounded-xl
                 flex items-center gap-4 active:scale-[0.98] transition-transform"
      >
        <div className="w-12 h-12 rounded-full bg-jarvis-primary/20 flex items-center justify-center">
          <Mic className="w-6 h-6 text-jarvis-primary" />
        </div>
        <div className="flex-1 text-left">
          <p className="font-medium text-jarvis-text">Tap to speak</p>
          <p className="text-sm text-jarvis-muted">Ask JARVIS anything</p>
        </div>
        <ChevronRight className="w-5 h-5 text-jarvis-muted" />
      </button>
      
      {/* Quick actions */}
      <div>
        <h3 className="text-sm font-medium text-jarvis-muted mb-3">Quick Actions</h3>
        <div className="grid grid-cols-4 gap-3">
          {quickActions.map(({ icon: Icon, label, command, color }) => (
            <button
              key={label}
              onClick={() => handleQuickAction(command)}
              className="flex flex-col items-center gap-2 p-3 rounded-xl bg-jarvis-card 
                       border border-jarvis-border hover:border-jarvis-primary/50
                       active:scale-95 transition-all"
            >
              <div className={`w-10 h-10 rounded-full bg-gradient-to-br ${color} 
                            flex items-center justify-center`}>
                <Icon className="w-5 h-5 text-white" />
              </div>
              <span className="text-xs text-jarvis-muted">{label}</span>
            </button>
          ))}
        </div>
      </div>
      
      {/* System status */}
      <div className="p-4 bg-jarvis-card rounded-xl border border-jarvis-border">
        <div className="flex items-center justify-between mb-3">
          <h3 className="text-sm font-medium text-jarvis-muted">System Status</h3>
          <div className={`flex items-center gap-1.5 text-xs ${
            status?.status === 'healthy' ? 'text-jarvis-secondary' : 'text-jarvis-warning'
          }`}>
            <Activity className="w-3.5 h-3.5" />
            <span className="capitalize">{status?.status || 'Unknown'}</span>
          </div>
        </div>
        
        <div className="grid grid-cols-2 gap-3">
          <div className="p-3 bg-jarvis-bg rounded-lg">
            <p className="text-xs text-jarvis-muted">Version</p>
            <p className="text-sm font-medium text-jarvis-text mt-0.5">
              {status?.version || '—'}
            </p>
          </div>
          <div className="p-3 bg-jarvis-bg rounded-lg">
            <p className="text-xs text-jarvis-muted">Uptime</p>
            <p className="text-sm font-medium text-jarvis-text mt-0.5">
              {status?.uptime_seconds 
                ? `${Math.floor(status.uptime_seconds / 3600)}h ${Math.floor((status.uptime_seconds % 3600) / 60)}m`
                : '—'}
            </p>
          </div>
        </div>
        
        {/* Data stats */}
        <div className="grid grid-cols-2 gap-3 mt-3">
          <button
            onClick={() => navigate('/contacts')}
            className="p-3 bg-jarvis-bg rounded-lg hover:bg-jarvis-border/50 transition-colors text-left"
          >
            <div className="flex items-center gap-2">
              <Users className="w-4 h-4 text-jarvis-primary" />
              <p className="text-xs text-jarvis-muted">Contacts</p>
            </div>
            <div className="flex items-center gap-2 mt-1">
              <p className="text-sm font-medium text-jarvis-text">
                {contactStats?.total || 0}
              </p>
              {contactStats?.favorites > 0 && (
                <span className="flex items-center gap-0.5 text-xs text-yellow-500">
                  <Star className="w-3 h-3 fill-yellow-500" />
                  {contactStats.favorites}
                </span>
              )}
            </div>
          </button>
          <button
            onClick={() => navigate('/quicklaunch')}
            className="p-3 bg-jarvis-bg rounded-lg hover:bg-jarvis-border/50 transition-colors text-left"
          >
            <div className="flex items-center gap-2">
              <Rocket className="w-4 h-4 text-jarvis-secondary" />
              <p className="text-xs text-jarvis-muted">Quick Launch</p>
            </div>
            <p className="text-sm font-medium text-jarvis-text mt-1">
              {(quicklaunchStats?.apps_count || 0) + (quicklaunchStats?.bookmarks_count || 0)} items
            </p>
          </button>
        </div>
      </div>
      
      {/* Recent commands */}
      <div>
        <div className="flex items-center justify-between mb-3">
          <h3 className="text-sm font-medium text-jarvis-muted">Recent Commands</h3>
          <button
            onClick={() => navigate('/history')}
            className="text-xs text-jarvis-primary hover:underline"
          >
            View all
          </button>
        </div>
        
        <div className="space-y-2">
          {history?.commands?.length > 0 ? (
            history.commands.slice(0, 5).map((cmd) => (
              <button
                key={cmd.command_id}
                onClick={() => handleQuickAction(cmd.text)}
                className="w-full p-3 bg-jarvis-card rounded-lg border border-jarvis-border
                         text-left hover:border-jarvis-primary/50 transition-colors"
              >
                <div className="flex items-start gap-3">
                  <Clock className="w-4 h-4 text-jarvis-muted mt-0.5 flex-shrink-0" />
                  <div className="flex-1 min-w-0">
                    <p className="text-sm text-jarvis-text truncate">{cmd.text}</p>
                    <p className="text-xs text-jarvis-muted mt-0.5 truncate">
                      {cmd.response?.substring(0, 50)}...
                    </p>
                  </div>
                </div>
              </button>
            ))
          ) : (
            <div className="p-6 text-center text-jarvis-muted">
              <Zap className="w-8 h-8 mx-auto mb-2 opacity-50" />
              <p className="text-sm">No recent commands</p>
            </div>
          )}
        </div>
      </div>
    </div>
  )
}
