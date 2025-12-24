/**
 * WebSocket Service for JARVIS Mobile
 * 
 * Real-time bidirectional communication with auto-reconnect.
 */

class WebSocketService {
  constructor() {
    this.ws = null
    this.url = null
    this.token = null
    this.reconnectAttempts = 0
    this.maxReconnectAttempts = 5
    this.reconnectDelay = 1000
    this.listeners = new Map()
    this.messageQueue = []
    this.isConnecting = false
    this.pingInterval = null
  }
  
  connect(token) {
    if (this.isConnecting || (this.ws && this.ws.readyState === WebSocket.OPEN)) {
      return
    }
    
    this.token = token
    this.isConnecting = true
    
    // Build WebSocket URL
    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:'
    const host = window.location.host
    this.url = `${protocol}//${host}/api/v1/ws?token=${token}`
    
    try {
      this.ws = new WebSocket(this.url)
      
      this.ws.onopen = () => {
        console.log('WebSocket connected')
        this.isConnecting = false
        this.reconnectAttempts = 0
        this.emit('connected')
        
        // Send queued messages
        while (this.messageQueue.length > 0) {
          const msg = this.messageQueue.shift()
          this.send(msg.type, msg.data)
        }
        
        // Start ping interval
        this.startPing()
      }
      
      this.ws.onclose = (event) => {
        console.log('WebSocket closed:', event.code, event.reason)
        this.isConnecting = false
        this.stopPing()
        this.emit('disconnected', { code: event.code, reason: event.reason })
        
        // Attempt reconnect
        if (this.reconnectAttempts < this.maxReconnectAttempts) {
          this.scheduleReconnect()
        }
      }
      
      this.ws.onerror = (error) => {
        console.error('WebSocket error:', error)
        this.isConnecting = false
        this.emit('error', error)
      }
      
      this.ws.onmessage = (event) => {
        try {
          const message = JSON.parse(event.data)
          this.handleMessage(message)
        } catch (error) {
          console.error('Failed to parse WebSocket message:', error)
        }
      }
      
    } catch (error) {
      console.error('Failed to create WebSocket:', error)
      this.isConnecting = false
      this.scheduleReconnect()
    }
  }
  
  disconnect() {
    this.stopPing()
    this.reconnectAttempts = this.maxReconnectAttempts // Prevent reconnect
    
    if (this.ws) {
      this.ws.close(1000, 'User disconnect')
      this.ws = null
    }
  }
  
  scheduleReconnect() {
    this.reconnectAttempts++
    const delay = this.reconnectDelay * Math.pow(2, this.reconnectAttempts - 1)
    
    console.log(`Reconnecting in ${delay}ms (attempt ${this.reconnectAttempts})`)
    
    setTimeout(() => {
      if (this.token) {
        this.connect(this.token)
      }
    }, delay)
  }
  
  startPing() {
    this.pingInterval = setInterval(() => {
      this.send('ping', {})
    }, 30000) // Ping every 30 seconds
  }
  
  stopPing() {
    if (this.pingInterval) {
      clearInterval(this.pingInterval)
      this.pingInterval = null
    }
  }
  
  send(type, data = {}) {
    const message = {
      type,
      data,
      message_id: `${Date.now()}-${Math.random().toString(36).substr(2, 9)}`,
    }
    
    if (this.ws && this.ws.readyState === WebSocket.OPEN) {
      this.ws.send(JSON.stringify(message))
      return message.message_id
    } else {
      // Queue message for later
      this.messageQueue.push(message)
      return null
    }
  }
  
  handleMessage(message) {
    const { type, data, message_id } = message
    
    // Emit specific event
    this.emit(type, data, message_id)
    
    // Emit generic message event
    this.emit('message', { type, data, message_id })
  }
  
  // Event emitter methods
  on(event, callback) {
    if (!this.listeners.has(event)) {
      this.listeners.set(event, new Set())
    }
    this.listeners.get(event).add(callback)
    
    // Return unsubscribe function
    return () => {
      this.listeners.get(event)?.delete(callback)
    }
  }
  
  off(event, callback) {
    this.listeners.get(event)?.delete(callback)
  }
  
  emit(event, ...args) {
    this.listeners.get(event)?.forEach(callback => {
      try {
        callback(...args)
      } catch (error) {
        console.error(`Error in WebSocket listener for ${event}:`, error)
      }
    })
  }
  
  // Convenience methods
  sendCommand(text) {
    return this.send('command', { text })
  }
  
  sendAudioChunk(audioBase64) {
    return this.send('audio_chunk', { audio: audioBase64 })
  }
  
  cancelOperation() {
    return this.send('cancel', {})
  }
  
  subscribe(topic) {
    return this.send('subscribe', { topic })
  }
  
  unsubscribe(topic) {
    return this.send('unsubscribe', { topic })
  }
  
  get isConnected() {
    return this.ws && this.ws.readyState === WebSocket.OPEN
  }
  
  get connectionState() {
    if (!this.ws) return 'disconnected'
    switch (this.ws.readyState) {
      case WebSocket.CONNECTING: return 'connecting'
      case WebSocket.OPEN: return 'connected'
      case WebSocket.CLOSING: return 'closing'
      case WebSocket.CLOSED: return 'disconnected'
      default: return 'unknown'
    }
  }
}

export const wsService = new WebSocketService()
