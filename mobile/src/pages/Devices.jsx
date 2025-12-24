import { useState, useEffect } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { 
  Lightbulb, Lock, Unlock, Power, PowerOff, 
  RefreshCw, Wifi, WifiOff, ChevronDown, ChevronUp,
  Loader2, AlertCircle
} from 'lucide-react'
import { api } from '../services/api'
import { wsService } from '../services/websocket'
import { useToast } from '../contexts/ToastContext'
import PinConfirm from '../components/PinConfirm'
import clsx from 'clsx'

const deviceIcons = {
  light_switch: Lightbulb,
  door_lock: Lock,
  sensor: Wifi,
  generic: Power,
}

export default function Devices() {
  const toast = useToast()
  const queryClient = useQueryClient()
  const [expandedDevice, setExpandedDevice] = useState(null)
  const [pinConfirm, setPinConfirm] = useState({ isOpen: false, deviceId: null, action: null })
  
  // Fetch devices
  const { data, isLoading, error, refetch, isRefetching } = useQuery({
    queryKey: ['devices'],
    queryFn: () => api.devices.list(),
  })
  
  // Device action mutation
  const actionMutation = useMutation({
    mutationFn: ({ deviceId, action, value }) => 
      api.devices.action(deviceId, action, value),
    onSuccess: (result) => {
      if (result.success) {
        toast.success(result.message)
        queryClient.invalidateQueries(['devices'])
      } else {
        toast.error(result.message)
      }
    },
    onError: (error) => {
      toast.error(error.message)
    },
  })
  
  // Listen for device state changes via WebSocket
  useEffect(() => {
    const unsub = wsService.on('device_state_changed', (data) => {
      queryClient.invalidateQueries(['devices'])
      toast.info(`${data.device_id} state changed`)
    })
    
    // Subscribe to device updates
    wsService.subscribe('devices')
    
    return () => {
      unsub()
      wsService.unsubscribe('devices')
    }
  }, [queryClient, toast])
  
  // Handle device action
  const handleAction = (deviceId, action, value = null) => {
    actionMutation.mutate({ deviceId, action, value })
  }
  
  // Toggle device expansion
  const toggleExpand = (deviceId) => {
    setExpandedDevice(expandedDevice === deviceId ? null : deviceId)
  }
  
  if (isLoading) {
    return (
      <div className="h-full flex items-center justify-center">
        <Loader2 className="w-8 h-8 animate-spin text-jarvis-primary" />
      </div>
    )
  }
  
  if (error) {
    return (
      <div className="h-full flex flex-col items-center justify-center p-8 text-center">
        <AlertCircle className="w-12 h-12 text-jarvis-error mb-4" />
        <h3 className="text-lg font-medium text-jarvis-text mb-2">Failed to load devices</h3>
        <p className="text-sm text-jarvis-muted mb-4">{error.message}</p>
        <button
          onClick={() => refetch()}
          className="px-4 py-2 bg-jarvis-primary text-jarvis-bg rounded-lg"
        >
          Retry
        </button>
      </div>
    )
  }
  
  const devices = data?.devices || []
  
  return (
    <div className="p-4 pb-20">
      {/* Header with refresh */}
      <div className="flex items-center justify-between mb-4">
        <div>
          <h2 className="text-lg font-semibold text-jarvis-text">IoT Devices</h2>
          <p className="text-sm text-jarvis-muted">{devices.length} devices</p>
        </div>
        <button
          onClick={() => refetch()}
          disabled={isRefetching}
          className="p-2 rounded-lg bg-jarvis-card border border-jarvis-border
                   hover:border-jarvis-primary/50 disabled:opacity-50"
        >
          <RefreshCw className={clsx('w-5 h-5', isRefetching && 'animate-spin')} />
        </button>
      </div>
      
      {/* Device list */}
      {devices.length === 0 ? (
        <div className="text-center py-12">
          <Power className="w-12 h-12 mx-auto text-jarvis-muted/50 mb-4" />
          <h3 className="text-lg font-medium text-jarvis-text mb-2">No devices found</h3>
          <p className="text-sm text-jarvis-muted">
            Connect IoT devices to control them here
          </p>
        </div>
      ) : (
        <div className="space-y-3">
          {devices.map((device) => {
            const Icon = deviceIcons[device.device_type] || Power
            const isExpanded = expandedDevice === device.device_id
            const isOnline = device.state === 'online'
            const isOn = device.is_on
            
            return (
              <div
                key={device.device_id}
                className="bg-jarvis-card rounded-xl border border-jarvis-border overflow-hidden"
              >
                {/* Device header */}
                <button
                  onClick={() => toggleExpand(device.device_id)}
                  className="w-full p-4 flex items-center gap-4 text-left"
                >
                  {/* Icon */}
                  <div className={clsx(
                    'w-12 h-12 rounded-full flex items-center justify-center',
                    isOn ? 'bg-jarvis-secondary/20' : 'bg-jarvis-muted/10'
                  )}>
                    <Icon className={clsx(
                      'w-6 h-6',
                      isOn ? 'text-jarvis-secondary' : 'text-jarvis-muted'
                    )} />
                  </div>
                  
                  {/* Info */}
                  <div className="flex-1 min-w-0">
                    <h3 className="font-medium text-jarvis-text truncate">
                      {device.name}
                    </h3>
                    <div className="flex items-center gap-2 mt-0.5">
                      <span className={clsx(
                        'text-xs',
                        isOnline ? 'text-jarvis-secondary' : 'text-jarvis-muted'
                      )}>
                        {isOnline ? 'Online' : 'Offline'}
                      </span>
                      {device.device_type !== 'generic' && (
                        <>
                          <span className="text-jarvis-muted">•</span>
                          <span className="text-xs text-jarvis-muted capitalize">
                            {device.device_type.replace('_', ' ')}
                          </span>
                        </>
                      )}
                    </div>
                  </div>
                  
                  {/* Quick toggle for lights */}
                  {device.device_type === 'light_switch' && isOnline && (
                    <button
                      onClick={(e) => {
                        e.stopPropagation()
                        handleAction(device.device_id, isOn ? 'off' : 'on')
                      }}
                      disabled={actionMutation.isPending}
                      className={clsx(
                        'w-12 h-7 rounded-full transition-colors relative',
                        isOn ? 'bg-jarvis-secondary' : 'bg-jarvis-border'
                      )}
                    >
                      <div className={clsx(
                        'absolute top-1 w-5 h-5 rounded-full bg-white transition-transform',
                        isOn ? 'translate-x-6' : 'translate-x-1'
                      )} />
                    </button>
                  )}
                  
                  {/* Expand indicator */}
                  {isExpanded ? (
                    <ChevronUp className="w-5 h-5 text-jarvis-muted" />
                  ) : (
                    <ChevronDown className="w-5 h-5 text-jarvis-muted" />
                  )}
                </button>
                
                {/* Expanded controls */}
                {isExpanded && (
                  <div className="px-4 pb-4 pt-2 border-t border-jarvis-border animate-fade-in">
                    {/* Device-specific controls */}
                    {device.device_type === 'light_switch' && (
                      <div className="space-y-4">
                        {/* On/Off buttons */}
                        <div className="flex gap-2">
                          <button
                            onClick={() => handleAction(device.device_id, 'on')}
                            disabled={!isOnline || actionMutation.isPending}
                            className={clsx(
                              'flex-1 py-2.5 rounded-lg font-medium transition-colors',
                              'disabled:opacity-50 disabled:cursor-not-allowed',
                              isOn
                                ? 'bg-jarvis-secondary text-jarvis-bg'
                                : 'bg-jarvis-bg border border-jarvis-border text-jarvis-text'
                            )}
                          >
                            <Power className="w-4 h-4 inline mr-2" />
                            On
                          </button>
                          <button
                            onClick={() => handleAction(device.device_id, 'off')}
                            disabled={!isOnline || actionMutation.isPending}
                            className={clsx(
                              'flex-1 py-2.5 rounded-lg font-medium transition-colors',
                              'disabled:opacity-50 disabled:cursor-not-allowed',
                              !isOn
                                ? 'bg-jarvis-muted/20 text-jarvis-text'
                                : 'bg-jarvis-bg border border-jarvis-border text-jarvis-text'
                            )}
                          >
                            <PowerOff className="w-4 h-4 inline mr-2" />
                            Off
                          </button>
                        </div>
                        
                        {/* Brightness slider (if supported) */}
                        {device.position !== undefined && (
                          <div>
                            <label className="text-sm text-jarvis-muted mb-2 block">
                              Brightness: {device.position}%
                            </label>
                            <input
                              type="range"
                              min="0"
                              max="100"
                              value={device.position || 0}
                              onChange={(e) => handleAction(device.device_id, 'set_position', parseInt(e.target.value))}
                              disabled={!isOnline}
                              className="w-full accent-jarvis-primary"
                            />
                          </div>
                        )}
                      </div>
                    )}
                    
                    {device.device_type === 'door_lock' && (
                      <div className="flex gap-2">
                        <button
                          onClick={() => setPinConfirm({ 
                            isOpen: true, 
                            deviceId: device.device_id, 
                            action: 'unlock' 
                          })}
                          disabled={!isOnline || actionMutation.isPending}
                          className="flex-1 py-2.5 rounded-lg font-medium bg-jarvis-warning/20 text-jarvis-warning
                                   disabled:opacity-50 disabled:cursor-not-allowed"
                        >
                          <Unlock className="w-4 h-4 inline mr-2" />
                          Unlock
                        </button>
                        <button
                          onClick={() => handleAction(device.device_id, 'lock')}
                          disabled={!isOnline || actionMutation.isPending}
                          className="flex-1 py-2.5 rounded-lg font-medium bg-jarvis-secondary/20 text-jarvis-secondary
                                   disabled:opacity-50 disabled:cursor-not-allowed"
                        >
                          <Lock className="w-4 h-4 inline mr-2" />
                          Lock
                        </button>
                      </div>
                    )}
                    
                    {/* Device info */}
                    <div className="mt-4 pt-4 border-t border-jarvis-border">
                      <div className="grid grid-cols-2 gap-2 text-xs">
                        <div>
                          <span className="text-jarvis-muted">ID:</span>
                          <span className="ml-1 text-jarvis-text">{device.device_id}</span>
                        </div>
                        {device.ip_address && (
                          <div>
                            <span className="text-jarvis-muted">IP:</span>
                            <span className="ml-1 text-jarvis-text">{device.ip_address}</span>
                          </div>
                        )}
                        {device.last_seen && (
                          <div className="col-span-2">
                            <span className="text-jarvis-muted">Last seen:</span>
                            <span className="ml-1 text-jarvis-text">
                              {new Date(device.last_seen).toLocaleString()}
                            </span>
                          </div>
                        )}
                      </div>
                    </div>
                  </div>
                )}
              </div>
            )
          })}
        </div>
      )}
      
      {/* PIN Confirmation Modal */}
      <PinConfirm
        isOpen={pinConfirm.isOpen}
        onClose={() => setPinConfirm({ isOpen: false, deviceId: null, action: null })}
        onConfirm={async (pin) => {
          // For now, accept any 4-digit PIN (in production, verify against stored PIN)
          if (pin.length === 4) {
            handleAction(pinConfirm.deviceId, pinConfirm.action)
          } else {
            throw new Error('Invalid PIN')
          }
        }}
        title="Unlock Door"
        message="Enter your 4-digit PIN to unlock"
        dangerous={true}
      />
    </div>
  )
}
