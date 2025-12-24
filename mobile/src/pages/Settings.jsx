import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { useNavigate } from 'react-router-dom'
import { 
  User, Volume2, Bell, Database, Smartphone, Info,
  ChevronRight, LogOut, Trash2, Loader2, Check,
  Users, Rocket, Globe
} from 'lucide-react'
import { api } from '../services/api'
import { useAuth } from '../contexts/AuthContext'
import { useToast } from '../contexts/ToastContext'
import clsx from 'clsx'

export default function Settings() {
  const navigate = useNavigate()
  const { user, logout } = useAuth()
  const toast = useToast()
  const queryClient = useQueryClient()
  
  // Fetch settings
  const { data: settings, isLoading } = useQuery({
    queryKey: ['settings'],
    queryFn: () => api.settings.get(),
  })
  
  // Fetch cache stats
  const { data: cacheStats } = useQuery({
    queryKey: ['cacheStats'],
    queryFn: () => api.cache.stats(),
  })
  
  // Fetch registered devices
  const { data: devices } = useQuery({
    queryKey: ['authDevices'],
    queryFn: () => api.auth.getDevices(),
  })
  
  // Update settings mutation
  const updateMutation = useMutation({
    mutationFn: (newSettings) => api.settings.update(newSettings),
    onSuccess: () => {
      queryClient.invalidateQueries(['settings'])
      toast.success('Settings updated')
    },
    onError: (error) => {
      toast.error(error.message)
    },
  })
  
  // Clear cache mutation
  const clearCacheMutation = useMutation({
    mutationFn: () => api.cache.clear('all'),
    onSuccess: () => {
      queryClient.invalidateQueries(['cacheStats'])
      toast.success('Cache cleared')
    },
    onError: (error) => {
      toast.error(error.message)
    },
  })
  
  // Handle setting toggle
  const handleToggle = (key) => {
    if (settings) {
      updateMutation.mutate({ [key]: !settings[key] })
    }
  }
  
  // Handle logout
  const handleLogout = async () => {
    if (confirm('Are you sure you want to logout?')) {
      await logout()
      navigate('/login', { replace: true })
    }
  }
  
  if (isLoading) {
    return (
      <div className="h-full flex items-center justify-center">
        <Loader2 className="w-8 h-8 animate-spin text-jarvis-primary" />
      </div>
    )
  }
  
  return (
    <div className="p-4 pb-20 space-y-6">
      {/* Account section */}
      <section>
        <h3 className="text-sm font-medium text-jarvis-muted mb-3 px-1">Account</h3>
        <div className="bg-jarvis-card rounded-xl border border-jarvis-border overflow-hidden">
          <div className="p-4 flex items-center gap-4 border-b border-jarvis-border">
            <div className="w-12 h-12 rounded-full bg-jarvis-primary/20 flex items-center justify-center">
              <User className="w-6 h-6 text-jarvis-primary" />
            </div>
            <div className="flex-1">
              <p className="font-medium text-jarvis-text">Admin</p>
              <p className="text-sm text-jarvis-muted">Logged in</p>
            </div>
          </div>
          
          <button
            onClick={handleLogout}
            className="w-full p-4 flex items-center gap-3 text-jarvis-error hover:bg-jarvis-error/10 transition-colors"
          >
            <LogOut className="w-5 h-5" />
            <span>Logout</span>
          </button>
        </div>
      </section>
      
      {/* Voice section */}
      <section>
        <h3 className="text-sm font-medium text-jarvis-muted mb-3 px-1">Voice</h3>
        <div className="bg-jarvis-card rounded-xl border border-jarvis-border divide-y divide-jarvis-border">
          <SettingToggle
            icon={Volume2}
            label="Voice Enabled"
            description="Enable voice input and output"
            checked={settings?.voice_enabled ?? true}
            onChange={() => handleToggle('voice_enabled')}
          />
          
          <div className="p-4">
            <div className="flex items-center gap-3 mb-3">
              <Volume2 className="w-5 h-5 text-jarvis-muted" />
              <div className="flex-1">
                <p className="text-sm font-medium text-jarvis-text">TTS Voice</p>
                <p className="text-xs text-jarvis-muted">{settings?.tts_voice || 'Default'}</p>
              </div>
            </div>
          </div>
          
          <div className="p-4">
            <div className="flex items-center gap-3 mb-2">
              <Volume2 className="w-5 h-5 text-jarvis-muted" />
              <p className="text-sm font-medium text-jarvis-text">Speech Rate</p>
              <span className="ml-auto text-sm text-jarvis-muted">
                {settings?.tts_speed?.toFixed(1) || '1.0'}x
              </span>
            </div>
            <input
              type="range"
              min="0.5"
              max="2"
              step="0.1"
              value={settings?.tts_speed || 1}
              onChange={(e) => updateMutation.mutate({ tts_speed: parseFloat(e.target.value) })}
              className="w-full accent-jarvis-primary"
            />
          </div>
        </div>
      </section>
      
      {/* Notifications section */}
      <section>
        <h3 className="text-sm font-medium text-jarvis-muted mb-3 px-1">Notifications</h3>
        <div className="bg-jarvis-card rounded-xl border border-jarvis-border">
          <SettingToggle
            icon={Bell}
            label="Push Notifications"
            description="Receive notifications on this device"
            checked={settings?.notifications_enabled ?? true}
            onChange={() => handleToggle('notifications_enabled')}
          />
        </div>
      </section>
      
      {/* Management section */}
      <section>
        <h3 className="text-sm font-medium text-jarvis-muted mb-3 px-1">Management</h3>
        <div className="bg-jarvis-card rounded-xl border border-jarvis-border divide-y divide-jarvis-border">
          <button
            onClick={() => navigate('/contacts')}
            className="w-full p-4 flex items-center gap-3 hover:bg-jarvis-border/30 transition-colors"
          >
            <Users className="w-5 h-5 text-jarvis-primary" />
            <div className="flex-1 text-left">
              <p className="text-sm font-medium text-jarvis-text">Contacts</p>
              <p className="text-xs text-jarvis-muted">Manage your contacts</p>
            </div>
            <ChevronRight className="w-5 h-5 text-jarvis-muted" />
          </button>
          
          <button
            onClick={() => navigate('/quicklaunch')}
            className="w-full p-4 flex items-center gap-3 hover:bg-jarvis-border/30 transition-colors"
          >
            <Rocket className="w-5 h-5 text-jarvis-secondary" />
            <div className="flex-1 text-left">
              <p className="text-sm font-medium text-jarvis-text">Quick Launch</p>
              <p className="text-xs text-jarvis-muted">Apps & bookmarks</p>
            </div>
            <ChevronRight className="w-5 h-5 text-jarvis-muted" />
          </button>
        </div>
      </section>
      
      {/* Cache section */}
      <section>
        <h3 className="text-sm font-medium text-jarvis-muted mb-3 px-1">Cache</h3>
        <div className="bg-jarvis-card rounded-xl border border-jarvis-border divide-y divide-jarvis-border">
          <div className="p-4">
            <div className="flex items-center gap-3 mb-3">
              <Database className="w-5 h-5 text-jarvis-muted" />
              <div className="flex-1">
                <p className="text-sm font-medium text-jarvis-text">Cache Statistics</p>
              </div>
            </div>
            
            {cacheStats && (
              <div className="grid grid-cols-2 gap-3">
                <div className="p-3 bg-jarvis-bg rounded-lg">
                  <p className="text-xs text-jarvis-muted">Hit Ratio</p>
                  <p className="text-lg font-semibold text-jarvis-secondary">
                    {(cacheStats.hit_ratio * 100).toFixed(1)}%
                  </p>
                </div>
                <div className="p-3 bg-jarvis-bg rounded-lg">
                  <p className="text-xs text-jarvis-muted">Total Hits</p>
                  <p className="text-lg font-semibold text-jarvis-text">
                    {cacheStats.total_hits}
                  </p>
                </div>
              </div>
            )}
          </div>
          
          <button
            onClick={() => {
              if (confirm('Clear all cached data?')) {
                clearCacheMutation.mutate()
              }
            }}
            disabled={clearCacheMutation.isPending}
            className="w-full p-4 flex items-center gap-3 text-jarvis-warning hover:bg-jarvis-warning/10 transition-colors disabled:opacity-50"
          >
            {clearCacheMutation.isPending ? (
              <Loader2 className="w-5 h-5 animate-spin" />
            ) : (
              <Trash2 className="w-5 h-5" />
            )}
            <span>Clear Cache</span>
          </button>
        </div>
      </section>
      
      {/* Devices section */}
      <section>
        <h3 className="text-sm font-medium text-jarvis-muted mb-3 px-1">Registered Devices</h3>
        <div className="bg-jarvis-card rounded-xl border border-jarvis-border divide-y divide-jarvis-border">
          {devices?.devices?.length > 0 ? (
            devices.devices.map((device) => (
              <div key={device.device_id} className="p-4 flex items-center gap-3">
                <Smartphone className="w-5 h-5 text-jarvis-muted" />
                <div className="flex-1 min-w-0">
                  <p className="text-sm font-medium text-jarvis-text truncate">
                    {device.device_name}
                  </p>
                  <p className="text-xs text-jarvis-muted">
                    {device.device_type} • Last seen {new Date(device.last_seen).toLocaleDateString()}
                  </p>
                </div>
                {device.is_current && (
                  <span className="text-xs text-jarvis-secondary bg-jarvis-secondary/10 px-2 py-1 rounded">
                    Current
                  </span>
                )}
              </div>
            ))
          ) : (
            <div className="p-4 text-center text-jarvis-muted text-sm">
              No devices registered
            </div>
          )}
        </div>
      </section>
      
      {/* About section */}
      <section>
        <h3 className="text-sm font-medium text-jarvis-muted mb-3 px-1">About</h3>
        <div className="bg-jarvis-card rounded-xl border border-jarvis-border divide-y divide-jarvis-border">
          <div className="p-4 flex items-center gap-3">
            <Info className="w-5 h-5 text-jarvis-muted" />
            <div className="flex-1">
              <p className="text-sm font-medium text-jarvis-text">JARVIS Mobile</p>
              <p className="text-xs text-jarvis-muted">Version 1.0.0</p>
            </div>
          </div>
          
          <a
            href="/api/docs"
            target="_blank"
            rel="noopener noreferrer"
            className="p-4 flex items-center gap-3 hover:bg-jarvis-border/30 transition-colors"
          >
            <Database className="w-5 h-5 text-jarvis-muted" />
            <span className="flex-1 text-sm text-jarvis-text">API Documentation</span>
            <ChevronRight className="w-5 h-5 text-jarvis-muted" />
          </a>
        </div>
      </section>
    </div>
  )
}

// Toggle setting component
function SettingToggle({ icon: Icon, label, description, checked, onChange }) {
  return (
    <button
      onClick={onChange}
      className="w-full p-4 flex items-center gap-3 text-left hover:bg-jarvis-border/30 transition-colors"
    >
      <Icon className="w-5 h-5 text-jarvis-muted" />
      <div className="flex-1">
        <p className="text-sm font-medium text-jarvis-text">{label}</p>
        {description && (
          <p className="text-xs text-jarvis-muted">{description}</p>
        )}
      </div>
      <div className={clsx(
        'w-11 h-6 rounded-full transition-colors relative',
        checked ? 'bg-jarvis-primary' : 'bg-jarvis-border'
      )}>
        <div className={clsx(
          'absolute top-1 w-4 h-4 rounded-full bg-white transition-transform',
          checked ? 'translate-x-6' : 'translate-x-1'
        )} />
      </div>
    </button>
  )
}
